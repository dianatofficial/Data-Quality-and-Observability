import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.models import BatchSummary, QuarantineRecord, ValidationStatus


class DataWarehouseRepository:
    """Repository for managing clean production data warehouse tables and metrics."""

    def __init__(self, session: Session):
        self.session = session

    def save_clean_orders(self, orders: List[Dict[str, Any]], batch_id: str) -> int:
        if not orders:
            return 0

        insert_sql = text("""
            INSERT INTO clean_orders (
                order_id, customer_id, total_amount, discount_amount,
                currency, status, order_timestamp, items_count,
                shipping_country, batch_id, ingested_at
            ) VALUES (
                :order_id, :customer_id, :total_amount, :discount_amount,
                :currency, :status, :order_timestamp, :items_count,
                :shipping_country, :batch_id, :ingested_at
            )
            ON CONFLICT (order_id) DO UPDATE SET
                status = EXCLUDED.status,
                total_amount = EXCLUDED.total_amount,
                discount_amount = EXCLUDED.discount_amount;
        """)

        now = datetime.utcnow()
        for ord_dict in orders:
            params = {
                "order_id": ord_dict["order_id"],
                "customer_id": ord_dict["customer_id"],
                "total_amount": float(ord_dict["total_amount"]),
                "discount_amount": float(ord_dict.get("discount_amount", 0.0)),
                "currency": ord_dict.get("currency", "USD"),
                "status": ord_dict.get("status", "PENDING"),
                "order_timestamp": ord_dict["order_timestamp"],
                "items_count": int(ord_dict.get("items_count", 1)),
                "shipping_country": ord_dict.get("shipping_country", "US"),
                "batch_id": batch_id,
                "ingested_at": now,
            }
            # Fallback for SQLite which doesn't support ON CONFLICT in old versions without primary key
            try:
                self.session.execute(insert_sql, params)
            except Exception:
                # Fallback to simple insert/replace for sqlite
                self.session.execute(
                    text("""
                        INSERT OR REPLACE INTO clean_orders (
                            order_id, customer_id, total_amount, discount_amount,
                            currency, status, order_timestamp, items_count,
                            shipping_country, batch_id, ingested_at
                        ) VALUES (
                            :order_id, :customer_id, :total_amount, :discount_amount,
                            :currency, :status, :order_timestamp, :items_count,
                            :shipping_country, :batch_id, :ingested_at
                        )
                    """),
                    params,
                )

        return len(orders)

    def save_clean_customers(self, customers: List[Dict[str, Any]], batch_id: str) -> int:
        if not customers:
            return 0

        now = datetime.utcnow()
        for cust in customers:
            params = {
                "customer_id": cust["customer_id"],
                "email": cust["email"],
                "signup_date": cust["signup_date"],
                "country_code": cust.get("country_code", "US"),
                "age": cust.get("age"),
                "is_active": cust.get("is_active", True),
                "batch_id": batch_id,
                "ingested_at": now,
            }
            try:
                self.session.execute(
                    text("""
                        INSERT INTO clean_customers (
                            customer_id, email, signup_date, country_code, age, is_active, batch_id, ingested_at
                        ) VALUES (
                            :customer_id, :email, :signup_date, :country_code, :age, :is_active, :batch_id, :ingested_at
                        )
                        ON CONFLICT (customer_id) DO UPDATE SET
                            email = EXCLUDED.email,
                            country_code = EXCLUDED.country_code,
                            age = EXCLUDED.age;
                    """),
                    params,
                )
            except Exception:
                self.session.execute(
                    text("""
                        INSERT OR REPLACE INTO clean_customers (
                            customer_id, email, signup_date, country_code, age, is_active, batch_id, ingested_at
                        ) VALUES (
                            :customer_id, :email, :signup_date, :country_code, :age, :is_active, :batch_id, :ingested_at
                        )
                    """),
                    params,
                )

        return len(customers)

    def save_metrics(self, summary: BatchSummary) -> None:
        params = {
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
        }

        try:
            self.session.execute(
                text("""
                    INSERT INTO data_quality_metrics (
                        batch_id, dataset_name, total_records, passed_records,
                        quarantined_records, pass_rate, error_rate, completeness,
                        validity, uniqueness, timeliness, consistency,
                        overall_health_score, sla_breached, processing_duration_ms,
                        schema_drift_detected, schema_drift_score, executed_at
                    ) VALUES (
                        :batch_id, :dataset_name, :total_records, :passed_records,
                        :quarantined_records, :pass_rate, :error_rate, :completeness,
                        :validity, :uniqueness, :timeliness, :consistency,
                        :overall_health_score, :sla_breached, :processing_duration_ms,
                        :schema_drift_detected, :schema_drift_score, :executed_at
                    )
                    ON CONFLICT (batch_id) DO NOTHING;
                """),
                params,
            )
        except Exception:
            self.session.execute(
                text("""
                    INSERT OR IGNORE INTO data_quality_metrics (
                        batch_id, dataset_name, total_records, passed_records,
                        quarantined_records, pass_rate, error_rate, completeness,
                        validity, uniqueness, timeliness, consistency,
                        overall_health_score, sla_breached, processing_duration_ms,
                        schema_drift_detected, schema_drift_score, executed_at
                    ) VALUES (
                        :batch_id, :dataset_name, :total_records, :passed_records,
                        :quarantined_records, :pass_rate, :error_rate, :completeness,
                        :validity, :uniqueness, :timeliness, :consistency,
                        :overall_health_score, :sla_breached, :processing_duration_ms,
                        :schema_drift_detected, :schema_drift_score, :executed_at
                    )
                """),
                params,
            )

    def get_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = self.session.execute(
            text("""
                SELECT * FROM data_quality_metrics
                ORDER BY executed_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in result]


class QuarantineRepository:
    """Repository for persisting, inspecting, and resolving quarantined records."""

    def __init__(self, session: Session):
        self.session = session

    def save_quarantine_records(self, records: List[QuarantineRecord]) -> int:
        if not records:
            return 0

        for rec in records:
            params = {
                "quarantine_id": rec.quarantine_id,
                "batch_id": rec.batch_id,
                "entity_type": rec.entity_type,
                "record_index": rec.record_index,
                "raw_payload_json": json.dumps(rec.raw_payload),
                "violations_json": json.dumps([v.model_dump() for v in rec.violations]),
                "severity": rec.severity.value,
                "status": rec.status.value,
                "quarantined_at": rec.quarantined_at,
                "resolved_at": rec.resolved_at,
                "resolution_notes": rec.resolution_notes,
            }

            try:
                self.session.execute(
                    text("""
                        INSERT INTO quarantine_records (
                            quarantine_id, batch_id, entity_type, record_index,
                            raw_payload_json, violations_json, severity,
                            status, quarantined_at, resolved_at, resolution_notes
                        ) VALUES (
                            :quarantine_id, :batch_id, :entity_type, :record_index,
                            :raw_payload_json, :violations_json, :severity,
                            :status, :quarantined_at, :resolved_at, :resolution_notes
                        )
                        ON CONFLICT (quarantine_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            resolved_at = EXCLUDED.resolved_at,
                            resolution_notes = EXCLUDED.resolution_notes;
                    """),
                    params,
                )
            except Exception:
                self.session.execute(
                    text("""
                        INSERT OR REPLACE INTO quarantine_records (
                            quarantine_id, batch_id, entity_type, record_index,
                            raw_payload_json, violations_json, severity,
                            status, quarantined_at, resolved_at, resolution_notes
                        ) VALUES (
                            :quarantine_id, :batch_id, :entity_type, :record_index,
                            :raw_payload_json, :violations_json, :severity,
                            :status, :quarantined_at, :resolved_at, :resolution_notes
                        )
                    """),
                    params,
                )

        return len(records)

    def get_quarantined_records(
        self,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM quarantine_records WHERE 1=1"
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if status:
            query += " AND status = :status"
            params["status"] = status

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY quarantined_at DESC LIMIT :limit OFFSET :offset"
        result = self.session.execute(text(query), params)
        
        rows = []
        for row in result:
            d = dict(row._mapping)
            if isinstance(d.get("raw_payload_json"), str):
                d["raw_payload"] = json.loads(d["raw_payload_json"])
            if isinstance(d.get("violations_json"), str):
                d["violations"] = json.loads(d["violations_json"])
            rows.append(d)
        return rows

    def update_status(
        self,
        quarantine_id: str,
        new_status: ValidationStatus,
        notes: str,
        actor: str = "DATA_ENGINEER",
    ) -> bool:
        now = datetime.utcnow()
        self.session.execute(
            text("""
                UPDATE quarantine_records
                SET status = :status, resolved_at = :resolved_at, resolution_notes = :notes
                WHERE quarantine_id = :quarantine_id
            """),
            {
                "status": new_status.value,
                "resolved_at": now,
                "notes": notes,
                "quarantine_id": quarantine_id,
            },
        )

        self.session.execute(
            text("""
                INSERT INTO reconciliation_audit_logs (quarantine_id, action, actor, notes, created_at)
                VALUES (:quarantine_id, :action, :actor, :notes, :created_at)
            """),
            {
                "quarantine_id": quarantine_id,
                "action": new_status.value,
                "actor": actor,
                "notes": notes,
                "created_at": now,
            },
        )
        return True
