from datetime import datetime
from unittest.mock import MagicMock, patch

from src.alerts.notifier import AlertDispatcher, QualityAlert
from src.core.models import (
    BatchSummary,
    HealthScore,
    SchemaDriftReport,
    ValidationSeverity,
)


def test_alert_payload_builder():
    dispatcher = AlertDispatcher(channel="#test-alerts")
    alert = QualityAlert(
        title="Test Alert",
        dataset_name="orders",
        batch_id="BATCH-001",
        severity=ValidationSeverity.CRITICAL,
        health_score=82.0,
        error_rate=0.18,
        quarantined_count=18,
        schema_drift_detected=True,
        summary="Critical SLA failure",
    )

    payload = dispatcher.build_slack_payload(alert)
    assert payload["channel"] == "#test-alerts"
    assert len(payload["attachments"]) == 1
    assert payload["attachments"][0]["color"] == "#ff0000"


def test_alert_dispatch_mock():
    dispatcher = AlertDispatcher(webhook_url="https://hooks.slack.com/services/test/mock/url")

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        alert = QualityAlert(
            title="SLA Alert",
            dataset_name="orders",
            batch_id="BATCH-123",
            severity=ValidationSeverity.HIGH,
            health_score=91.0,
            error_rate=0.09,
            quarantined_count=9,
            schema_drift_detected=False,
            summary="SLA threshold breach",
        )

        result = dispatcher.dispatch(alert)
        assert result is True
        mock_post.assert_called_once()
