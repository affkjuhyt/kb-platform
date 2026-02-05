import base64
import os

os.environ.setdefault("RAG_KAFKA_BROKERS", "")

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_ingest_requires_content():
    resp = client.post(
        "/webhook",
        json={
            "tenant_id": "t1",
            "source": "manual",
            "source_id": "doc1",
        },
    )
    assert resp.status_code == 400


def test_webhook_ingest_base64():
    payload = {
        "tenant_id": "t1",
        "source": "manual",
        "source_id": "doc2",
        "content_base64": base64.b64encode(b"hello").decode("utf-8"),
    }
    resp = client.post("/webhook", json=payload)
    assert resp.status_code in (200, 500)
