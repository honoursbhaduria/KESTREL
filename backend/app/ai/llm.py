"""Provider-agnostic LLM interface with structured outputs, retries, and token/cost logging."""

import abc
import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import TypeVar

import httpx
import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import UsageEvent
from app.core.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt_template(filename: str) -> str:
    """Load prompt template from app/ai/prompts/ directory."""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


class UsageInfo(BaseModel):
    """Token consumption and estimated USD cost for an LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class LLMProvider(abc.ABC):
    """Abstract LLM completion provider."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @abc.abstractmethod
    async def complete(self, prompt: str, system: str | None = None) -> tuple[str, UsageInfo]:
        """Perform completion returning raw string response and usage metrics."""
        ...


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for offline development, tests, and CI."""

    def __init__(self, model_name: str = "mock-llm-v1"):
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def complete(self, prompt: str, system: str | None = None) -> tuple[str, UsageInfo]:
        in_tokens = max(10, len(prompt.split()))
        out_text = ""

        # Test case: SampleOutput / generic summary
        if "SampleOutput" in prompt or "Analyze the room layout score" in prompt or "test_retry" in prompt or "Explain brief" in prompt:
            out_text = json.dumps({"summary": "Layout has balanced zoning and good circulation.", "score": 85})

        # Test case: Infeasible mansion brief (FAR check)
        elif "mansion" in prompt.lower() or "grand ballroom" in prompt.lower() or "800 sqm" in prompt.lower():
            out_text = json.dumps({
                "levels": 2,
                "rooms": [
                    {"type": "living", "name": "Grand Ballroom", "target_area_mm2": 150_000_000.0, "min_width_mm": 8000.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                    {"type": "bedroom", "name": "Master Suite 1", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 2, "needs_exterior_wall": True, "needs_attached_bath": True},
                    {"type": "bedroom", "name": "Master Suite 2", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 2, "needs_exterior_wall": True, "needs_attached_bath": True},
                    {"type": "bedroom", "name": "Master Suite 3", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 2, "needs_exterior_wall": True, "needs_attached_bath": True},
                    {"type": "bedroom", "name": "Master Suite 4", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 2, "needs_exterior_wall": True, "needs_attached_bath": True},
                    {"type": "bedroom", "name": "Master Suite 5", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": True},
                    {"type": "kitchen", "name": "Commercial Kitchen", "target_area_mm2": 50_000_000.0, "min_width_mm": 5000.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                ],
                "adjacencies": [{"a": "Grand Ballroom", "b": "Commercial Kitchen", "strength": "must"}],
                "preferences": {"entrance_side": "east", "vastu": False, "parking": True, "style_notes": "Luxury mansion"},
            })

        # General brief structuring
        elif "brief" in prompt.lower() or "structure" in prompt.lower():
            is_two_floors = "2" in prompt or "two" in prompt.lower() or "first floor" in prompt.lower() or "storey" in prompt.lower()
            levels = 2 if is_two_floors else 1
            rooms = [
                {"type": "living", "name": "Living Room", "target_area_mm2": 22_000_000.0, "min_width_mm": 3200.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                {"type": "kitchen", "name": "Modular Kitchen", "target_area_mm2": 9_000_000.0, "min_width_mm": 2400.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                {"type": "dining", "name": "Dining Room", "target_area_mm2": 11_000_000.0, "min_width_mm": 2700.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                {"type": "bedroom", "name": "Master Bedroom", "target_area_mm2": 15_000_000.0, "min_width_mm": 3200.0, "level_hint": levels, "needs_exterior_wall": True, "needs_attached_bath": True},
                {"type": "bathroom", "name": "Master Bath", "target_area_mm2": 4_500_000.0, "min_width_mm": 1800.0, "level_hint": levels, "needs_exterior_wall": False, "needs_attached_bath": True},
                {"type": "bedroom", "name": "Guest Bedroom", "target_area_mm2": 13_000_000.0, "min_width_mm": 3000.0, "level_hint": 1, "needs_exterior_wall": True, "needs_attached_bath": False},
                {"type": "bathroom", "name": "Powder Toilet", "target_area_mm2": 3_000_000.0, "min_width_mm": 1200.0, "level_hint": 1, "needs_exterior_wall": False, "needs_attached_bath": False},
            ]
            if levels > 1:
                rooms.append({"type": "stair", "name": "Staircase", "target_area_mm2": 6_000_000.0, "min_width_mm": 2000.0, "level_hint": 1, "needs_exterior_wall": False, "needs_attached_bath": False})
                rooms.append({"type": "stair", "name": "Staircase", "target_area_mm2": 6_000_000.0, "min_width_mm": 2000.0, "level_hint": 2, "needs_exterior_wall": False, "needs_attached_bath": False})
                rooms.append({"type": "bedroom", "name": "Kids Bedroom", "target_area_mm2": 13_000_000.0, "min_width_mm": 3000.0, "level_hint": 2, "needs_exterior_wall": True, "needs_attached_bath": False})

            entrance_side = "east"
            brief_match = re.search(r"Client Brief:\s*(.*)", prompt, re.DOTALL | re.IGNORECASE)
            brief_content = brief_match.group(1).lower() if brief_match else prompt.lower()

            if "east" in brief_content:
                entrance_side = "east"
            elif "north" in brief_content:
                entrance_side = "north"
            elif "west" in brief_content:
                entrance_side = "west"
            elif "south" in brief_content:
                entrance_side = "south"

            out_text = json.dumps({
                "levels": levels,
                "rooms": rooms,
                "adjacencies": [
                    {"a": "Living Room", "b": "Modular Kitchen", "strength": "prefer"},
                    {"a": "Master Bedroom", "b": "Master Bath", "strength": "must"},
                ],
                "preferences": {
                    "entrance_side": entrance_side,
                    "vastu": "vastu" in brief_content,
                    "parking": "parking" in brief_content,
                    "style_notes": "Modern residential layout with natural daylight.",
                },
            })

        # Option description
        elif "describe" in prompt.lower() or "option details" in prompt.lower():
            out_text = json.dumps({
                "description": (
                    "Scheme arranges the social zones along the primary entrance side with direct natural daylight. "
                    "Private bedrooms are clustered for acoustic privacy with seamless circulation access. "
                    "Service utilities and wet cores are aligned to optimize plumbing and statutory clearances."
                )
            })
        else:
            out_text = json.dumps({"summary": "Default model completion", "score": 90, "description": "Completed layout."})

        out_tokens = max(15, len(out_text.split()))
        # Estimated cost: $0.15 / 1M input, $0.60 / 1M output
        cost = (in_tokens * 0.00000015) + (out_tokens * 0.00000060)
        return out_text, UsageInfo(input_tokens=in_tokens, output_tokens=out_tokens, cost=cost)


class OpenAILLMProvider(LLMProvider):
    """OpenAI API provider for production inference."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str | None = None) -> tuple[str, UsageInfo]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = (in_tok * 0.00000015) + (out_tok * 0.00000060)
        return content, UsageInfo(input_tokens=in_tok, output_tokens=out_tok, cost=cost)


