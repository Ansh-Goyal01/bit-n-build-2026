"""Build cleaned, sectioned corpus documents from raw fetched sources."""

import html
import json
import re
from typing import Any

from app.config import settings
from app.ingestion.models import CorpusDoc, Reference
from app.ingestion.schemes import SCHEME_SOURCES


def clean_text(raw: str) -> str:
    """Normalize myScheme markdown: double-escaped HTML entities, <br>, blank runs."""
    text = html.unescape(html.unescape(raw))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _label(node: dict[str, Any] | None) -> str:
    return (node or {}).get("label", "") or ""


def _application_markdown(process_blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in process_blocks:
        mode = block.get("mode", "")
        body = block.get("process_md", "") or ""
        if body.strip():
            parts.append(f"### Application mode: {mode}\n\n{body}")
    return "\n\n".join(parts)


def _faq_markdown(faq_items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in faq_items:
        question = (item.get("question") or "").strip()
        answer = (item.get("answer_md") or "").strip()
        if question and answer:
            parts.append(f"**Q: {question}**\n\nA: {answer}")
    return "\n\n".join(parts)


def corpus_doc_from_bundle(bundle: dict[str, Any]) -> CorpusDoc:
    """Transform one raw myScheme bundle (fetch.py output) into a CorpusDoc."""
    en = bundle["scheme"]["data"]["en"]
    basic = en["basicDetails"]
    content = en.get("schemeContent", {})
    eligibility = en.get("eligibilityCriteria", {})

    documents_md = (
        bundle.get("documents", {}).get("data", {}).get("en", {}).get("documentsRequired_md", "")
        or ""
    )
    faq_items = bundle.get("faqs", {}).get("data", {}).get("en", {}).get("faqs", []) or []

    raw_sections = {
        "details": content.get("detailedDescription_md") or content.get("briefDescription") or "",
        "benefits": content.get("benefits_md") or "",
        "eligibility": eligibility.get("eligibilityDescription_md") or "",
        "exclusions": content.get("exclusions_md") or "",
        "application": _application_markdown(en.get("applicationProcess", []) or []),
        "documents": documents_md,
        "faq": _faq_markdown(faq_items),
    }
    sections = {name: clean_text(text) for name, text in raw_sections.items() if text.strip()}

    references = [
        Reference(title=(ref.get("title") or "Official reference").strip(), url=ref["url"].strip())
        for ref in content.get("references", []) or []
        if ref.get("url")
    ]

    return CorpusDoc(
        scheme_id=bundle["slug"],
        short_name=bundle["short_name"],
        name=basic.get("schemeName", ""),
        category=bundle["category"],
        level=_label(basic.get("level")),
        ministry=_label(basic.get("nodalMinistryName")),
        page_url=bundle["page_url"],
        references=references,
        fetched_at=bundle["fetched_at"],
        sections=sections,
    )


def build_corpus() -> list[CorpusDoc]:
    """Build and persist corpus docs for every scheme with a raw myScheme bundle."""
    from app.ingestion.pdf_corpus import build_pdf_corpus_docs

    settings.corpus_dir.mkdir(parents=True, exist_ok=True)
    docs: list[CorpusDoc] = []
    for source in SCHEME_SOURCES:
        raw_path = settings.raw_dir / f"{source.slug}.json"
        if not raw_path.exists():
            print(f"MISSING raw bundle: {source.slug} — run fetch first")
            continue
        bundle = json.loads(raw_path.read_text(encoding="utf-8"))
        docs.append(corpus_doc_from_bundle(bundle))

    docs.extend(build_pdf_corpus_docs())

    for doc in docs:
        out = settings.corpus_dir / f"{doc.scheme_id}.json"
        out.write_text(doc.model_dump_json(indent=1), encoding="utf-8")
        print(f"CORPUS {doc.scheme_id}: sections={list(doc.sections)}")
    return docs


def load_corpus() -> list[CorpusDoc]:
    """Load persisted corpus docs from data/corpus/."""
    docs = []
    for path in sorted(settings.corpus_dir.glob("*.json")):
        docs.append(CorpusDoc.model_validate_json(path.read_text(encoding="utf-8")))
    return docs
