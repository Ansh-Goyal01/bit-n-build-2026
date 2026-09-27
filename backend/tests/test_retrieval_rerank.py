"""Two-stage retrieval: dense pool -> cross-encoder -> scheme-max selection."""

import pytest

from app.retrieval.rerank import rank_schemes_by_best_chunk
from app.retrieval.search import RetrievedChunk


def chunk(chunk_id: str, scheme_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        scheme_id=scheme_id,
        scheme_name=scheme_id,
        short_name=scheme_id,
        section="eligibility",
        text="text",
        source_url="https://example.gov.in",
        score=score,
    )


def test_scheme_with_one_decisive_chunk_outranks_many_mediocre_ones():
    scored = [
        chunk("ssy-1", "sukanya-samriddhi", 0.9),
        chunk("pension-1", "ignwps", 0.6),
        chunk("pension-2", "ignwps", 0.59),
        chunk("pension-3", "ignwps", 0.58),
        chunk("pension-4", "ignwps", 0.57),
    ]
    ordered = list(rank_schemes_by_best_chunk(scored))
    assert ordered == ["sukanya-samriddhi", "ignwps"]


def test_chunks_stay_grouped_and_sorted_within_scheme():
    scored = [
        chunk("a-1", "apy", 0.8),
        chunk("b-1", "pmsby", 0.7),
        chunk("a-2", "apy", 0.5),
    ]
    by_scheme = rank_schemes_by_best_chunk(scored)
    assert [c.chunk_id for c in by_scheme["apy"]] == ["a-1", "a-2"]
    assert list(by_scheme) == ["apy", "pmsby"]


@pytest.mark.slow
def test_reranked_search_surfaces_the_right_scheme():
    """The FN-class probe: a savings-account query for a young daughter must
    keep Sukanya Samriddhi among the retrieved schemes, ahead of the pension
    schemes that dominated dense-only retrieval."""
    from app.retrieval.rerank import CHUNKS_PER_SCHEME, TOP_SCHEMES, search_reranked

    hits = search_reranked(
        "eligibility for government welfare schemes: female, daughter aged 9, "
        "Mother of a 9-year-old girl.",
        k=18,
    )
    schemes = [c.scheme_id for c in hits]
    assert "sukanya-samriddhi" in schemes
    assert len(set(schemes)) <= TOP_SCHEMES
    per_scheme = {s: schemes.count(s) for s in schemes}
    assert max(per_scheme.values()) <= CHUNKS_PER_SCHEME
    # scores are sigmoid-normalized so downstream section-guarantee chunks
    # (pinned at 1.0) always sort above reranked ones
    assert all(0.0 <= c.score <= 1.0 for c in hits)
