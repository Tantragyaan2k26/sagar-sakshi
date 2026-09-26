"""
SAGAR-SAKSHI End-to-End & API Integration Tests (tests/test_phase0_end_to_end.py)
Tests Phase 0 walking skeleton completion, pipeline execution, and REST endpoints (§10, §12).
"""

from fastapi.testclient import TestClient
import pytest
from api.main import app
from pipeline import run_pipeline


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    """Test health check endpoint."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_api_spatial_layers(client):
    """Layers must belong to a real run; no canned placeholder GeoJSON."""
    assert client.get("/layers/slicks").status_code == 422
    missing = client.get("/layers/slicks", params={"run_id": "no_such_run"})
    assert missing.status_code == 404


def test_pipeline_end_to_end_execution():
    """Phase 0 Acceptance: Pipeline runs end-to-end and produces valid EvidenceCard."""
    card = run_pipeline("config/kerala_2025.yaml", run_id="test_e2e_run_001")

    # Contract assertions
    assert card.run_id == "test_e2e_run_001"
    assert len(card.manifest_sha256) == 64
    assert card.attribution.grade in ["A", "B", "C", "None"]
    assert "U" in card.attribution.posteriors
    assert pytest.approx(sum(card.attribution.posteriors.values()), abs=1e-4) == 1.0


def test_api_run_and_card_retrieval(client):
    """Tests triggering run via API and retrieving JSON and PDF cards."""
    # 1. Trigger run via POST /runs
    post_resp = client.post("/runs", json={"config_path": "config/kerala_2025.yaml", "run_id": "api_test_001"})
    assert post_resp.status_code == 201
    card_data = post_resp.json()
    assert card_data["run_id"] == "api_test_001"

    # Spatial layers must be derived from this run's persisted manifest.
    for layer in ("slicks", "ships", "tracks", "back_region"):
        response = client.get(f"/layers/{layer}", params={"run_id": "api_test_001"})
        assert response.status_code == 200
        assert response.json()["type"] == "FeatureCollection"
        assert response.json()["run_id"] == "api_test_001"
    slick_layer = client.get("/layers/slicks", params={"run_id": "api_test_001"}).json()
    assert slick_layer["features"]
    assert slick_layer["features"][0]["properties"]["score_semantics"].startswith("uncalibrated")

    # 2. Get status via GET /runs/{id}
    status_resp = client.get("/runs/api_test_001")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["run_id"] == "api_test_001"
    assert "shortlist" in status_data

    # 3. Get JSON card via GET /runs/{id}/card?format=json
    card_resp = client.get("/runs/api_test_001/card?format=json")
    assert card_resp.status_code == 200
    assert card_resp.json()["run_id"] == "api_test_001"

    # 4. Get PDF card via GET /runs/{id}/card?format=pdf
    pdf_resp = client.get("/runs/api_test_001/card?format=pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"

    # 5. Record review decision via POST /runs/{id}/review
    review_resp = client.post("/runs/api_test_001/review", json={
        "reviewer_id": "ICG_OFFICER_042",
        "decision": "accept",
        "notes": "Verified against Coast Guard aerial reconnaissance report.",
    })
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "recorded"
