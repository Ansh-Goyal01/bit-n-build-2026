"""Section-aware chunking: retrieval units that keep their semantic label."""

from app.ingestion.models import Chunk, CorpusDoc

MAX_CHUNK_CHARS = 1400
OVERLAP_CHARS = 150


def _split_long_text(text: str) -> list[str]:
    """Split on paragraph boundaries, packing up to MAX_CHUNK_CHARS with overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= MAX_CHUNK_CHARS or not current:
            current = candidate
        else:
            pieces.append(current)
            current = current[-OVERLAP_CHARS:] + "\n\n" + paragraph
    if current:
        pieces.append(current)
    return pieces


def chunk_section(doc: CorpusDoc, section: str, text: str) -> list[Chunk]:
    header = f"{doc.name} ({doc.short_name}) — {section}"
    pieces = [text] if len(text) <= MAX_CHUNK_CHARS else _split_long_text(text)
    return [
        Chunk(
            chunk_id=f"{doc.scheme_id}:{section}:{i}",
            scheme_id=doc.scheme_id,
            scheme_name=doc.name,
            short_name=doc.short_name,
            section=section,
            text=f"{header}\n\n{piece}",
            source_url=doc.page_url,
            fetched_at=doc.fetched_at,
        )
        for i, piece in enumerate(pieces)
    ]


def chunk_corpus(docs: list[CorpusDoc]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        for section, text in doc.sections.items():
            chunks.extend(chunk_section(doc, section, text))
    return chunks
