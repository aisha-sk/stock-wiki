"""Local MLflow log for one candidate. The web app reads model.json, not the store."""

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

EXPERIMENT = "direction-5d"
TICKET = "F2-ML-1"


def log_candidate(
    *,
    algorithm: str,
    params: dict[str, object],
    metrics: dict[str, float | int],
    baselines: list[dict[str, float | str]] | None = None,
    predictions: pd.DataFrame | None = None,
    model: object | None = None,
    feature_names: list[str] | None = None,
    tickers: list[str] | None = None,
    horizon: int = 5,
    initial_window: int = 252,
    test_block: int = 21,
    purge: int = 5,
    data_end: str = "",
    gate_threshold: float = 0.52,
) -> str | None:
    """Record one walk-forward run. Returns the run id, or None if MLflow cannot start."""
    try:
        import mlflow
        from mlflow.models import infer_signature
    except ImportError:
        return None
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT)
    recorded = {
        "algorithm": algorithm,
        "features": ",".join(feature_names or []),
        "tickers": ",".join(tickers or []),
        "horizon": horizon,
        "initial_window": initial_window,
        "test_block": test_block,
        "purge": purge,
        "data_end": data_end,
        **params,
    }
    logged_metrics = {key: float(value) for key, value in metrics.items()}
    for baseline in baselines or []:
        logged_metrics[f"{baseline['name']}_accuracy"] = float(baseline["directional_accuracy"])
    logged_metrics["gate_threshold"] = float(gate_threshold)
    with mlflow.start_run() as run:
        mlflow.log_params({key: _param(value) for key, value in recorded.items()})
        mlflow.log_metrics(logged_metrics)
        mlflow.set_tags({"git_sha": _git_sha(), "ticket": TICKET})
        if predictions is not None and not predictions.empty:
            _log_prediction_artifacts(predictions)
        if model is not None and feature_names:
            _log_importances(model, feature_names)
            example = _example_frame(model, feature_names)
            if example is not None:
                signature = infer_signature(example, model.predict_proba(example))
                mlflow.xgboost.log_model(model, name="model", signature=signature, input_example=example)
        return run.info.run_id


def _log_prediction_artifacts(predictions: pd.DataFrame) -> None:
    import mlflow

    frame = predictions.copy()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        csv_path = root / "oos_predictions.csv"
        frame.to_csv(csv_path, index=False)
        mlflow.log_artifact(str(csv_path))
        _save_confusion(frame, root / "confusion_matrix.png")
        _save_calibration(frame, root / "calibration.png")
        mlflow.log_artifact(str(root / "confusion_matrix.png"))
        mlflow.log_artifact(str(root / "calibration.png"))


def _save_confusion(predictions: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_true = predictions["y_true"].to_numpy(dtype=int)
    guessed = (predictions["prob_up"].to_numpy(dtype=float) >= 0.5).astype(int)
    matrix = np.zeros((2, 2), dtype=int)
    for truth, guess in zip(y_true, guessed, strict=True):
        matrix[int(truth), int(guess)] += 1
    figure, axis = plt.subplots()
    axis.imshow(matrix, cmap="Blues")
    axis.set_xticks([0, 1], ["down", "up"])
    axis.set_yticks([0, 1], ["down", "up"])
    axis.set_xlabel("Predicted")
    axis.set_ylabel("Actual")
    axis.set_title("Out-of-sample confusion")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def _save_calibration(predictions: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    probability = predictions["prob_up"].to_numpy(dtype=float)
    y_true = predictions["y_true"].to_numpy(dtype=int)
    edges = np.linspace(0.0, 1.0, 6)
    predicted: list[float] = []
    observed: list[float] = []
    for index in range(5):
        if index == 4:
            mask = (probability >= edges[index]) & (probability <= edges[index + 1])
        else:
            mask = (probability >= edges[index]) & (probability < edges[index + 1])
        if int(mask.sum()) == 0:
            continue
        predicted.append(float(probability[mask].mean()))
        observed.append(float(y_true[mask].mean()))
    figure, axis = plt.subplots()
    axis.plot([0, 1], [0, 1], linestyle="--", color="#5B6472")
    if predicted:
        axis.plot(predicted, observed, marker="o", color="#1D4ED8")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.set_xlabel("Predicted probability")
    axis.set_ylabel("Observed frequency")
    axis.set_title("Calibration, 5 bins")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def _log_importances(model: object, feature_names: list[str]) -> None:
    import mlflow

    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return
    frame = pd.DataFrame({"feature": feature_names, "importance": importances})
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "feature_importances.csv"
        frame.to_csv(path, index=False)
        mlflow.log_artifact(str(path))


def _example_frame(model: object, feature_names: list[str]) -> pd.DataFrame | None:
    names = list(getattr(model, "feature_names_in_", feature_names))
    if len(names) != len(feature_names):
        names = feature_names
    return pd.DataFrame([[0.0] * len(names)], columns=names)


def _param(value: object) -> str | int | float:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int | float):
        return value
    return str(value)


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
