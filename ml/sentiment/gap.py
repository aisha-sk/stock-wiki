"""Perspective gap across the sentiment sources that are present."""

_DISPLAY = {
    "analysts": "Wall Street analysts",
    "news": "News media",
    "reddit": "Reddit",
}


def gap_for(sources: list[dict]) -> dict | None:
    """``None`` when fewer than two sources are present.

    The summary never uses buy or sell language.
    """
    if len(sources) < 2:
        return None
    ordered = sorted(sources, key=lambda source: int(source["score"]))
    bearish = ordered[0]
    bullish = ordered[-1]
    points = int(bullish["score"]) - int(bearish["score"])
    if points < 20:
        summary = "The available groups are close together."
    else:
        summary = (
            f"{_DISPLAY[bullish['source']]} lean bullish while "
            f"{_DISPLAY[bearish['source']]} lean bearish."
        )
    return {
        "points": points,
        "most_bullish": bullish["source"],
        "most_bearish": bearish["source"],
        "summary": summary,
    }
