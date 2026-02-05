# RAG Knowledge Base Platform

Phase 0 setup for a solo-dev build using:
FastAPI, Postgres, Qdrant, Redis, Docker, OpenSearch, Cron, MinIO, Kafka, API Gateway, LLM Gateway, OpenTelemetry, Datadog.

## Repo Structure (initial)

- `services/ingestion`
- `services/indexer`
- `services/query-api`
- `services/rerank`
- `services/llm-gateway`
- `infra/docker-compose`

## Start Local Infra

```bash
docker compose -f infra/docker-compose/docker-compose.yml up -d
```

## Phase 1: Ingestion Service

The ingestion service runs at `http://localhost:8001` when the compose stack is up.

### Webhook ingest

```bash
curl -X POST http://localhost:8001/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_a",
    "source": "manual",
    "source_id": "doc_001",
    "content_type": "text/plain",
    "content": "Hello RAG",
    "metadata": {"tag": "demo"}
  }'
```

### Pull ingest

```bash
curl -X POST http://localhost:8001/pull \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_a",
    "source": "example_api",
    "source_id": "doc_002",
    "url": "https://example.com/doc2.txt"
  }'
```

### Cron runner (example)

```bash
python services/ingestion/cron_runner.py \
  --api http://localhost:8001 \
  --jobs services/ingestion/jobs.sample.json
```

## Notes

- OpenSearch may require `vm.max_map_count=262144` on the host.
- Ingestion service is included in the compose stack for Phase 1.
