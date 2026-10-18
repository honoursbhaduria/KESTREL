"""Tests for LLM wrapper, structured output, retries, and usage/cost logging."""

import uuid

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMClient, MockLLMProvider, UsageInfo
from app.ai.models import UsageEvent


class SampleOutput(BaseModel):
    summary: str
    score: int = Field(ge=0, le=100)


@pytest.mark.asyncio
async def test_llm_structured_output_mock():
    """Verify provider returns structured Pydantic object."""
    mock_provider = MockLLMProvider()
    client = LLMClient(provider=mock_provider)

    prompt = "Analyze the room layout score."
    result, usage = await client.generate_structured(
        prompt=prompt,
        response_model=SampleOutput,
        kind="test_kind",
    )

    assert isinstance(result, SampleOutput)
    assert result.summary != ""
    assert 0 <= result.score <= 100
    assert usage.input_tokens > 0
    assert usage.output_tokens > 0
    assert usage.cost >= 0.0


@pytest.mark.asyncio
async def test_llm_usage_logging_to_db():
    """Verify token counts and cost are recorded in usage_events table."""
    from app.modules.auth.models import Organization
    from tests.conftest import TestingSessionLocal

    async with TestingSessionLocal() as session:
        org = Organization(name="AI Test Org", slug=f"ai-test-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()
        org_id = org.id

        mock_provider = MockLLMProvider()
        client = LLMClient(provider=mock_provider)

        result, usage = await client.generate_structured(
            prompt="Explain brief summary",
            response_model=SampleOutput,
            kind="brief_structure",
            org_id=org_id,
            session=session,
        )
        await session.commit()

        # Verify row in usage_events
        query = select(UsageEvent).where(UsageEvent.org_id == org_id)
        records = (await session.execute(query)).scalars().all()
        assert len(records) == 1
        event = records[0]
        assert event.kind == "brief_structure"
        assert event.model == mock_provider.model_name
        assert event.input_tokens == usage.input_tokens
        assert event.output_tokens == usage.output_tokens
        assert round(event.cost, 6) == round(usage.cost, 6)


@pytest.mark.asyncio
async def test_llm_retries_on_failure():
    """Verify client retries with backoff upon transient provider error."""
    attempts = 0

    class FlakyProvider(MockLLMProvider):
        async def complete(self, prompt: str, system: str | None = None) -> tuple[str, UsageInfo]:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Transient network failure")
            return await super().complete(prompt, system)

    flaky_provider = FlakyProvider()
    client = LLMClient(provider=flaky_provider, max_retries=3)

    result, usage = await client.generate_structured(
        prompt="Retry test",
        response_model=SampleOutput,
        kind="test_retry",
    )
    assert attempts == 3
    assert isinstance(result, SampleOutput)
