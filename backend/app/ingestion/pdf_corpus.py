"""Corpus builders for the two schemes sourced from official PDFs.

- Sukanya Samriddhi: text-layer extraction from the gazette notification
  (Sukanya Samriddhi Account Scheme, 2019), sectioned by its numbered clauses.
- PMS-SC: the official guidelines PDF is a scan; we ingest a Gemini-transcribed
  markdown (see transcribe.py) that was human spot-checked against the PDF.
"""

import re

from pypdf import PdfReader

from app.config import settings
from app.ingestion.models import CorpusDoc, Reference
from app.ingestion.schemes import PDF_SOURCES, PdfSource

# --- Sukanya Samriddhi (gazette clauses -> corpus sections) ---

SSY_SECTION_BY_CLAUSE = {
    1: "details",  # Short title and commencement
    2: "details",  # Definitions
    3: "eligibility",  # Opening of account (girl child < 10, two per family...)
    4: "benefits",  # Deposits
    5: "benefits",  # Interest on deposit
    6: "application",  # Operation of account
    7: "benefits",  # Premature closure
    8: "benefits",  # Withdrawal
    9: "benefits",  # Closure on maturity
    10: "details",  # Application of General Rules
    11: "details",  # Power to relax
}

_CLAUSE_START = re.compile(r"\n\s*(\d{1,2})\.\s+(?=[A-Z])")


def _strip_gazette_noise(text: str) -> str:
    """Drop running headers, page numbers, and mangled-Devanagari header lines."""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or re.fullmatch(r"\d+", stripped):
            continue
        if "GAZETTE OF INDIA" in stripped or "EXTRAORDINARY" in stripped:
            continue
        non_ascii = sum(1 for ch in stripped if ord(ch) > 127)
        if non_ascii / len(stripped) > 0.3:
            continue
        kept.append(line)
    return "\n".join(kept)


def _ssy_sections(pdf_text: str) -> dict[str, str]:
    start = pdf_text.find("G.S.R.")
    if start == -1:
        raise ValueError("SSY gazette: English notification start (G.S.R.) not found")
    body = pdf_text[start:]
    form_start = re.search(r"\bFORM\s*-?\s*1\b", body)
    if form_start:
        body = body[: form_start.start()]
    body = _strip_gazette_noise(body)

    matches = list(_CLAUSE_START.finditer(body))
    sections: dict[str, list[str]] = {}
    preamble = body[: matches[0].start()].strip() if matches else body.strip()
    if preamble:
        sections.setdefault("details", []).append(preamble)
    for i, match in enumerate(matches):
        clause_no = int(match.group(1))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        clause_text = body[match.start() : end].strip()
        section = SSY_SECTION_BY_CLAUSE.get(clause_no)
        if section:
            sections.setdefault(section, []).append(clause_text)
    return {name: "\n\n".join(parts) for name, parts in sections.items()}


# --- PMS-SC (transcribed guidelines markdown -> corpus sections) ---

PMS_SC_HEADING_TO_SECTION = [
    ("objective", "details"),
    ("scope", "details"),
    ("eligibility", "eligibility"),
    ("conditions", "eligibility"),
    ("value of scholarship", "benefits"),
    ("scholarship amount", "benefits"),
    ("academic allowance", "benefits"),
    ("duration", "benefits"),
    ("procedure", "application"),
    ("application", "application"),
    ("documents", "documents"),
]


def _pms_sc_sections(markdown: str) -> dict[str, str]:
    """Bucket transcript blocks by their nearest markdown heading."""
    sections: dict[str, list[str]] = {}
    current = "details"
    for block in markdown.split("\n\n"):
        heading = re.match(r"\s{0,3}#{1,4}\s*(.+)", block)
        if heading:
            title = heading.group(1).lower()
            for needle, section in PMS_SC_HEADING_TO_SECTION:
                if needle in title:
                    current = section
                    break
        sections.setdefault(current, []).append(block.strip())
    return {name: "\n\n".join(parts).strip() for name, parts in sections.items() if parts}


def _doc_from_sections(source: PdfSource, sections: dict[str, str], note: str) -> CorpusDoc:
    return CorpusDoc(
        scheme_id=source.scheme_id,
        short_name=source.short_name,
        name=source.name,
        category=source.category,
        level="Central",
        ministry=note,
        page_url=source.page_url,
        references=[Reference(title="Official scheme document (PDF)", url=source.pdf_url)],
        fetched_at="2026-07-10",
        sections=sections,
    )


def build_pdf_corpus_docs() -> list[CorpusDoc]:
    docs: list[CorpusDoc] = []
    for source in PDF_SOURCES:
        if source.scheme_id == "sukanya-samriddhi":
            pdf_path = settings.raw_dir / "sukanya-samriddhi.pdf"
            text = "\n".join(
                page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages
            )
            docs.append(
                _doc_from_sections(
                    source, _ssy_sections(text), "Ministry of Finance (Department of Posts)"
                )
            )
        elif source.scheme_id == "pms-sc":
            transcript = settings.raw_dir / "pms-sc-transcript.md"
            if not transcript.exists():
                print("MISSING pms-sc-transcript.md — run `python -m app.ingestion.transcribe`")
                continue
            docs.append(
                _doc_from_sections(
                    source,
                    _pms_sc_sections(transcript.read_text(encoding="utf-8")),
                    "Ministry of Social Justice and Empowerment",
                )
            )
    return docs
