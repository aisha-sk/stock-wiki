"""Gate boundary and promotion. No network."""

import numpy as np
from xgboost import XGBClassifier

from ml.gate import failed_checks, passes_gate
from ml.registry import append_version

LAZY = [{"name": "always_quiet", "directional_accuracy": 0.5}]


def test_exact_threshold_passes() -> None:
    assert passes_gate({"directional_accuracy": 0.52}, 0.52, LAZY)
    assert not passes_gate({"directional_accuracy": 0.5199}, 0.52, LAZY)


def test_clearing_the_threshold_but_losing_to_always_quiet_is_rejected() -> None:
    lazy = [{"name": "always_quiet", "directional_accuracy": 0.557}]
    assert failed_checks({"directional_accuracy": 0.5372}, 0.52, lazy) == ["accuracy beats always_quiet"]
    assert not passes_gate({"directional_accuracy": 0.557}, 0.52, lazy)
    assert not passes_gate({"directional_accuracy": 0.6}, 0.52, [])
    versions = append_version(
        [],
        accuracy=0.5372,
        threshold=0.52,
        baselines=lazy,
        algorithm="xgboost",
        model_name="move-xgb",
        trained_at="2026-10-10T22:00:00Z",
        mlflow_run_id="new",
    )
    assert versions[0]["status"] == "rejected"
    assert versions[0]["gate_passed"] is False


def test_shuffled_labels_are_rejected_and_production_is_unchanged() -> None:
    rng = np.random.default_rng(0)
    features = rng.normal(size=(400, 4))
    labels = rng.integers(0, 2, size=400)
    model = XGBClassifier(n_estimators=20, max_depth=2, random_state=0, n_jobs=1)
    model.fit(features[:300], labels[:300])
    guessed = model.predict(features[300:])
    accuracy = float(np.mean(guessed == labels[300:]))
    assert accuracy < 0.52

    production = {
        "version": "1",
        "model_name": "direction-xgb",
        "algorithm": "xgboost",
        "trained_at": "2026-10-01T00:00:00Z",
        "directional_accuracy": 0.6,
        "gate_passed": True,
        "status": "production",
        "mlflow_run_id": "kept",
    }
    versions = append_version(
        [production],
        accuracy=accuracy,
        threshold=0.52,
        baselines=LAZY,
        algorithm="xgboost",
        model_name="direction-xgb",
        trained_at="2026-10-10T00:00:00Z",
        mlflow_run_id="new",
    )

    assert versions[0]["status"] == "rejected"
    assert versions[0]["gate_passed"] is False
    assert versions[1]["status"] == "production"
    assert versions[1]["directional_accuracy"] == 0.6
    assert versions[1]["mlflow_run_id"] == "kept"


def test_a_better_candidate_archives_the_previous_production() -> None:
    production = {
        "version": "1",
        "model_name": "direction-xgb",
        "algorithm": "xgboost",
        "trained_at": "2026-10-01T00:00:00Z",
        "directional_accuracy": 0.53,
        "gate_passed": True,
        "status": "production",
        "mlflow_run_id": "old",
    }
    versions = append_version(
        [production],
        accuracy=0.55,
        threshold=0.52,
        baselines=LAZY,
        algorithm="xgboost",
        model_name="direction-xgb",
        trained_at="2026-10-10T00:00:00Z",
        mlflow_run_id="new",
    )

    assert versions[0]["status"] == "production"
    assert versions[0]["version"] == "2"
    assert versions[1]["status"] == "archived"
    assert versions[1]["directional_accuracy"] == 0.53


def test_a_passer_that_does_not_beat_production_is_archived() -> None:
    production = {
        "version": "1",
        "model_name": "direction-xgb",
        "algorithm": "xgboost",
        "trained_at": "2026-10-01T00:00:00Z",
        "directional_accuracy": 0.6,
        "gate_passed": True,
        "status": "production",
        "mlflow_run_id": "old",
    }
    versions = append_version(
        [production],
        accuracy=0.54,
        threshold=0.52,
        baselines=LAZY,
        algorithm="xgboost",
        model_name="direction-xgb",
        trained_at="2026-10-10T00:00:00Z",
        mlflow_run_id="new",
    )

    assert versions[0]["status"] == "archived"
    assert versions[1]["status"] == "production"


def test_an_identical_rerun_does_not_rewrite_history() -> None:
    existing = {
        "version": "4",
        "model_name": "direction-xgb",
        "algorithm": "xgboost",
        "trained_at": "2026-10-10T21:00:00Z",
        "directional_accuracy": 0.4955,
        "gate_passed": False,
        "status": "rejected",
        "mlflow_run_id": "kept",
        "task": "move",
    }
    versions = append_version(
        [existing],
        accuracy=0.4955357,
        threshold=0.52,
        baselines=LAZY,
        algorithm="xgboost",
        model_name="direction-xgb",
        trained_at="2026-10-10T22:00:00Z",
        mlflow_run_id="new",
    )

    assert len(versions) == 1
    assert versions[0]["version"] == existing["version"]
    assert versions[0]["directional_accuracy"] == existing["directional_accuracy"]
    assert versions[0]["mlflow_run_id"] == "kept"


def test_a_move_model_is_appended_beside_a_direction_row_with_the_same_accuracy() -> None:
    existing = {
        "version": "7",
        "model_name": "direction-xgb",
        "algorithm": "xgboost",
        "trained_at": "2026-10-10T21:00:00Z",
        "directional_accuracy": 0.4955,
        "gate_passed": False,
        "status": "rejected",
        "mlflow_run_id": "old",
        "task": "direction",
    }
    versions = append_version(
        [existing],
        accuracy=0.4955,
        threshold=0.52,
        baselines=LAZY,
        algorithm="xgboost",
        model_name="move-xgb",
        trained_at="2026-10-10T22:00:00Z",
        mlflow_run_id="new",
    )

    assert versions[0]["version"] == "8"
    assert versions[0]["task"] == "move"
    assert versions[1]["task"] == "direction"
    assert versions[1]["directional_accuracy"] == 0.4955
