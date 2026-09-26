from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import database, main, repository
from app.config import DEMO_DIR
from app.retrieval import retrieve


@pytest.fixture
def demo_client(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "devpilot-test.db")
    monkeypatch.setattr(main, "STORAGE_DIR", storage)
    monkeypatch.setattr(repository, "STORAGE_DIR", storage)
    with TestClient(main.app) as client:
        response = client.post("/api/repositories/demo")
        assert response.status_code == 200
        yield client, response.json(), storage


def test_demo_repository_returns_metadata_without_local_paths_or_code_index(demo_client):
    _, repo, _ = demo_client
    assert repo["file_count"] >= 8
    assert "root" not in repo
    assert "chunks" not in repo
    assert "snippet_index" not in repo


def test_python_index_has_symbol_chunks_and_precise_retrieval():
    metadata = repository.analyze_path(DEMO_DIR, "sample", "demo/sample-repository", "test-repo")

    auth_chunks = [chunk for chunk in metadata["chunks"] if chunk["file_path"] == "backend/auth.py"]
    match = next(item for item in retrieve(metadata, "find account email", limit=8)
                 if item["file"] == "backend/auth.py" and item["symbol"] == "find_account")
    assert any(chunk["symbol"] == "find_account" and chunk["chunk_type"] == "function" for chunk in auth_chunks)
    assert match["line_start"] == 4
    assert match["line_end"] == 9


def test_issue_to_verified_fix_requires_approval_and_preserves_source(demo_client):
    client, repo, storage = demo_client
    source_file = storage / "demo-devpilot" / "backend" / "auth.py"
    original_source = source_file.read_text(encoding="utf-8")

    created = client.post("/api/workflow/investigate", json={
        "repository_id": repo["id"], "issue_number": 1,
    })
    assert created.status_code == 200
    workflow = created.json()
    workflow_id = workflow["workflow_id"]
    assert workflow["investigation"]["affected_symbols"] == ["find_account"]
    assert workflow["investigation"]["evidence"][0]["line_start"] == 4

    workflow = client.post(f"/api/workflow/{workflow_id}/plan", json={}).json()
    assert workflow["status"] == "PLANNED"
    workflow = client.post(f"/api/workflow/{workflow_id}/patch").json()
    assert "unified_diff" in workflow["patch"]
    assert workflow["patch"]["applied_to_repository"] is False
    workflow = client.post(f"/api/workflow/{workflow_id}/test").json()
    assert workflow["status"] == "WAITING_FOR_APPROVAL"

    blocked = client.post(f"/api/workflow/{workflow_id}/verify")
    assert blocked.status_code == 409
    client.post(f"/api/workflow/{workflow_id}/approve", json={"approved": True})
    workflow = client.post(f"/api/workflow/{workflow_id}/verify").json()
    assert workflow["verification"]["before"]["status"] == "FAIL"
    assert workflow["verification"]["after"]["status"] == "PASS", workflow["verification"]["after"]["stderr"]
    assert source_file.read_text(encoding="utf-8") == original_source

    workflow = client.post(f"/api/workflow/{workflow_id}/review").json()
    assert workflow["status"] == "REVIEWED"
    assert workflow["final_status"] == "READY_FOR_HUMAN_REVIEW"
    persisted = client.get(f"/api/workflow/{workflow_id}").json()
    assert persisted["verification"]["status"] == "PASS"


def test_workflow_missing_id_and_invalid_investigation_are_clear(demo_client):
    client, repo, _ = demo_client
    assert client.get("/api/workflow/wf_missing").status_code == 404
    response = client.post("/api/workflow/investigate", json={"repository_id": repo["id"]})
    assert response.status_code == 422


def test_anonymous_workflows_reject_user_supplied_issue_content(demo_client):
    client, repo, _ = demo_client
    response = client.post("/api/workflow/investigate", json={
        "repository_id": repo["id"], "origin": "manual", "issue_title": "private title",
        "issue_body": "private issue body", "issue_number": 42,
    })
    assert response.status_code == 503
    assert client.get("/api/workflow").json() == []


def test_anonymous_zip_upload_is_disabled_until_user_ownership_exists(demo_client):
    client, _, _ = demo_client
    response = client.post("/api/repositories/upload", files={"file": ("repo.zip", b"not actually read")})
    assert response.status_code == 503
    assert "ownership" in response.json()["detail"]
