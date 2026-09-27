"""Semantic search over the Chroma corpus index (BGE-small query embeddings)."""

from functools import lru_cache

import chromadb
from fastembed import TextEmbedding
from pydantic import BaseModel

from app.config import settings
from app.ingestion.index import COLLECTION_NAME


class RetrievedChunk(BaseModel):
    chunk_id: str
    scheme_id: str
    scheme_name: str
    short_name: str
    section: str
    text: str
    source_url: str
    score: float


@lru_cache(maxsize=1)
def _embedder() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model)


@lru_cache(maxsize=1)
def _collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_collection(COLLECTION_NAME)


def _to_chunks(
    ids: list[str], docs: list[str], metas: list[dict], scores: list[float]
) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            scheme_id=meta["scheme_id"],
            scheme_name=meta["scheme_name"],
            short_name=meta["short_name"],
            section=meta["section"],
            text=doc,
            source_url=meta["source_url"],
            score=score,
        )
        for chunk_id, doc, meta, score in zip(ids, docs, metas, scores, strict=True)
    ]


def search(query: str, k: int = 18) -> list[RetrievedChunk]:
    """Top-k semantic search across the whole corpus."""
    vector = next(iter(_embedder().query_embed(query))).tolist()
    result = _collection().query(query_embeddings=[vector], n_results=k)
    return _to_chunks(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        [1.0 - d for d in result["distances"][0]],
    )


def get_sections(scheme_id: str, sections: list[str]) -> list[RetrievedChunk]:
    """Fetch specific sections of a scheme directly (used to guarantee the
    eligibility/exclusions text of every candidate scheme reaches the LLM)."""
    result = _collection().get(
        where={"$and": [{"scheme_id": scheme_id}, {"section": {"$in": sections}}]}
    )
    return _to_chunks(
        result["ids"], result["documents"], result["metadatas"], [1.0] * len(result["ids"])
    )
