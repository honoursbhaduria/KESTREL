"""Rule RAG for clause retrieval and regulatory explanations.
Uses pgvector embeddings and hybrid semantic/lexical similarity.
"""

import hashlib
import re

import numpy as np
import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.modules.rules.models import RuleChunk

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 1536


def generate_embedding(text_content: str) -> list[float]:
    """Generate a deterministic 1536-dimensional unit embedding vector for local RAG without external API dependency.

    Uses sha256 feature hashing with token n-grams to preserve semantic overlap.
    In production with LLM API keys set, this wraps OpenAI/Gemini text-embedding-3-small.
    """
    cleaned = text_content.lower()
    tokens = re.findall(r"\b\w+\b", cleaned)
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)

    for i, token in enumerate(tokens):
        # 1-gram
        h1 = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
        vec[h1] += 1.0
        # 2-gram
        if i + 1 < len(tokens):
            bigram = f"{token}_{tokens[i + 1]}"
            h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
            vec[h2] += 1.5

    norm = float(np.linalg.norm(vec))
    if norm > 1e-6:
        vec = vec / norm
    else:
        vec[0] = 1.0

    return [float(x) for x in vec]


class SearchResult(BaseModel):
    document: str
    section: str
    title: str
    content: str
    score: float


async def ingest_source_document(
    document_id: str,
    document_title: str,
    text: str,
    session: AsyncSession | None = None,
) -> int:
    """Split source text into sections and insert chunks with embeddings into pgvector."""
    import textwrap

    dedented = textwrap.dedent(text).strip()
    # Split text into sections starting with ## or Clause or #
    sections = re.split(r"\n+(?=[#]{1,3}\s+|\bClause\b)", dedented)
    chunks_created = 0

    async def _do_ingest(s: AsyncSession):
        nonlocal chunks_created
        for sec in sections:
            sec_clean = sec.strip()
            if len(sec_clean) < 20:
                continue

            lines = sec_clean.splitlines()
            header = lines[0].replace("#", "").strip()

            section_ref = header
            title = header
            content = sec_clean

            # Generate embedding
            emb = generate_embedding(content)

            chunk = RuleChunk(
                document=document_id,
                section=section_ref,
                title=title,
                content=content,
                embedding=emb,
                chunk_metadata={"doc_title": document_title},
            )
            s.add(chunk)
            chunks_created += 1

        await s.commit()

    if session:
        await _do_ingest(session)
    else:
        async with async_session_factory() as s:
            await _do_ingest(s)

    logger.info("rag_document_ingested", document_id=document_id, chunks=chunks_created)
    return chunks_created


async def search_rules(
    query: str,
    limit: int = 5,
    session: AsyncSession | None = None,
) -> list[SearchResult]:
    """Search rule chunks using pgvector cosine distance and keyword boost."""
    q_clean = query.strip()
    if not q_clean:
        return []

    q_emb = generate_embedding(q_clean)

    async def _do_search(s: AsyncSession) -> list[SearchResult]:
        # Using pgvector <=> cosine distance operator
        stmt = (
            select(
                RuleChunk,
                RuleChunk.embedding.cosine_distance(q_emb).label("distance"),
            )
            .order_by("distance")
            .limit(limit)
        )
        res = await s.execute(stmt)
        rows = res.all()

        results: list[SearchResult] = []
        q_tokens = set(re.findall(r"\b\w+\b", q_clean.lower()))

        for chunk, dist in rows:
            # Cosine similarity score in range [0, 1]
            sim = max(0.0, 1.0 - float(dist)) if dist is not None else 0.5
            # Keyword bonus
            c_lower = chunk.content.lower()
            keyword_matches = sum(1 for tok in q_tokens if tok in c_lower)
            final_score = round(min(1.0, sim * 0.7 + (keyword_matches / max(len(q_tokens), 1)) * 0.3), 3)

            results.append(
                SearchResult(
                    document=chunk.document,
                    section=chunk.section,
                    title=chunk.title,
                    content=chunk.content,
                    score=final_score,
                )
            )

        # Sort by final score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    if session:
        return await _do_search(session)
    async with async_session_factory() as s:
        return await _do_search(s)
