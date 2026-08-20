import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import uuid4

import yaml
from pydantic import ValidationError

from src.core.drift import SchemaDriftDetector
from src.core.metrics import QualityMetricsCalculator
from src.core.models import (
    BatchSummary,
    CustomerPayload,
    OrderPayload,
    QuarantineRecord,
    RecordValidationResult,
    RuleViolation,
    ValidationSeverity,
    ValidationStatus,
)
from src.core.quarantine import QuarantineManager
from src.core.reporter import DataDocsReporter
from src.core.rules import BaseRule, create_rule_from_config

# Schema mappings for standard enterprise datasets
DATASET_SCHEMAS: Dict[str, Dict[str, Type]] = {
    "orders": {
        "order_id": str,
        "customer_id": str,
        "total_amount": float,
        "discount_amount": float,
        "currency": str,
        "status": str,
        "order_timestamp": str,
        "items_count": int,
        "shipping_country": str,
    },
    "customers": {
        "customer_id": str,
        "email": str,
        "signup_date": str,
        "country_code": str,
        "age": int,
    },
}

PYDANTIC_PAYLOAD_MODELS = {
    "orders": OrderPayload,
    "customers": CustomerPayload,
}


class GatekeeperEngine:
    """Core orchestration engine for data validation, quarantine routing, and observability."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        min_sla_score: float = 95.0,
        max_error_rate: float = 0.05,
    ):
        self.config_path = config_path or Path("config/expectations_config.yaml")
        self.min_sla_score = min_sla_score
        self.max_error_rate = max_error_rate
        self.metrics_calculator = QualityMetricsCalculator(
            min_sla_score=min_sla_score, max_error_rate=max_error_rate
        )
        self.reporter = DataDocsReporter()
        self.rules_by_suite: Dict[str, List[BaseRule]] = {}
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            suites = cfg.get("suites", {})
            for suite_name, suite_def in suites.items():
                rules: List[BaseRule] = []
                for r_cfg in suite_def.get("rules", []):
                    rules.append(create_rule_from_config(r_cfg))
                for xr_cfg in suite_def.get("cross_column_rules", []):
                    rules.append(create_rule_from_config(xr_cfg))
                self.rules_by_suite[suite_name] = rules

    def register_custom_rules(self, suite_name: str, rules: List[BaseRule]) -> None:
        """Dynamically add or override rules for a suite."""
        self.rules_by_suite[suite_name] = rules

    def process_batch(
        self,
        dataset_name: str,
        records: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
        primary_key: Optional[str] = None,
    ) -> Tuple[BatchSummary, List[Dict[str, Any]], List[QuarantineRecord]]:
        """Validate an entire incoming batch of records and partition into clean vs quarantined."""
        start_time = time.perf_counter()
        bid = batch_id or f"BATCH-{uuid4().hex[:8].upper()}"
        pk_col = primary_key or ("order_id" if dataset_name == "orders" else "customer_id")

        # 1. Schema Drift Analysis
        expected_schema = DATASET_SCHEMAS.get(dataset_name, {})
        drift_detector = SchemaDriftDetector(dataset_name, expected_schema)
        drift_report = drift_detector.detect(records)

        # 2. Record-by-Record Validation
        rules = self.rules_by_suite.get(dataset_name, [])
        pydantic_model = PYDANTIC_PAYLOAD_MODELS.get(dataset_name)

        validation_results: List[RecordValidationResult] = []
        clean_records: List[Dict[str, Any]] = []
        violations_by_type: Dict[str, int] = {}
        violations_by_column: Dict[str, int] = {}

        for idx, rec in enumerate(records):
            rec_violations: List[RuleViolation] = []

            # 2.1 Pydantic Contract Validation
            cleaned_dict = None
            if pydantic_model:
                try:
                    parsed_obj = pydantic_model(**rec)
                    cleaned_dict = parsed_obj.model_dump()
                except ValidationError as ve:
                    for err in ve.errors():
                        loc_field = str(err["loc"][0]) if err["loc"] else "payload"
                        rec_violations.append(
                            RuleViolation(
                                rule_name=f"pydantic_type_error_{loc_field}",
                                column=loc_field,
                                rule_type="type_contract",
                                severity=ValidationSeverity.CRITICAL,
                                message=err.get("msg", "Type mismatch"),
                                actual_value=rec.get(loc_field),
                                expected=err.get("type", "valid_type"),
                            )
                        )

            # 2.2 Deep Expectation Suite Rules
            for rule in rules:
                violation = rule.validate_record(rec, idx)
                if violation:
                    rec_violations.append(violation)

            # Aggregate violation statistics
            for v in rec_violations:
                violations_by_type[v.rule_type] = violations_by_type.get(v.rule_type, 0) + 1
                if v.column:
                    violations_by_column[v.column] = violations_by_column.get(v.column, 0) + 1

            is_valid = len(rec_violations) == 0
            entity_id = str(rec.get(pk_col, f"REC-{idx}"))

            v_res = RecordValidationResult(
                record_index=idx,
                entity_id=entity_id,
                is_valid=is_valid,
                violations=rec_violations,
                raw_payload=rec,
                cleaned_payload=cleaned_dict if is_valid else None,
            )
            validation_results.append(v_res)

            if is_valid:
                clean_records.append(cleaned_dict or rec)

        # 3. Create Quarantine Records for non-compliant payloads
        failed_results = [r for r in validation_results if not r.is_valid]
        quarantine_records = QuarantineManager.create_quarantine_records(
            batch_id=bid,
            entity_type=dataset_name,
            failed_results=failed_results,
        )

        # 4. Observability & Health Score Metrics
        health_score = self.metrics_calculator.calculate(
            raw_records=records,
            validation_results=validation_results,
            primary_key=pk_col,
        )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total = len(records)
        passed = len(clean_records)
        quarantined = len(quarantine_records)
        pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 100.0
        error_rate = round((quarantined / total), 4) if total > 0 else 0.0

        sla_breached = (not health_score.sla_passed) or drift_report.drift_score > 0.15

        summary = BatchSummary(
            batch_id=bid,
            dataset_name=dataset_name,
            total_records=total,
            passed_records=passed,
            quarantined_records=quarantined,
            pass_rate=pass_rate,
            error_rate=error_rate,
            health_score=health_score,
            schema_drift=drift_report,
            processing_duration_ms=duration_ms,
            executed_at=datetime.utcnow(),
            sla_breached=sla_breached,
            violations_by_type=violations_by_type,
            violations_by_column=violations_by_column,
        )

        return summary, clean_records, quarantine_records
