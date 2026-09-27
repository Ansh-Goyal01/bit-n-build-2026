"""Corpus data models shared by ingestion, retrieval, and (later) rules."""

from pydantic import BaseModel


class Reference(BaseModel):
    """An official document linked from a scheme page (guidelines PDF etc.)."""

    title: str
    url: str


class CorpusDoc(BaseModel):
    """One scheme's cleaned official content, sectioned."""

    scheme_id: str
    short_name: str
    name: str
    category: str
    level: str
    ministry: str
    page_url: str
    references: list[Reference]
    fetched_at: str
    # section name -> cleaned markdown (details, benefits, eligibility,
    # exclusions, application, documents, faq)
    sections: dict[str, str]


class Chunk(BaseModel):
    """An indexed retrieval unit. Every chunk knows its official source URL."""

    chunk_id: str
    scheme_id: str
    scheme_name: str
    short_name: str
    section: str
    text: str
    source_url: str
    fetched_at: str
