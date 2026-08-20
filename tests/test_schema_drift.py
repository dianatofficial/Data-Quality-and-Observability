from src.core.drift import SchemaDriftDetector


def test_schema_drift_exact_match():
    expected_schema = {
        "order_id": str,
        "customer_id": str,
        "total_amount": float,
    }
    detector = SchemaDriftDetector(dataset_name="orders", expected_schema=expected_schema)

    records = [
        {"order_id": "ORD-1", "customer_id": "CUST-1", "total_amount": 99.5},
        {"order_id": "ORD-2", "customer_id": "CUST-2", "total_amount": 150.0},
    ]

    report = detector.detect(records)
    assert report.detected is False
    assert report.drift_score == 0.0
    assert len(report.missing_columns) == 0
    assert len(report.unexpected_columns) == 0


def test_schema_drift_missing_and_unexpected_columns():
    expected_schema = {
        "order_id": str,
        "customer_id": str,
        "total_amount": float,
    }
    detector = SchemaDriftDetector(dataset_name="orders", expected_schema=expected_schema)

    # Missing total_amount, added unexpected price_gross and new_field
    records = [
        {"order_id": "ORD-1", "customer_id": "CUST-1", "price_gross": 99.5, "new_field": "test"},
    ]

    report = detector.detect(records)
    assert report.detected is True
    assert "total_amount" in report.missing_columns
    assert "price_gross" in report.unexpected_columns
    assert "new_field" in report.unexpected_columns
    assert report.drift_score > 0.0
