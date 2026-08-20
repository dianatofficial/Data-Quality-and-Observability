from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.core.models import (
    QuarantineRecord,
    RecordValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class QuarantineManager:
    """Manages isolation, categorization, and remediation lifecycle of non-compliant records."""

    @staticmethod
    def create_quarantine_records(
        batch_id: str,
        entity_type: str,
        failed_results: List[RecordValidationResult],
    ) -> List[QuarantineRecord]:
        quarantine_records: List[QuarantineRecord] = []

        for res in failed_results:
            if res.is_valid:
                continue

            # Determine maximum severity
            max_sev = res.max_severity or ValidationSeverity.HIGH

            record = QuarantineRecord(
                quarantine_id=f"QR-{uuid4().hex[:10].upper()}",
                batch_id=batch_id,
                entity_type=entity_type,
                record_index=res.record_index,
                raw_payload=res.raw_payload,
                violations=res.violations,
                severity=max_sev,
                status=ValidationStatus.QUARANTINED,
                quarantined_at=datetime.utcnow(),
            )
            quarantine_records.append(record)

        return quarantine_records

    @staticmethod
    def resolve_record(
        record: QuarantineRecord,
        action: ValidationStatus,
        notes: str,
        patched_payload: Optional[Dict[str, Any]] = None,
    ) -> QuarantineRecord:
        """Mark a quarantined record as resolved (RECONCILED or DROPPED)."""
        record.status = action
        record.resolved_at = datetime.utcnow()
        record.resolution_notes = notes
        if patched_payload:
            record.raw_payload = patched_payload
        return record
