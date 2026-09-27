"""Two-stage retrieval: broad dense sweep, then local cross-encoder scheme ranking.

Dense-only retrieval was the pipeline's weakest link (scheme precision ~0.22,
and single-chunk schemes kept sliding out of the top-k). This module retrieves
a broad dense pool, scores every query/chunk pair with a small local
cross-encoder (ONNX, CPU, free), ranks *schemes* by their best-scoring chunk
(max-pooling — no chunk-count bias), and returns the top schemes' best chunks.

Chosen over BM25-hybrid/RRF and plain chunk-top-k reranking on measured
precision AND recall (offline sweep over the eval set; see the vault's
Eval-Results-Log). BM25 fusion actively hurt recall here: profile-summary
queries share incidental vocabulary with every statutory text.
"""

from collections import defaultdict
from functools import lru_cache
from math import exp

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.config import settings
from app.retrieval.search import RetrievedChunk, search

DENSE_POOL_K = 40  # breadth of the dense candidate sweep fed to the cross-encoder
TOP_SCHEMES = 8  # schemes kept, ranked by their single best chunk
CHUNKS_PER_SCHEME = 2  # best chunks carried per kept scheme


@lru_cache(maxsize=1)
def _cross_encoder() -> TextCrossEncoder:
    return TextCrossEncoder(model_name=settings.reranker_model)


def _sigmoid(logit: float) -> float:
    return 1.0 / (1.0 + exp(-logit))


def rank_schemes_by_best_chunk(
    scored_chunks: list[RetrievedChunk],
) -> dict[str, list[RetrievedChunk]]:
    """Group score-descending chunks by scheme, schemes ordered by best chunk.

    Max-pooling: a scheme is as relevant as its single most relevant chunk, so
    one decisive clause (e.g. Sukanya Samriddhi's only rule) outranks a scheme
    with many mediocre matches.
    """
    by_scheme: dict[str, list[RetrievedChunk]] = defaultdict(list)
    for chunk in scored_chunks:  # already sorted desc, so [0] is each scheme's best
        by_scheme[chunk.scheme_id].append(chunk)
    ordered = sorted(by_scheme.items(), key=lambda kv: kv[1][0].score, reverse=True)
    return dict(ordered)


def search_reranked(query: str, k: int = 18) -> list[RetrievedChunk]:
    """Dense pool -> cross-encoder -> scheme-max ranking -> top schemes' chunks.

    Returned scores are sigmoid(cross-encoder logit) in (0, 1), so callers that
    pin must-include chunks at 1.0 keep their guarantee after merging.
    """
    pool = search(query, k=DENSE_POOL_K)
    logits = _cross_encoder().rerank(query, [chunk.text for chunk in pool])
    scored = sorted(
        (
            chunk.model_copy(update={"score": round(_sigmoid(logit), 6)})
            for chunk, logit in zip(pool, logits, strict=True)
        ),
        key=lambda chunk: chunk.score,
        reverse=True,
    )
    by_scheme = rank_schemes_by_best_chunk(scored)
    picked = [
        chunk
        for chunks in list(by_scheme.values())[:TOP_SCHEMES]
        for chunk in chunks[:CHUNKS_PER_SCHEME]
    ]
    return picked[:k]
