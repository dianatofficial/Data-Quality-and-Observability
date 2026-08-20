import json
import logging
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from src.core.models import BatchSummary, ValidationSeverity

logger = logging.getLogger("DataQualityAlerts")


class QualityAlert(BaseModel):
    """Structured notification alert."""

    title: str
    dataset_name: str
    batch_id: str
    severity: ValidationSeverity
    health_score: float
    error_rate: float
    quarantined_count: int
    schema_drift_detected: bool
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertDispatcher:
    """Dispatches data quality and SLA alerts to Slack / Webhooks."""

    def __init__(self, webhook_url: Optional[str] = None, channel: str = "#data-ops-alerts"):
        self.webhook_url = webhook_url or ""
        self.channel = channel

    def build_slack_payload(self, alert: QualityAlert) -> Dict[str, Any]:
        color = "#36a64f"  # Green
        if alert.severity == ValidationSeverity.CRITICAL or alert.health_score < 90.0:
            color = "#ff0000"  # Red
        elif alert.severity in (ValidationSeverity.HIGH, ValidationSeverity.MEDIUM):
            color = "#ff9900"  # Orange

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alert.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Dataset:*\n`{alert.dataset_name}`"},
                    {"type": "mrkdwn", "text": f"*Batch ID:*\n`{alert.batch_id}`"},
                    {"type": "mrkdwn", "text": f"*Health Score:*\n*{alert.health_score}%*"},
                    {"type": "mrkdwn", "text": f"*Quarantined Records:*\n*{alert.quarantined_count}*"},
                    {"type": "mrkdwn", "text": f"*Error Rate:*\n*{alert.error_rate * 100:.2f}%*"},
                    {"type": "mrkdwn", "text": f"*Schema Drift:*\n*{'⚠️ YES' if alert.schema_drift_detected else '✅ NO'}*"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Root Cause / Summary:*\n{alert.summary}",
                },
            },
        ]

        return {
            "channel": self.channel,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ],
        }

    def dispatch(self, alert: QualityAlert) -> bool:
        payload = self.build_slack_payload(alert)

        if not self.webhook_url:
            logger.info("Slack webhook unconfigured. Simulating alert delivery: %s", json.dumps(payload))
            return True

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )
            if response.status_code == 200:
                logger.info("Alert successfully dispatched to Slack for batch %s", alert.batch_id)
                return True
            else:
                logger.error("Failed to post alert to Slack: %s %s", response.status_code, response.text)
                return False
        except Exception as e:
            logger.error("Exception during alert dispatch: %s", str(e))
            return False

    def notify_batch_evaluation(self, summary: BatchSummary) -> bool:
        if not summary.sla_breached and summary.quarantined_records == 0:
            # All clean, only notify if explicit info logging
            return True

        title = "Data Quality Gatekeeper Alert"
        severity = ValidationSeverity.HIGH
        if summary.sla_breached:
            title = "CRITICAL: SLA Breached at Data Quality Gate"
            severity = ValidationSeverity.CRITICAL

        summary_text = (
            f"Gatekeeper intercepted {summary.quarantined_records} non-compliant records. "
            f"Pass rate: {summary.pass_rate}%. Overall health: {summary.health_score.overall_score}%."
        )
        if summary.schema_drift.detected:
            summary_text += f" Schema drift detected: {summary.schema_drift.summary}"

        alert = QualityAlert(
            title=title,
            dataset_name=summary.dataset_name,
            batch_id=summary.batch_id,
            severity=severity,
            health_score=summary.health_score.overall_score,
            error_rate=summary.error_rate,
            quarantined_count=summary.quarantined_records,
            schema_drift_detected=summary.schema_drift.detected,
            summary=summary_text,
        )

        return self.dispatch(alert)
