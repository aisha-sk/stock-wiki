"""Gap wording. No network."""

from ml.sentiment.gap import gap_for


def _source(name: str, score: int) -> dict:
    return {"source": name, "score": score}


def test_gap_with_three_two_and_one_sources() -> None:
    three = gap_for([_source("analysts", 40), _source("news", 10), _source("reddit", -20)])
    two = gap_for([_source("news", 12), _source("reddit", 4)])
    one = gap_for([_source("news", 12)])

    assert three is not None
    assert three["points"] == 60
    assert three["most_bullish"] == "analysts"
    assert three["most_bearish"] == "reddit"
    assert "buy" not in three["summary"].lower()
    assert "sell" not in three["summary"].lower()
    assert "lean bullish" in three["summary"]
    assert two is not None
    assert two["points"] == 8
    assert "close together" in two["summary"]
    assert one is None