class LLMClient:
    """High-level client supporting structured response parsing, retry backoff, and usage logging."""

    def __init__(self, provider: LLMProvider | None = None, max_retries: int = 3, base_delay: float = 0.05):
        if provider is not None:
            self.provider = provider
        else:
            settings = get_settings()
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key and getattr(settings, "LLM_PROVIDER", "mock") == "openai":
                self.provider = OpenAILLMProvider(api_key=api_key)
            else:
                self.provider = MockLLMProvider()

        self.max_retries = max_retries
        self.base_delay = base_delay

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        kind: str,
        system: str | None = None,
        org_id: uuid.UUID | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[T, UsageInfo]:
        """Execute LLM call with exponential retry and parse response into response_model."""
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                raw_text, usage = await self.provider.complete(prompt, system=system)
                # Clean up any potential markdown code blocks
                clean_text = raw_text.strip()
                if clean_text.startswith("```"):
                    clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                    clean_text = re.sub(r"\s*```$", "", clean_text)

                parsed_json = json.loads(clean_text)
                model_instance = response_model.model_validate(parsed_json)

                # Log usage to DB if session and org_id provided
                if session is not None and org_id is not None:
                    event = UsageEvent(
                        org_id=org_id,
                        kind=kind,
                        model=self.provider.model_name,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        cost=usage.cost,
                    )
                    session.add(event)
                    await session.flush()

                return model_instance, usage
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "llm_completion_retry",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=str(exc),
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.base_delay * (2 ** (attempt - 1)))

        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last_exc}") from last_exc
