# api

FastAPI service that serves the artifact JSON in `DATA_DIR`, unchanged. Lane: SWE.
Shapes and rules are in `../docs/CONTRACT.md`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

| File | Role |
|---|---|
| `app/main.py` | Routes and CORS |
| `app/store.py` | Reads a file from `DATA_DIR`, validates it, caches by mtime |
| `app/schemas.py` | Pydantic mirrors of `../contracts/schemas` |
| `app/errors.py` | The single error shape |

`DATA_DIR` is resolved from the repo root. It defaults to `contracts/examples` (fake data) and
is read from the environment or the repo-root `.env`. Tests: `pytest`. Lint: `ruff check .`
