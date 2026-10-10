"""Analyst consensus formula. No network."""

from ml.ingest.analysts import analyst_score


def test_analyst_score_matches_the_contract_formula() -> None:
    score = analyst_score(strong_buy=4, buy=15, hold=21, sell=2, strong_sell=2)

    assert score == 19


def test_analyst_score_is_none_when_nobody_rated() -> None:
    assert analyst_score(strong_buy=0, buy=0, hold=0, sell=0, strong_sell=0) is None
