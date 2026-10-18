"""Tests for Rule RAG chunking, pgvector ingestion, and semantic search (Phase 2).
Enforces strict TDD: tests written before implementation.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rule_chunk_ingestion_and_search(client: AsyncClient, auth_org_a: dict, db_session):
    """Ingesting source document chunks and searching via GET /api/v1/rules/search."""
    from app.modules.rules.rag import ingest_source_document

    sample_text = """
    # NBC 2016 Part 3: Development Control Rules and General Building Requirements

    ## Clause 4.2 Habitable Rooms
    4.2.1 Size of Habitable Room
    No habitable room shall have a floor area of less than 9.5 m2, where there is only one room with a minimum width of 2.4 m.
    Where there are two rooms, one of these shall not be less than 9.5 m2 and the other not less than 7.5 m2 with a minimum width of 2.1 m.

    ## Clause 4.3 Kitchen
    4.3.1 Size of Kitchen
    The area of kitchen where separate dining area is provided shall be not less than 5.0 m2 with a minimum width of 1.8 m.
    Where there is no separate dining area, the area of kitchen shall not be less than 7.5 m2 with a minimum width of 2.1 m.

    ## Clause 4.4 Bathrooms and Water-Closets
    4.4.1 Size of Bathroom
    The size of a bathroom shall not be less than 1.8 m2 with a minimum width of 1.2 m.
    The size of a water closet (WC) shall not be less than 1.1 m2 with a minimum width of 0.9 m.
    """

    # Ingest document
    count = await ingest_source_document(
        document_id="NBC-2016-Part3",
        document_title="National Building Code of India 2016 (Part 3)",
        text=sample_text,
        session=db_session,
    )
    assert count >= 3

    # Search for habitable room size
    resp = await client.get(
        "/api/v1/rules/search?q=habitable+room+minimum+floor+area",
        headers=auth_org_a["headers"],
    )
    assert resp.status_code == 200
    results = resp.json()

    assert isinstance(results, list)
    assert len(results) > 0

    top = results[0]
    assert "document" in top
    assert "section" in top
    assert "content" in top
    assert "score" in top
    assert "9.5" in top["content"] or "habitable" in top["content"].lower()


@pytest.mark.asyncio
async def test_rule_search_empty_query(client: AsyncClient, auth_org_a: dict):
    """Empty or blank query should return 422 or empty list gracefully."""
    resp = await client.get(
        "/api/v1/rules/search?q=",
        headers=auth_org_a["headers"],
    )
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json() == []
