import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"


def example(relative: str) -> dict:
    return json.loads((EXAMPLES / relative).read_text())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("DATA_DIR", "contracts/examples")
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def data_copy(tmp_path, monkeypatch) -> Path:
    """A writable copy of the fixtures, with DATA_DIR pointed at it."""
    target = tmp_path / "data"
    shutil.copytree(EXAMPLES, target)
    monkeypatch.setenv("DATA_DIR", str(target))
    return target
