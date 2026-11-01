"""
Comprehensive Tests for PDF and Word (.docx) Export Services and Endpoints.
Verifies binary format signatures, document structures, headings, callouts, and citations.
"""

import io
import pytest
from httpx import AsyncClient
from docx import Document
from sqlalchemy import select

from app.models.conversation import Conversation, Message
from app.models.citation import Citation
from app.models.user import User


@pytest.mark.asyncio
async def test_export_conversation_pdf(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test exporting a conversation as a publication-ready PDF document."""
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    conv = Conversation(title="Neural Networks Research", user_id=user.id)
    db_session.add(conv)
    await db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="What is gradient descent and backpropagation in deep neural networks?",
        sequence_number=0,
    )
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content=(
            "### Optimization Overview\n\n"
            "Gradient descent iteratively computes parameter gradients to minimize loss.\n\n"
            "#### Key Properties\n"
            "- Learning rate controls step size [1].\n"
            "- Backpropagation applies the chain rule of calculus [1].\n"
            "- Momentum prevents local minima oscillations.\n"
        ),
        sequence_number=1,
    )
    db_session.add_all([msg1, msg2])
    await db_session.flush()

    cit = Citation(
        message_id=msg2.id,
        citation_index=1,
        source_title="Deep Learning Foundations.pdf",
        page_number=42,
        snippet="Backpropagation calculates gradients through reverse accumulation of the chain rule.",
        relevance_score=0.95,
    )
    db_session.add(cit)
    await db_session.commit()

    # Request PDF export
    response = await client.get(
        f"/api/v1/chat/conversations/{conv.id}/export?format=pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Neural_Networks_Research.pdf" in response.headers["content-disposition"]
    # PDF magic bytes
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


@pytest.mark.asyncio
async def test_export_conversation_docx(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test exporting a conversation as a Word (.docx) document."""
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    conv = Conversation(title="CRISPR Gene Editing Study", user_id=user.id)
    db_session.add(conv)
    await db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="Explain the mechanism of Cas9 guide RNA targeting.",
        sequence_number=0,
    )
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content=(
            "## Molecular Mechanism\n\n"
            "Cas9 forms a ribonucleoprotein complex with a synthetic single guide RNA (sgRNA).\n\n"
            "### Targeted Cleavage Steps\n"
            "- Protospacer Adjacent Motif (PAM) recognition.\n"
            "- DNA unwinding and R-loop formation.\n"
            "- Double-strand break induction at targeted locus.\n"
        ),
        sequence_number=1,
    )
    db_session.add_all([msg1, msg2])
    await db_session.flush()

    cit = Citation(
        message_id=msg2.id,
        citation_index=1,
        source_title="Nature Biotechnology CRISPR Review.pdf",
        page_number=18,
        snippet="Cas9 recognizes the 5'-NGG-3' PAM motif preceding the 20-nucleotide target sequence.",
        relevance_score=0.98,
    )
    db_session.add(cit)
    await db_session.commit()

    # Request Word (.docx) export
    response = await client.get(
        f"/api/v1/chat/conversations/{conv.id}/export?format=docx",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "wordprocessingml.document" in response.headers["content-type"]
    assert "CRISPR_Gene_Editing_Study.docx" in response.headers["content-disposition"]

    docx_bytes = response.content
    assert docx_bytes.startswith(b"PK")  # ZIP container header for DOCX

    # Parse with python-docx to verify document structure
    doc = Document(io.BytesIO(docx_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    assert any("CRISPR Gene Editing Study" in p for p in paragraphs)
    assert any("Research Query" in p for p in paragraphs)
    assert any("Molecular Mechanism" in p for p in paragraphs)

    # Verify table has citations
    assert len(doc.tables) >= 1
    table_text = " ".join([cell.text for tbl in doc.tables for row in tbl.rows for cell in row.cells])
    assert "Nature Biotechnology CRISPR Review.pdf" in table_text
    assert "Page 18" in table_text


@pytest.mark.asyncio
async def test_export_research_report_pdf(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test exporting a comprehensive research report to PDF."""
    report_payload = {
        "title": "Quantum Computing Scalability Analysis",
        "topic": "Superconducting Qubits vs Trapped Ions",
        "executive_summary": "This report synthesizes decoherence rates and gate fidelity benchmarks.",
        "key_findings": [
            "Superconducting qubits achieve sub-10ns gate execution speeds.",
            "Trapped ion systems demonstrate coherence times exceeding one hour.",
            "Surface code quantum error correction requires physical error rates below 1%.",
        ],
        "conclusions": "Hybrid architectures and fault-tolerant logical qubits remain the primary frontier.",
        "limitations": "Cryogenic thermal dissipation limits large-scale dilution refrigerator scalability.",
        "content": (
            "## 1. Architectural Comparison\n\n"
            "Superconducting circuits use Josephson junctions fabricated on silicon substrates.\n\n"
            "### 1.1 Gate Fidelity Analysis\n"
            "- Two-qubit gate error rates have crossed the 99.5% threshold.\n"
            "- Cross-talk cancellation algorithms significantly reduce idle errors.\n\n"
            "> High gate fidelity is a prerequisite for topological code syndromic extraction.\n"
        ),
        "documents": [
            {"id": "doc-1", "filename": "IBM Quantum Review 2024.pdf"},
            {"id": "doc-2", "filename": "IonQ Architecture Whitepaper.pdf"},
        ],
        "citations": [
            {
                "citation_index": 1,
                "source_title": "IBM Quantum Review 2024.pdf",
                "source_url": "https://example.com/ibm-quantum",
                "page_number": 5,
                "snippet": "Coherence times reached 300 microseconds using niobium thin films.",
            },
            {
                "citation_index": 2,
                "source_title": "IonQ Architecture Whitepaper.pdf",
                "source_url": "https://example.com/ionq",
                "page_number": 12,
                "snippet": "Ytterbium-171 ions provide identical, naturally occurring qubit frequencies.",
            },
        ],
    }

    response = await client.post(
        "/api/v1/research/export?format=pdf",
        json=report_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Quantum_Computing_Scalability_Analysis.pdf" in response.headers["content-disposition"]

    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000


@pytest.mark.asyncio
async def test_export_research_report_docx(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test exporting a comprehensive research report to Word (.docx)."""
    report_payload = {
        "title": "Renewable Energy Grid Integration",
        "topic": "Battery Storage vs Pumped Hydro",
        "executive_summary": "Evaluating grid resilience and capital expenditure for long-duration energy storage.",
        "key_findings": [
            "Lithium-iron-phosphate (LFP) batteries dominate short-duration storage under 4 hours.",
            "Pumped-storage hydroelectricity accounts for 90% of global long-duration capacity.",
            "Flow batteries provide degraded-free chemical cycling over 20,000 cycles.",
        ],
        "conclusions": "Multi-day winter deficits necessitate seasonal storage mechanisms.",
        "limitations": "Geographic constraints limit pumped hydro expansion in non-mountainous regions.",
        "content": (
            "# Detailed Analysis\n\n"
            "Energy storage capacity must scale threefold by 2035.\n\n"
            "## Storage Economics\n"
            "Levelized cost of storage (LCOS) continues downward trajectory.\n"
        ),
        "documents": [
            {"id": "doc-a", "filename": "NREL Storage Futures Study.pdf"},
        ],
        "citations": [
            {
                "citation_index": 1,
                "source_title": "NREL Storage Futures Study.pdf",
                "source_url": "https://nrel.gov/storage",
                "page_number": 23,
                "snippet": "Utility-scale 4-hour battery installed costs fell below $250/kWh.",
            }
        ],
    }

    response = await client.post(
        "/api/v1/research/export?format=docx",
        json=report_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "wordprocessingml.document" in response.headers["content-type"]
    assert "Renewable_Energy_Grid_Integration.docx" in response.headers["content-disposition"]

    docx_bytes = response.content
    assert docx_bytes.startswith(b"PK")

    doc = Document(io.BytesIO(docx_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    assert any("Renewable Energy Grid Integration" in p for p in paragraphs)
    assert any("Executive Summary" in p for p in paragraphs)
    assert any("Key Findings" in p for p in paragraphs)
    assert any("Detailed Analysis" in p for p in paragraphs)

    # Verify citation table across all tables in doc
    assert len(doc.tables) >= 2
    all_tables_text = " ".join([cell.text for tbl in doc.tables for row in tbl.rows for cell in row.cells])
    assert "NREL Storage Futures Study.pdf" in all_tables_text
    assert "Page 23" in all_tables_text


@pytest.mark.asyncio
async def test_export_research_comparison_pdf_and_docx(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test exporting a multi-source comparative matrix to both PDF and Word (.docx)."""
    comparison_payload = {
        "title": "Cross-Document Comparison: GPT-4 vs Claude 3.5 vs Gemini 1.5",
        "topic": "Context Window Scaling & Architecture",
        "executive_summary": "Comparative matrix contrasting memory, multimodal capabilities, and long-context retrieval.",
        "key_findings": [
            "Gemini 1.5 achieves 2M token context via multi-needle in a haystack tests.",
            "Claude 3.5 Sonnet demonstrates industry-leading coding benchmarks.",
            "GPT-4o provides real-time voice and vision low latency.",
        ],
        "content": (
            "## 1. Architectural Comparison Matrix\n\n"
            "| Model | Context Window | Architecture | Modality |\n"
            "|---|---|---|---|\n"
            "| GPT-4o | 128k | Dense / MoE | Text/Audio/Vision |\n"
            "| Claude 3.5 Sonnet | 200k | MoE | Text/Vision |\n"
            "| Gemini 1.5 Pro | 2,000k | Sparse MoE | Audio/Video/Text |\n\n"
            "### 1.1 Consensus & Divergence\n"
            "- All models employ Mixture of Experts (MoE).\n"
            "- Retrieval accuracy diverges beyond 500k tokens.\n"
        ),
        "documents": [
            {"id": "doc-1", "filename": "GPT-4 Technical Report.pdf"},
            {"id": "doc-2", "filename": "Gemini 1.5 Architecture Paper.pdf"},
        ],
        "citations": [
            {
                "citation_index": 1,
                "source_title": "Gemini 1.5 Architecture Paper.pdf",
                "page_number": 3,
                "snippet": "Gemini 1.5 Pro maintains >99% recall across 1M token needle tests.",
            }
        ],
    }

    # 1. PDF
    r_pdf = await client.post(
        "/api/v1/research/export?format=pdf",
        json=comparison_payload,
        headers=auth_headers,
    )
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"] == "application/pdf"
    assert r_pdf.content.startswith(b"%PDF-")

    # 2. DOCX
    r_docx = await client.post(
        "/api/v1/research/export?format=docx",
        json=comparison_payload,
        headers=auth_headers,
    )
    assert r_docx.status_code == 200
    assert "wordprocessingml.document" in r_docx.headers["content-type"]
    assert r_docx.content.startswith(b"PK")

    doc = Document(io.BytesIO(r_docx.content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    assert any("Cross-Document Comparison" in p for p in paragraphs)
    assert any("Architectural Comparison Matrix" in p for p in paragraphs)


@pytest.mark.asyncio
async def test_export_invalid_format(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that requesting an invalid export format returns HTTP 400."""
    response = await client.post(
        "/api/v1/research/export?format=invalid_format",
        json={"title": "Test", "content": "Content"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Export format must be" in response.json()["detail"]
