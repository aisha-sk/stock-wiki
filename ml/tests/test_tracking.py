"""MLflow logging. Uses a temporary file store, not the repo mlruns directory."""

import pandas as pd
import pytest
from xgboost import XGBClassifier

from ml.tracking import EXPERIMENT, log_candidate


def test_log_candidate_records_a_comparable_run(tmp_path, monkeypatch) -> None:
    pytest.importorskip("mlflow")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tmp_path.as_uri())
    frame = pd.DataFrame({"ret_1d": [0.1, -0.2, 0.3, -0.1, 0.2, -0.3], "y": [1, 0, 1, 0, 1, 0]})
    model = XGBClassifier(n_estimators=2, max_depth=1, random_state=0, n_jobs=1)
    model.fit(frame[["ret_1d"]], frame["y"])
    predictions = pd.DataFrame(
        {"y_true": [1, 0, 1, 0, 1, 0], "prob_up": [0.8, 0.2, 0.7, 0.3, 0.6, 0.4]}
    )

    run_id = log_candidate(
        algorithm="xgboost",
        params={"n_estimators": 2, "max_depth": 1},
        metrics={"directional_accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5, "n_test": 6},
        baselines=[
            {"name": "always_up", "directional_accuracy": 0.5},
            {"name": "previous_direction", "directional_accuracy": 0.4},
        ],
        predictions=predictions,
        model=model,
        feature_names=["ret_1d"],
        tickers=["TSLA"],
        data_end="2026-10-09",
        gate_threshold=0.52,
    )

    assert run_id
    import mlflow
    from mlflow.tracking import MlflowClient

    client = MlflowClient()
    recorded = client.get_run(run_id)
    assert recorded.info.experiment_id == client.get_experiment_by_name(EXPERIMENT).experiment_id
    assert recorded.data.params["algorithm"] == "xgboost"
    assert recorded.data.params["tickers"] == "TSLA"
    assert recorded.data.metrics["always_up_accuracy"] == 0.5
    assert recorded.data.metrics["gate_threshold"] == 0.52
    assert recorded.data.tags["ticket"] == "F2-ML-1"
    names = {item.path for item in client.list_artifacts(run_id)}
    assert {"oos_predictions.csv", "confusion_matrix.png", "calibration.png", "feature_importances.csv"} <= names
    logged_models = client.search_logged_models(experiment_ids=[recorded.info.experiment_id])
    assert any(item.name == "model" for item in logged_models)
    mlflow.end_run()
