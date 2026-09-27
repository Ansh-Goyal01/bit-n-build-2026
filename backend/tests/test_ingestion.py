"""Unit tests for corpus cleaning, sectioning, and chunking."""

from app.ingestion.chunk import MAX_CHUNK_CHARS, chunk_corpus, chunk_section
from app.ingestion.corpus import clean_text, corpus_doc_from_bundle
from app.ingestion.models import CorpusDoc


def make_doc(sections: dict[str, str]) -> CorpusDoc:
    return CorpusDoc(
        scheme_id="test-scheme",
        short_name="TS",
        name="Test Scheme",
        category="test",
        level="Central",
        ministry="Ministry of Testing",
        page_url="https://example.gov.in/schemes/test-scheme",
        references=[],
        fetched_at="2026-07-10",
        sections=sections,
    )


def test_clean_text_unescapes_double_encoded_entities():
    assert clean_text("the &amp;quot;PM-KISAN&amp;quot; scheme") == 'the "PM-KISAN" scheme'


def test_clean_text_strips_br_and_collapses_blank_lines():
    assert clean_text("a<br>\n\n\n\nb <BR/>") == "a\n\nb"


def test_chunk_small_section_is_single_chunk_with_header_and_metadata():
    doc = make_doc({"eligibility": "Must be over 60 years of age."})
    chunks = chunk_section(doc, "eligibility", doc.sections["eligibility"])

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "test-scheme:eligibility:0"
    assert chunk.section == "eligibility"
    assert chunk.source_url == "https://example.gov.in/schemes/test-scheme"
    assert "Test Scheme (TS) — eligibility" in chunk.text
    assert "over 60 years" in chunk.text


def test_chunk_long_section_splits_and_covers_all_content():
    paragraphs = [f"Paragraph {i}: " + ("detail " * 60) for i in range(10)]
    doc = make_doc({"faq": "\n\n".join(paragraphs)})
    chunks = chunk_section(doc, "faq", doc.sections["faq"])

    assert len(chunks) > 1
    header_len = len(f"{doc.name} ({doc.short_name}) — faq\n\n")
    assert all(len(c.text) <= MAX_CHUNK_CHARS + header_len + 200 for c in chunks)
    joined = "".join(c.text for c in chunks)
    assert all(f"Paragraph {i}:" in joined for i in range(10))


def test_chunk_corpus_covers_every_section():
    doc = make_doc({"eligibility": "e", "benefits": "b", "documents": "d"})
    chunks = chunk_corpus([doc])
    assert {c.section for c in chunks} == {"eligibility", "benefits", "documents"}


def test_corpus_doc_from_bundle_maps_sections_and_references():
    bundle = {
        "slug": "test-scheme",
        "short_name": "TS",
        "category": "test",
        "page_url": "https://example.gov.in/schemes/test-scheme",
        "fetched_at": "2026-07-10",
        "scheme": {
            "data": {
                "en": {
                    "basicDetails": {
                        "schemeName": "Test Scheme",
                        "level": {"label": "Central"},
                        "nodalMinistryName": {"label": "Ministry of Testing"},
                    },
                    "schemeContent": {
                        "detailedDescription_md": "About the scheme.",
                        "benefits_md": "&amp;#8377;6000 per year",
                        "exclusions_md": "Income tax payers.",
                        "references": [
                            {"title": "Guidelines", "url": "https://example.gov.in/g.pdf "}
                        ],
                    },
                    "eligibilityCriteria": {
                        "eligibilityDescription_md": "All landholding farmers."
                    },
                    "applicationProcess": [
                        {"mode": "Online", "process_md": "Apply on the portal."}
                    ],
                }
            }
        },
        "documents": {"data": {"en": {"documentsRequired_md": "1. Aadhaar Card."}}},
        "faqs": {"data": {"en": {"faqs": [{"question": "Who?", "answer_md": "Farmers."}]}}},
    }

    doc = corpus_doc_from_bundle(bundle)

    assert doc.ministry == "Ministry of Testing"
    assert doc.sections["eligibility"] == "All landholding farmers."
    assert doc.sections["exclusions"] == "Income tax payers."
    assert "₹6000" in doc.sections["benefits"]
    assert "Application mode: Online" in doc.sections["application"]
    assert "Aadhaar Card" in doc.sections["documents"]
    assert "**Q: Who?**" in doc.sections["faq"]
    assert doc.references[0].url == "https://example.gov.in/g.pdf"
