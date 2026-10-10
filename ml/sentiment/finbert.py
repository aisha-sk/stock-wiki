"""FinBERT title scores. The model is loaded once per process."""

_classifier: object | None = None


def score_titles(titles: list[str], *, batch_size: int = 16) -> list[int]:
    """Score headlines on CPU. ``score = round((P(positive) - P(negative)) * 100)``."""
    if not titles:
        return []
    classifier = _get_classifier()
    outputs = classifier(
        list(titles),
        batch_size=batch_size,
        truncation=True,
        max_length=128,
        top_k=None,
    )
    if outputs and isinstance(outputs[0], dict):
        outputs = [outputs]
    return [score_from_probabilities(item) for item in outputs]


def score_from_probabilities(rows: list[dict]) -> int:
    by_label = {str(row["label"]).lower(): float(row["score"]) for row in rows}
    value = (by_label.get("positive", 0.0) - by_label.get("negative", 0.0)) * 100
    rounded = round(value)
    return max(-100, min(100, rounded))


def _get_classifier() -> object:
    global _classifier
    if _classifier is None:
        from transformers import pipeline

        _classifier = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            truncation=True,
            device=-1,
        )
    return _classifier
