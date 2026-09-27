"""The scoring policy is the experiment's referee — pin it down."""

from evals.metrics import retrieval_metrics, score_case, summarize


def outcomes_by_scheme(outcomes):
    return {o.scheme_id: o.outcome for o in outcomes}


def test_gold_eligible_scoring():
    gold = {"eligible": ["a", "b", "c", "d"], "not_eligible": [], "need_info": []}
    predicted = {"a": "eligible", "b": "not_eligible", "c": "need_more_info"}
    result = outcomes_by_scheme(score_case("t", gold, predicted))
    assert result == {"a": "correct", "b": "fn", "c": "abstain", "d": "fn"}


def test_gold_not_eligible_scoring_absent_is_correct():
    gold = {"eligible": [], "not_eligible": ["a", "b", "c"], "need_info": []}
    predicted = {"a": "likely_eligible", "b": "not_eligible"}
    result = outcomes_by_scheme(score_case("t", gold, predicted))
    assert result == {"a": "fp", "b": "correct", "c": "correct"}


def test_gold_need_info_scoring():
    gold = {"eligible": [], "not_eligible": [], "need_info": ["a", "b"]}
    predicted = {"a": "eligible", "b": "need_more_info"}
    result = outcomes_by_scheme(score_case("t", gold, predicted))
    assert result == {"a": "fp", "b": "correct"}


def test_summarize_counts():
    gold = {"eligible": ["a"], "not_eligible": ["b"], "need_info": []}
    summary = summarize(score_case("t", gold, {"a": "eligible", "b": "eligible"}))
    assert summary["pairs"] == 2
    assert summary["accuracy"] == 0.5
    assert summary["false_positives"] == 1


def test_retrieval_metrics():
    precision, recall = retrieval_metrics({"a", "b"}, {"a", "c", "d"})
    assert precision == 1 / 3
    assert recall == 1 / 2
