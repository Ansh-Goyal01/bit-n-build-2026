"""Feedback endpoint — PII-free issue reports appended to disk."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "feedback_dir", tmp_path)
    return TestClient(app)


def _read_records(tmp_path):
    path = tmp_path / "feedback.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_accepts_report_and_appends_jsonl(client, tmp_path):
    response = client.post(
        "/api/feedback",
        json={
            "category": "wrong_verdict",
            "scheme_id": "pm-kisan",
            "message": "The land-ownership rule seems wrong for tenant farmers.",
            "lang": "hi",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    records = _read_records(tmp_path)
    assert len(records) == 1
    assert records[0]["category"] == "wrong_verdict"
    assert records[0]["scheme_id"] == "pm-kisan"
    assert records[0]["lang"] == "hi"
    assert "ts" in records[0]


def test_rejects_unknown_category(client):
    response = client.post(
        "/api/feedback",
        json={"category": "spam", "message": "hello there"},
    )
    assert response.status_code == 422


def test_rejects_overlong_message(client):
    response = client.post(
        "/api/feedback",
        json={"category": "other", "message": "x" * 2001},
    )
    assert response.status_code == 422


def test_redacts_accidental_pii_from_message(client, tmp_path):
    response = client.post(
        "/api/feedback",
        json={
            "category": "other",
            "message": "Call me at 9876543210 or mail me@example.com about PMAY.",
        },
    )
    assert response.status_code == 200
    (record,) = _read_records(tmp_path)
    assert "9876543210" not in record["message"]
    assert "me@example.com" not in record["message"]
    assert "PMAY" in record["message"]


def test_no_profile_or_contact_fields_accepted(client, tmp_path):
    """Extra fields (a profile, a name) must never be stored."""
    response = client.post(
        "/api/feedback",
        json={
            "category": "other",
            "message": "Verdict text overlaps on small screens.",
            "profile": {"age": 44},
            "name": "Ansh",
        },
    )
    assert response.status_code == 200
    (record,) = _read_records(tmp_path)
    assert "profile" not in record
    assert "name" not in record
