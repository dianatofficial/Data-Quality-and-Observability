from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.core.engine import GatekeeperEngine
from src.core.models import (
    BatchSummary,
    QuarantineRecord,
    ValidationStatus,
)
from src.ingestion.generator import EnterpriseDataGenerator


class LiveSimulationEngine:
    """In-memory enterprise simulation state engine for cloud preview and zero-dependency mode."""

    def __init__(self):
        self.engine = GatekeeperEngine()
        self.batch_history: List[Dict[str, Any]] = []
        self.clean_orders: List[Dict[str, Any]] = []
        self.quarantine_store: List[QuarantineRecord] = []
        self.audit_log: List[Dict[str, Any]] = []
        self.latest_summary: Optional[BatchSummary] = None
        self._seed_initial_state()

    def _seed_initial_state(self) -> None:
        """Bootstrap realistic multi-day historical baseline metrics."""
        base_time = datetime.utcnow() - timedelta(days=7)

        for i in range(10):
            batch_time = base_time + timedelta(hours=i * 14)
            corruption_rate = 0.02 if i % 4 != 0 else 0.18
            records = EnterpriseDataGenerator.generate_corrupted_orders(
                total_count=120, corruption_rate=corruption_rate
            )
            batch_id = f"BATCH-HIST-{1000 + i}"

            summary, clean, quarantined = self.engine.process_batch(
                dataset_name="orders",
                records=records,
                batch_id=batch_id,
            )
            summary.executed_at = batch_time

            self.batch_history.append({
                "batch_id": summary.batch_id,
                "dataset_name": summary.dataset_name,
                "total_records": summary.total_records,
                "passed_records": summary.passed_records,
                "quarantined_records": summary.quarantined_records,
                "pass_rate": summary.pass_rate,
                "error_rate": summary.error_rate,
                "completeness": summary.health_score.completeness,
                "validity": summary.health_score.validity,
                "uniqueness": summary.health_score.uniqueness,
                "timeliness": summary.health_score.timeliness,
                "consistency": summary.health_score.consistency,
                "overall_health_score": summary.health_score.overall_score,
                "sla_breached": summary.sla_breached,
                "processing_duration_ms": summary.processing_duration_ms,
                "schema_drift_detected": summary.schema_drift.detected,
                "schema_drift_score": summary.schema_drift.drift_score,
                "executed_at": summary.executed_at,
            })

            self.clean_orders.extend(clean)
            self.quarantine_store.extend(quarantined)
            self.latest_summary = summary

    def run_simulation_batch(
        self, batch_type: str = "mixed", total_records: int = 100
    ) -> BatchSummary:
        """Simulate execution of an incoming batch and update state."""
        batch_id = f"BATCH-SIM-{uuid4().hex[:8].upper()}"

        if batch_type == "clean":
            records = EnterpriseDataGenerator.generate_clean_orders(total_records)
        elif batch_type == "drifted":
            records = EnterpriseDataGenerator.generate_drifted_orders(total_records)
        else:  # mixed / corrupted
            records = EnterpriseDataGenerator.generate_corrupted_orders(
                total_count=total_records, corruption_rate=0.22
            )

        summary, clean, quarantined = self.engine.process_batch(
            dataset_name="orders",
            records=records,
            batch_id=batch_id,
        )

        self.clean_orders.extend(clean)
        self.quarantine_store.extend(quarantined)
        self.latest_summary = summary

        self.batch_history.append({
            "batch_id": summary.batch_id,
            "dataset_name": summary.dataset_name,
            "total_records": summary.total_records,
            "passed_records": summary.passed_records,
            "quarantined_records": summary.quarantined_records,
            "pass_rate": summary.pass_rate,
            "error_rate": summary.error_rate,
            "completeness": summary.health_score.completeness,
            "validity": summary.health_score.validity,
            "uniqueness": summary.health_score.uniqueness,
            "timeliness": summary.health_score.timeliness,
            "consistency": summary.health_score.consistency,
            "overall_health_score": summary.health_score.overall_score,
            "sla_breached": summary.sla_breached,
            "processing_duration_ms": summary.processing_duration_ms,
            "schema_drift_detected": summary.schema_drift.detected,
            "schema_drift_score": summary.schema_drift.drift_score,
            "executed_at": summary.executed_at,
        })

        return summary

    def get_quarantine_records(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for q in self.quarantine_store:
            if status and q.status.value != status:
                continue
            results.append({
                "quarantine_id": q.quarantine_id,
                "batch_id": q.batch_id,
                "entity_type": q.entity_type,
                "record_index": q.record_index,
                "raw_payload": q.raw_payload,
                "violations": [v.model_dump() for v in q.violations],
                "severity": q.severity.value,
                "status": q.status.value,
                "quarantined_at": q.quarantined_at,
                "resolved_at": q.resolved_at,
                "resolution_notes": q.resolution_notes,
            })
        return results

    def resolve_quarantine_record(
        self, quarantine_id: str, action: str, notes: str, actor: str = "LEAD_DATA_ENGINEER"
    ) -> bool:
        for q in self.quarantine_store:
            if q.quarantine_id == quarantine_id:
                if action == "RECONCILE":
                    q.status = ValidationStatus.RECONCILED
                elif action == "DROP":
                    q.status = ValidationStatus.DROPPED
                q.resolved_at = datetime.utcnow()
                q.resolution_notes = notes

                self.audit_log.append({
                    "quarantine_id": quarantine_id,
                    "action": action,
                    "actor": actor,
                    "notes": notes,
                    "timestamp": datetime.utcnow(),
                })
                return True
        return False
