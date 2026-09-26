"""
SAGAR-SAKSHI FastAPI REST API Service (api/main.py)
Exposes the multi-sensor attribution engine via standard OpenAPI REST endpoints (§10).
No frontend rendering logic; delivers strictly JSON, GeoJSON, and PDF artifacts.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from api.schemas import EvidenceCard, AttributionResult
from pipeline import run_pipeline
from fastapi.staticfiles import StaticFiles
from data_layer.database import db
from alerts.notification_gateway import alert_gateway


app = FastAPI(
    title="SAGAR-SAKSHI Maritime Attribution API",
    description="Prototype API for synthetic/default SAR and AIS attribution workflow runs.",
    version="1.0.0",
)

if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# In-memory store for prototype run cache
RUNS_STORE: dict[str, EvidenceCard] = {}
REVIEW_LOG: list[dict[str, Any]] = []



class RunRequest(BaseModel):
    config_path: str = Field("config/kerala_2025.yaml", description="Path to incident YAML configuration")
    run_id: str | None = Field(None, description="Optional custom run ID")


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(..., description="Analyst badge/ID")
    decision: Literal["accept", "reject", "inconclusive"]
    notes: str | None = None


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "SAGAR-SAKSHI Backend Pipeline",
        "version": "1.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/runs", response_model=EvidenceCard, status_code=201)
def trigger_run(payload: RunRequest):
    """
    POST /runs
    Starts a new attribution pipeline run from an incident configuration file.
    """
    if not os.path.exists(payload.config_path):
        raise HTTPException(status_code=404, detail=f"Config file not found: {payload.config_path}")

    try:
        card = run_pipeline(config_path=payload.config_path, run_id=payload.run_id)
        RUNS_STORE[card.run_id] = card
        db.save_run(card.model_dump(mode="json"))
        return card
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failure: {str(e)}")


@app.get("/runs/{run_id}")
def get_run_status(run_id: str):
    """
    GET /runs/{id}
    Returns run status, evidence grade, and top suspect shortlist.
    """
    card = RUNS_STORE.get(run_id)
    if not card:
        saved = db.get_run(run_id)
        if saved:
            card = EvidenceCard(**saved)
            RUNS_STORE[run_id] = card
    if not card:
        # Check if saved artifact exists on disk in runs/
        card_file = os.path.join("runs", f"{run_id}_evidence_card.json")
        if os.path.exists(card_file):
            with open(card_file, "r") as f:
                data = json.load(f)
            card = EvidenceCard(**data)
            RUNS_STORE[run_id] = card
        else:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    attr = card.attribution
    # Shortlist summary
    shortlist = [
        {"hypothesis": h, "posterior": p}
        for h, p in sorted(attr.posteriors.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "run_id": card.run_id,
        "grade": attr.grade,
        "headline": attr.headline,
        "manifest_sha256": card.manifest_sha256,
        "ais_status": card.ais_status,
        "shortlist": shortlist,
        "generated_at_utc": card.generated_at_utc,
    }


@app.get("/runs/{run_id}/card")
def get_run_evidence_card(run_id: str, format: Literal["json", "pdf"] = "json"):
    """
    GET /runs/{id}/card
    Returns a prototype JSON EvidenceCard or downloadable PDF report.
    """
    if format == "pdf":
        pdf_path = os.path.join("runs", f"{run_id}_evidence_card.pdf")
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"PDF evidence card for '{run_id}' not found.")
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"SAGAR_SAKSHI_{run_id}_EvidenceCard.pdf",
        )

    # Return JSON card
    card = RUNS_STORE.get(run_id)
    if not card:
        saved = db.get_run(run_id)
        if saved:
            card = EvidenceCard(**saved)
            RUNS_STORE[run_id] = card
    if not card:
        card_file = os.path.join("runs", f"{run_id}_evidence_card.json")
        if os.path.exists(card_file):
            with open(card_file, "r") as f:
                data = json.load(f)
            return JSONResponse(content=data)
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    return card


@app.get("/runs/{run_id}/manifest")
def get_run_manifest(run_id: str):
    """Returns the persisted provenance manifest for a pipeline run."""
    if os.path.basename(run_id) != run_id or run_id in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid run ID")
    manifest_path = os.path.join("runs", f"{run_id}_manifest.json")
    if not os.path.isfile(manifest_path):
        raise HTTPException(status_code=404, detail=f"Manifest for run '{run_id}' not found.")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return JSONResponse(content=json.load(f))


@app.get("/layers/{name}")
def get_spatial_layer(
    name: Literal["slicks", "ships", "tracks", "back_region"],
    run_id: str = Query(..., description="Run whose recorded outputs should be returned"),
):
    """Return GeoJSON generated by one run; never substitute illustrative data."""
    if os.path.basename(run_id) != run_id or run_id in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid run ID")
    manifest_path = os.path.join("runs", f"{run_id}_manifest.json")
    if not os.path.isfile(manifest_path):
        raise HTTPException(status_code=404, detail=f"Run manifest '{run_id}' not found.")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    outputs = manifest.get("outputs", {}).get("stage_outputs", {})
    features: list[dict[str, Any]] = []

    if name == "slicks":
        for slick in outputs.get("slicks", []):
            features.append({
                "type": "Feature", "geometry": slick.get("polygon"),
                "properties": {
                    "slick_id": slick.get("slick_id"),
                    "candidate_class": slick.get("lookalike_class"),
                    "heuristic_score": slick.get("p_oil"),
                    "score_semantics": "uncalibrated heuristic, not an oil probability",
                    "synthetic_sar": manifest.get("outputs", {}).get("run_summary", {}).get("sar_synthetic"),
                },
            })
    elif name == "ships":
        for ship in outputs.get("ship_detections", []):
            point = ship.get("point")
            if point and len(point) == 2:
                features.append({
                    "type": "Feature", "geometry": {"type": "Point", "coordinates": [point[1], point[0]]},
                    "properties": {"detection_id": ship.get("detection_id"), "p_vessel": ship.get("p_vessel"), "vessel_class": ship.get("vessel_class")},
                })
    elif name == "back_region":
        region = outputs.get("back_region")
        if region:
            geometry = region.get("envelope_polygon") if isinstance(region, dict) else None
            if geometry:
                features.append({"type": "Feature", "geometry": geometry, "properties": {"source": "run_output", "run_id": run_id}})
    else:
        records = manifest.get("inputs", {}).get("ais_messages", {}).get("value", [])
        grouped: dict[str, list[dict[str, Any]]] = {}
        for message in records:
            vessel_id = str(message.get("mmsi") or message.get("vessel_name") or "unknown")
            grouped.setdefault(vessel_id, []).append(message)
        for vessel_id, messages in grouped.items():
            messages.sort(key=lambda item: item.get("timestamp_utc", ""))
            coordinates = [[item["lon"], item["lat"]] for item in messages if "lon" in item and "lat" in item]
            if len(coordinates) >= 2:
                features.append({
                    "type": "Feature", "geometry": {"type": "LineString", "coordinates": coordinates},
                    "properties": {
                        "vessel_id": vessel_id, "vessel_name": messages[0].get("vessel_name"),
                        "data_status": "source_csv_unverified" if any(m.get("data_status") == "historical_csv_input_unverified" for m in messages) else "synthetic_demo",
                    },
                })
    return {"type": "FeatureCollection", "features": features, "run_id": run_id, "layer": name}


@app.post("/runs/{run_id}/review")
def record_analyst_review(run_id: str, payload: ReviewRequest):
    """
    POST /runs/{id}/review
    Records an analyst's accept/reject verification decision (§10).
    """
    if not db.get_run(run_id):
        card = RUNS_STORE.get(run_id)
        card_file = os.path.join("runs", f"{run_id}_evidence_card.json")
        if card:
            db.save_run(card.model_dump(mode="json"))
        elif os.path.isfile(card_file):
            with open(card_file, "r", encoding="utf-8") as f:
                db.save_run(json.load(f))
        else:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    record = db.record_review(run_id, payload.reviewer_id, payload.decision, payload.notes)
    REVIEW_LOG.append(record)
    card = RUNS_STORE.get(run_id)
    if card is None:
        saved = db.get_run(run_id)
        card = EvidenceCard(**saved) if saved else None
    if card is None:
        return {"status": "recorded", "review_entry": record, "alert": {"status": "suppressed", "reason": "Run output unavailable."}}
    candidates = [(h, p) for h, p in card.attribution.posteriors.items() if h != "U"]
    top_vessel = max(candidates, key=lambda item: item[1])[0] if candidates else None
    alert = alert_gateway.dispatch_incident_alert(
        incident_id=str(card.metadata.get("incident_id") or run_id),
        run_id=run_id,
        reviewer_id=payload.reviewer_id,
        review_decision=payload.decision,
        grade=card.attribution.grade,
        headline=card.attribution.headline,
        top_vessel=top_vessel,
    )
    return {"status": "recorded", "review_entry": record, "alert": alert}


@app.get("/runs/{run_id}/reviews")
def list_analyst_reviews(run_id: str):
    """Lists persisted analyst review entries for a run."""
    if not db.get_run(run_id):
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return {"run_id": run_id, "reviews": db.list_reviews_for_run(run_id)}
