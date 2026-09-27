"""Embed corpus chunks with BGE-small (fastembed/ONNX) and index them in Chroma."""

import contextlib

import chromadb
from fastembed import TextEmbedding

from app.config import settings
from app.ingestion.chunk import chunk_corpus
from app.ingestion.corpus import load_corpus

COLLECTION_NAME = "adhikaar_corpus"


def get_client() -> chromadb.ClientAPI:
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def build_index() -> int:
    """(Re)build the Chroma collection from data/corpus/. Returns chunk count."""
    docs = load_corpus()
    if not docs:
        raise RuntimeError("No corpus docs found — run `python -m app.ingestion build` first")
    chunks = chunk_corpus(docs)

    embedder = TextEmbedding(model_name=settings.embedding_model)
    vectors = [v.tolist() for v in embedder.embed([c.text for c in chunks], batch_size=32)]

    client = get_client()
    with contextlib.suppress(Exception):  # collection may not exist yet
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c.chunk_id for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[
            {
                "scheme_id": c.scheme_id,
                "scheme_name": c.scheme_name,
                "short_name": c.short_name,
                "section": c.section,
                "source_url": c.source_url,
                "fetched_at": c.fetched_at,
            }
            for c in chunks
        ],
    )
    print(f"INDEX: {len(chunks)} chunks from {len(docs)} schemes -> {settings.chroma_dir}")
    return len(chunks)
