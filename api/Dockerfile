# Build from the repo root, so the image holds the API, the contract and the published data:
#   docker build -f api/Dockerfile -t stocksense-api .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY api/requirements-prod.txt api/requirements-prod.txt
RUN pip install --no-cache-dir -r api/requirements-prod.txt

COPY api/app api/app
# The optional explainer. It only runs when ANTHROPIC_API_KEY is set.
COPY agent agent
COPY contracts contracts
COPY data/artifacts data/artifacts

# Real pipeline output, not the demo fixtures. Alert sign-ups go to a writable path;
# on a free host this file is lost on every redeploy.
ENV DATA_DIR=data/artifacts \
    ALERTS_DB=/tmp/alerts.db

RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8000
# Hosts such as Render inject PORT.
CMD ["sh", "-c", "uvicorn app.main:app --app-dir api --host 0.0.0.0 --port ${PORT:-8000}"]
