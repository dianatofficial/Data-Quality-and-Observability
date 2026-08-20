from datetime import datetime
from pathlib import Path

from src.core.metrics import QualityMetricsCalculator
from src.core.models import (
    BatchSummary,
    HealthScore,
    RecordValidationResult,
    RuleViolation,
    SchemaDriftReport,
    ValidationSeverity,
)
from src.core.reporter import DataDocsReporter


def test_metrics_calculator():
    calc = QualityMetricsCalculator(min_sla_score=95.0, max_error_rate=0.05)

    raw_records = [
        {"order_id": "ORD-1", "customer_id": "CUST-1", "total_amount": 100},
        {"order_id": "ORD-2", "customer_id": "CUST-2", "total_amount": 200},
    ]

    val_results = [
        RecordValidationResult(record_index=0, is_valid=True, raw_payload=raw_records[0]),
        RecordValidationResult(record_index=1, is_valid=True, raw_payload=raw_records[1]),
    ]

    score = calc.calculate(raw_records, val_results, primary_key="order_id")
    assert score.completeness == 100.0
    assert score.validity == 100.0
    assert score.uniqueness == 100.0
    assert score.overall_score == 100.0
    assert score.sla_passed is True


def test_data_docs_reporter(tmp_path: Path):
    reporter = DataDocsReporter(output_dir=tmp_path)

    health_score = HealthScore(
        completeness=98.0,
        validity=96.0,
        uniqueness=100.0,
        timeliness=100.0,
        consistency=100.0,
        overall_score=98.1,
        sla_passed=True,
    )

    drift = SchemaDriftReport(
        dataset_name="orders",
        detected=False,
        summary="No drift",
    )

    summary = BatchSummary(
        batch_id="BATCH-TEST-DOCS",
        dataset_name="orders",
        total_records=100,
        passed_records=96,
        quarantined_records=4,
        pass_rate=96.0,
        error_rate=0.04,
        health_score=health_score,
        schema_drift=drift,
        processing_duration_ms=12.5,
        executed_at=datetime.utcnow(),
        sla_breached=False,
    )

    html_content = reporter.generate_html(summary)
    assert "Data Quality Certificate" in html_content
    assert "BATCH-TEST-DOCS" in html_content
    assert "98.1%" in html_content

    file_path = reporter.export_to_file(summary)
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == html_content
