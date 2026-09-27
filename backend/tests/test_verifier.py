"""The verifier is the trust boundary: unverifiable claims must never survive."""

from app.agent.nodes import verify_and_compose
from app.agent.state import Citation, Reason, SchemeAssessment
from app.retrieval.search import RetrievedChunk


def chunk(chunk_id: str, scheme_id: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        scheme_id=scheme_id,
        scheme_name="Scheme",
        short_name="S",
        section="eligibility",
        text=text,
        source_url="https://example.gov.in/s",
        score=0.9,
    )


def make_state(assessment: SchemeAssessment) -> dict:
    return {
        "retrieved": [
            chunk("pm-kisan:eligibility:0", "pm-kisan", "All landholding farmers' families are eligible.")
        ],
        "assessments": [assessment],
    }


def test_verified_quote_survives():
    assessment = SchemeAssessment(
        scheme_id="pm-kisan",
        verdict="eligible",
        summary="You qualify.",
        reasons=[
            Reason(
                text="You own farmland.",
                citations=[
                    Citation(chunk_id="pm-kisan:eligibility:0", quote="landholding farmers' families")
                ],
            )
        ],
    )
    result = verify_and_compose(make_state(assessment))["results"][0]
    assert result.verdict == "eligible"
    assert result.dropped_claims == 0
    assert result.reasons[0].citations[0].source_url.startswith("https://")


def test_fabricated_quote_is_dropped_and_verdict_downgraded():
    assessment = SchemeAssessment(
        scheme_id="pm-kisan",
        verdict="eligible",
        summary="You qualify.",
        reasons=[
            Reason(
                text="You get 10,000 rupees per month.",
                citations=[
                    Citation(chunk_id="pm-kisan:eligibility:0", quote="10,000 rupees every month for all")
                ],
            )
        ],
    )
    result = verify_and_compose(make_state(assessment))["results"][0]
    assert result.verdict == "need_more_info"  # never asserts an unverified entitlement
    assert result.reasons == []
    assert result.dropped_claims >= 1


def test_citation_to_unknown_chunk_is_dropped():
    assessment = SchemeAssessment(
        scheme_id="pm-kisan",
        verdict="not_eligible",
        summary="You don't qualify.",
        reasons=[
            Reason(
                text="Excluded category.",
                citations=[Citation(chunk_id="pm-kisan:exclusions:9", quote="landholding farmers' families")],
            )
        ],
    )
    result = verify_and_compose(make_state(assessment))["results"][0]
    assert result.verdict == "need_more_info"
    assert result.dropped_claims >= 1


def test_unknown_scheme_id_is_ignored():
    assessment = SchemeAssessment(
        scheme_id="invented-scheme", verdict="eligible", summary="x", reasons=[]
    )
    results = verify_and_compose(make_state(assessment))["results"]
    assert results == []
