"""Append-only model history. Older accuracies are left as they were."""

from ml.gate import passes_gate


def append_version(
    prior: list[dict],
    *,
    accuracy: float,
    threshold: float,
    algorithm: str,
    model_name: str,
    trained_at: str,
    mlflow_run_id: str | None,
) -> list[dict]:
    """Return versions newest first.

    An identical algorithm and accuracy is not appended again. A passing
    candidate becomes production only when it is at least as accurate as the
    current production version. The previous production row becomes archived.
    """
    published = round(float(accuracy), 4)
    newest = prior[0] if prior else None
    if (
        newest is not None
        and newest.get("algorithm") == algorithm
        and float(newest["directional_accuracy"]) == published
    ):
        return [dict(item) for item in prior]

    passed = passes_gate({"directional_accuracy": published}, threshold)
    production = next((item for item in prior if item.get("status") == "production"), None)
    if not passed:
        status = "rejected"
    elif production is None or published >= float(production["directional_accuracy"]):
        status = "production"
    else:
        status = "archived"
    version = str(1 + max((int(item["version"]) for item in prior), default=0))
    row = {
        "version": version,
        "model_name": model_name,
        "algorithm": algorithm,
        "trained_at": trained_at,
        "directional_accuracy": published,
        "gate_passed": passed,
        "status": status,
        "mlflow_run_id": mlflow_run_id,
    }
    kept: list[dict] = []
    for item in prior:
        copy = dict(item)
        if status == "production" and copy.get("status") == "production":
            copy["status"] = "archived"
        kept.append(copy)
    return [row, *kept]


def register_mlflow_model(run_id: str | None) -> None:
    """Register the logged model as ``direction-5d``. A file-store refusal is not fatal."""
    if not run_id:
        return
    try:
        import mlflow
    except ImportError:
        return
    try:
        mlflow.register_model(f"runs:/{run_id}/model", "direction-5d")
    except mlflow.MlflowException as exc:
        print(f"MLflow model registry skipped: {exc}", flush=True)
