"""Prototype alert gate with dry-run-only dispatch in the current app."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Literal
from data_layer.database import db

logger = logging.getLogger("sagar_sakshi_alerts")


class NotificationGateway:
    """Dispatches regulatory maritime alerts post-analyst review."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.dispatched_alerts: list[dict[str, Any]] = []

    def dispatch_incident_alert(
        self,
        incident_id: str,
        run_id: str,
        reviewer_id: str,
        review_decision: Literal["accept", "reject", "inconclusive"],
        grade: str,
        headline: str,
        top_vessel: str | None = None,
        contacts: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Enforces the architectural guarantee:
        'alerts per incident, only after review via SMS / mail gateway'
        """
        # Strict enforcement: Never send an alert unless the analyst explicitly accepted the lead!
        if review_decision != "accept":
            return {
                "status": "suppressed",
                "reason": f"Alert dispatch suppressed: Analyst review decision was '{review_decision}' (requires 'accept').",
                "incident_id": incident_id,
            }

        if grade not in ["A", "B"]:
            return {
                "status": "suppressed",
                "reason": f"Alert dispatch suppressed: Evidence Grade '{grade}' does not meet high-confidence threshold (requires Grade A or B).",
                "incident_id": incident_id,
            }

        recipients = contacts or [
            "ops.icg@gov.in",
            "cochin.port@nic.in",
            "spill-response.incois@gov.in",
        ]

        now_utc = datetime.now(timezone.utc).isoformat()
        payload = {
            "alert_id": f"ALT_{incident_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "incident_id": incident_id,
            "run_id": run_id,
            "reviewer_id": reviewer_id,
            "evidence_grade": grade,
            "headline": headline,
            "top_suspect": top_vessel,
            "timestamp_utc": now_utc,
            "channels": ["SMS_GATEWAY", "MAIL_GATEWAY", "REST_WEBHOOK"],
            "recipients": recipients,
            "status": "dispatched" if not self.dry_run else "simulated_sent",
        }

        self.dispatched_alerts.append(payload)
        logger.info(f"[ALERT DISPATCHED] Incident: {incident_id} | Grade: {grade} | Reviewer: {reviewer_id}")

        return payload


alert_gateway = NotificationGateway(dry_run=True)
