from typing import Any, Dict, List

from src.core.models import HealthScore, RecordValidationResult


class QualityMetricsCalculator:
    """Computes multidimensional data quality scores and SLA status."""

    def __init__(self, min_sla_score: float = 95.0, max_error_rate: float = 0.05):
        self.min_sla_score = min_sla_score
        self.max_error_rate = max_error_rate

    def calculate(
        self,
        raw_records: List[Dict[str, Any]],
        validation_results: List[RecordValidationResult],
        primary_key: str = "order_id",
    ) -> HealthScore:
        total_records = len(raw_records)
        if total_records == 0:
            return HealthScore(
                completeness=100.0,
                validity=100.0,
                uniqueness=100.0,
                timeliness=100.0,
                consistency=100.0,
                overall_score=100.0,
                sla_passed=True,
            )

        # 1. Completeness: Check nullity across all fields
        total_fields = 0
        null_fields = 0
        for rec in raw_records:
            for _, val in rec.items():
                total_fields += 1
                if val is None or (isinstance(val, str) and str(val).strip() == ""):
                    null_fields += 1

        completeness = round(((total_fields - null_fields) / max(total_fields, 1)) * 100.0, 2)

        # 2. Validity: Proportion of records without any rule violations
        valid_records_count = sum(1 for res in validation_results if res.is_valid)
        validity = round((valid_records_count / total_records) * 100.0, 2)

        # 3. Uniqueness: Ratio of unique primary keys
        seen_keys = set()
        duplicate_count = 0
        for rec in raw_records:
            pk_val = rec.get(primary_key)
            if pk_val:
                if pk_val in seen_keys:
                    duplicate_count += 1
                else:
                    seen_keys.add(pk_val)
        uniqueness = round(((total_records - duplicate_count) / total_records) * 100.0, 2)

        # 4. Timeliness: Check timestamp presence & validity
        timeliness_failures = 0
        for res in validation_results:
            for v in res.violations:
                if v.rule_type == "timestamp_range":
                    timeliness_failures += 1
                    break
        timeliness = round(((total_records - timeliness_failures) / total_records) * 100.0, 2)

        # 5. Consistency: Cross-column validation compliance
        consistency_failures = 0
        for res in validation_results:
            for v in res.violations:
                if v.rule_type == "cross_column_expression":
                    consistency_failures += 1
                    break
        consistency = round(((total_records - consistency_failures) / total_records) * 100.0, 2)

        # Composite Overall Score (Weighted harmonic/linear average)
        # Validity (35%), Completeness (25%), Uniqueness (20%), Consistency (10%), Timeliness (10%)
        overall_score = round(
            (validity * 0.35)
            + (completeness * 0.25)
            + (uniqueness * 0.20)
            + (consistency * 0.10)
            + (timeliness * 0.10),
            2,
        )

        error_rate = (total_records - valid_records_count) / total_records
        sla_passed = overall_score >= self.min_sla_score and error_rate <= self.max_error_rate

        return HealthScore(
            completeness=completeness,
            validity=validity,
            uniqueness=uniqueness,
            timeliness=timeliness,
            consistency=consistency,
            overall_score=overall_score,
            sla_passed=sla_passed,
        )
