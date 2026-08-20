from datetime import datetime
from sqlalchemy.orm import Session

from src.core.models import (
    QuarantineRecord,
    RuleViolation,
    ValidationSeverity,
    ValidationStatus,
)
from src.storage.repositories import DataWarehouseRepository, QuarantineRepository


def test_quarantine_save_and_retrieve(db_session: Session):
    q_repo = QuarantineRepository(db_session)

    violation = RuleViolation(
        rule_name="not_null_check",
        column="order_id",
        rule_type="not_null",
        severity=ValidationSeverity.CRITICAL,
        message="Primary key is missing",
        actual_value=None,
        expected="non-null",
    )

    record = QuarantineRecord(
        quarantine_id="QR-TEST001",
        batch_id="BATCH-001",
        entity_type="orders",
        record_index=0,
        raw_payload={"order_id": None, "total_amount": 100},
        violations=[violation],
        severity=ValidationSeverity.CRITICAL,
        status=ValidationStatus.QUARANTINED,
    )

    inserted = q_repo.save_quarantine_records([record])
    assert inserted == 1

    records = q_repo.get_quarantined_records(status="QUARANTINED")
    assert len(records) == 1
    assert records[0]["quarantine_id"] == "QR-TEST001"
    assert records[0]["severity"] == "CRITICAL"
    assert len(records[0]["violations"]) == 1


def test_quarantine_status_update_and_audit(db_session: Session):
    q_repo = QuarantineRepository(db_session)

    record = QuarantineRecord(
        quarantine_id="QR-TEST002",
        batch_id="BATCH-002",
        entity_type="orders",
        record_index=1,
        raw_payload={"order_id": "ORD-TEST002", "total_amount": -10},
        violations=[],
        severity=ValidationSeverity.HIGH,
        status=ValidationStatus.QUARANTINED,
    )
    q_repo.save_quarantine_records([record])

    success = q_repo.update_status(
        quarantine_id="QR-TEST002",
        new_status=ValidationStatus.RECONCILED,
        notes="Approved after manual verification of refund transaction",
        actor="DATA_ENGINEER_LEAD",
    )
    assert success is True

    reconciled = q_repo.get_quarantined_records(status="RECONCILED")
    assert len(reconciled) == 1
    assert reconciled[0]["quarantine_id"] == "QR-TEST002"
    assert reconciled[0]["resolution_notes"] == "Approved after manual verification of refund transaction"
