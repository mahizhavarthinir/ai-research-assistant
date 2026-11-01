"""
Tests for Phase 4: Multi-source document comparison and Research Report generator.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.document import Document
from app.models.user import User


@pytest.mark.asyncio
async def test_multi_source_comparison_ownership_check(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that comparison endpoint enforces strict user ownership on all documents."""
    # 1. Create a document owned by the test user
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    doc1 = Document(
        user_id=user.id,
        filename="Doc_A_Quantum_Key.pdf",
        storage_path="/tmp/doc_a.pdf",
        file_type="pdf",
        file_size=1024,
        status="indexed",
    )
    db_session.add(doc1)

    # 2. Create another document owned by a different user
    other_user = User(
        email="other_researcher@example.com",
        username="other_researcher",
        hashed_password=hash_password("Pass123!"),
    )
    db_session.add(other_user)
    await db_session.flush()

    doc2_unowned = Document(
        user_id=other_user.id,
        filename="Doc_B_Private.pdf",
        storage_path="/tmp/doc_b.pdf",
        file_type="pdf",
        file_size=1024,
        status="indexed",
    )
    db_session.add(doc2_unowned)
    await db_session.commit()

    # Attempting to compare doc1 with doc2_unowned must fail with 404
    response = await client.post(
        "/api/v1/research/compare",
        json={"document_ids": [doc1.id, doc2_unowned.id], "topic": "Key distribution protocols"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "not found or access denied" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_multi_source_comparison_requires_at_least_two_docs(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that comparison endpoint validates minimum 2 documents."""
    response = await client.post(
        "/api/v1/research/compare",
        json={"document_ids": ["single-doc-id"], "topic": "Overview"},
        headers=auth_headers,
    )
    assert response.status_code == 422 or response.status_code == 400


@pytest.mark.asyncio
async def test_multi_source_comparison_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    monkeypatch,
):
    """Test successful document comparison with mock LLM response."""
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    doc1 = Document(
        user_id=user.id,
        filename="Quantum_BB84_Protocol.pdf",
        storage_path="/tmp/bb84.pdf",
        file_type="pdf",
        file_size=2048,
        status="indexed",
    )
    doc2 = Document(
        user_id=user.id,
        filename="Quantum_E91_Protocol.pdf",
        storage_path="/tmp/e91.pdf",
        file_type="pdf",
        file_size=2048,
        status="indexed",
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()

    # Mock LLM provider to return structured comparison
    from app.llm.base import LLMResponse

    async def mock_generate(*args, **kwargs):
        content = (
            "## Comparison Overview\n"
            "This analysis compares BB84 and E91 quantum key distribution protocols.\n\n"
            "## Comparative Matrix\n"
            "| Dimension | BB84 | E91 | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| Mechanism | Prepare and Measure [1] | Entangled Photon Pairs [2] | Different photon states |\n"
            "| Max Fiber Distance | 120 km [1] | 100 km [2] | Optical channel limits |\n\n"
            "## Consensus & Shared Findings\n"
            "Both protocols guarantee unconditional security based on quantum physics [1][2].\n\n"
            "## Divergences & Contrasting Perspectives\n"
            "BB84 relies on single photon polarization states, whereas E91 utilizes EPR pairs [2].\n\n"
            "## Gaps & Unavailable Information\n"
            "Document Quantum_E91_Protocol.pdf does not contain information regarding error correction runtime overhead.\n\n"
            "## Conclusions & Synthesis\n"
            "Both protocols demonstrate quantum key establishment with distinct optical trade-offs."
        )
        return LLMResponse(content=content, model="mock-model", total_tokens=420)

    from app.llm import get_llm_provider
    provider = get_llm_provider()
    monkeypatch.setattr(provider, "generate", mock_generate)

    response = await client.post(
        "/api/v1/research/compare",
        json={
            "document_ids": [doc1.id, doc2.id],
            "topic": "Compare security models and transmission distance",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Document Comparison" in data["title"]
    assert "Comparative Matrix" in data["content"]
    assert "Gaps & Unavailable Information" in data["content"]
    assert len(data["documents"]) == 2


@pytest.mark.asyncio
async def test_research_report_generator_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    monkeypatch,
):
    """Test generating a structured research report with executive summary and key findings."""
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    doc = Document(
        user_id=user.id,
        filename="Fiber_Optics_Survey_2026.pdf",
        storage_path="/tmp/fiber.pdf",
        file_type="pdf",
        file_size=4096,
        status="indexed",
    )
    db_session.add(doc)
    await db_session.commit()

    # Mock LLM provider to return structured report
    from app.llm.base import LLMResponse

    async def mock_generate(*args, **kwargs):
        content = (
            "# Research Report: Advances in Low-Loss Optical Fibers\n\n"
            "## Executive Summary\n"
            "This report examines attenuation benchmarks and optical dispersion in modern telecom fibers. "
            "Recent advancements in hollow-core photonic bandgap fibers have achieved transmission loss below 0.14 dB/km [1].\n\n"
            "## Scope & Analyzed Sources\n"
            "Analysis covers standard single-mode fibers and experimental hollow-core waveguides.\n\n"
            "## Key Findings\n"
            "- Attenuation at 1550 nm is reduced to 0.14 dB/km [1].\n"
            "- Non-linear phase noise decreases by 99% in hollow-core mediums [1].\n\n"
            "## In-Depth Analysis\n"
            "Detailed investigation into thermal dissipation and mode field diameter.\n\n"
            "## Strategic Conclusions & Implications\n"
            "Adoption of hollow-core fibers will extend repeaterless spans for subsea transmission.\n\n"
            "## Limitations & Gaps in Evidence\n"
            "The analyzed sources do not contain information regarding commercial manufacturing yield costs."
        )
        return LLMResponse(content=content, model="mock-model", total_tokens=550)

    from app.llm import get_llm_provider
    provider = get_llm_provider()
    monkeypatch.setattr(provider, "generate", mock_generate)

    response = await client.post(
        "/api/v1/research/report",
        json={
            "document_ids": [doc.id],
            "topic": "Low-loss optical transmission and hollow-core fibers",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Advances in Low-Loss Optical Fibers" in data["title"]
    assert len(data["executive_summary"]) > 20
    assert len(data["key_findings"]) >= 1
    assert "Limitations & Gaps in Evidence" in data["content"]
    assert len(data["limitations"]) > 10


@pytest.mark.asyncio
async def test_unavailable_information_admission(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    monkeypatch,
):
    """Test that LLM strictly admits when information is absent from documents."""
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    doc = Document(
        user_id=user.id,
        filename="Classical_Cryptography.pdf",
        storage_path="/tmp/crypto.pdf",
        file_type="pdf",
        file_size=1024,
        status="indexed",
    )
    db_session.add(doc)
    await db_session.commit()

    # Mock LLM to return strict admission of unavailable info
    from app.llm.base import LLMResponse

    async def mock_generate(*args, **kwargs):
        content = (
            "The provided document(s) do not contain information regarding photosynthesis or plant physiology. "
            "Classical_Cryptography.pdf focuses exclusively on RSA key exchange and block ciphers."
        )
        return LLMResponse(content=content, model="mock-model", total_tokens=120)

    from app.llm import get_llm_provider
    provider = get_llm_provider()
    monkeypatch.setattr(provider, "generate", mock_generate)

    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "What does the document say about photosynthesis and chlorophyll fluorescence?",
            "document_id": doc.id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "do not contain information regarding" in data["content"]
    assert len(data["citations"]) == 0  # No false citations fabricated


@pytest.mark.asyncio
async def test_research_export_endpoint(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test exporting research content as Markdown and JSON."""
    payload = {
        "title": "Quantum Repeater Network Comparison",
        "topic": "Quantum Repeaters",
        "executive_summary": "Summary of quantum repeater nodes and entanglement swapping.",
        "key_findings": ["Entanglement swapping works over 50 km", "Fidelity is 98%"],
        "conclusions": "Repeaters enable continental QKD networks.",
        "limitations": "Cryogenic cooling costs are not addressed in the sources.",
        "content": "## Analysis\nFull comparative analysis text goes here.",
        "citations": [
            {
                "id": "c1",
                "source_title": "Quantum Repeaters 2026.pdf",
                "page_number": 3,
                "snippet": "Atomic ensembles act as quantum memory.",
                "citation_index": 1,
            }
        ],
    }

    # 1. Export Markdown
    res_md = await client.post(
        "/api/v1/research/export?format=markdown",
        json=payload,
        headers=auth_headers,
    )
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Quantum Repeater Network Comparison" in res_md.text
    assert "Verified Source Citations" in res_md.text
    assert "Quantum Repeaters 2026.pdf" in res_md.text

    # 2. Export JSON
    res_json = await client.post(
        "/api/v1/research/export?format=json",
        json=payload,
        headers=auth_headers,
    )
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    json_data = res_json.json()
    assert json_data["title"] == "Quantum Repeater Network Comparison"
    assert len(json_data["key_findings"]) == 2
    assert json_data["citations"][0]["citation_index"] == 1