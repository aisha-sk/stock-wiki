"""Local MLflow log for one candidate. The web app reads model.json, not the store."""

import os
from pathlib import Path

_EXPERIMENT = "sentifi-direction"


def log_candidate(
    *,
    algorithm: str,
    params: dict[str, object],
    metrics: dict[str, float | int],
) -> str | None:
    """Record one walk-forward run. Returns the run id, or None if MLflow cannot start."""
    try:
        import mlflow
    except ImportError:
        return None
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    tracking_dir = Path(__file__).resolve().parents[1] / "mlruns"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment(_EXPERIMENT)
    with mlflow.start_run() as run:
        mlflow.log_params({key: value for key, value in params.items()})
        mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
        return run.info.run_id
