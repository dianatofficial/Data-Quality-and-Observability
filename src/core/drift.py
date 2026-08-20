from typing import Any, Dict, List, Set, Type

from src.core.models import SchemaDriftReport


class SchemaDriftDetector:
    """Detects schema drift between expected contracts and incoming raw batch data."""

    def __init__(self, dataset_name: str, expected_schema: Dict[str, Type]):
        self.dataset_name = dataset_name
        self.expected_schema = expected_schema

    def _infer_type(self, val: Any) -> str:
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, int):
            return "int"
        if isinstance(val, float):
            return "float"
        if isinstance(val, str):
            return "str"
        if isinstance(val, (list, tuple)):
            return "list"
        if isinstance(val, dict):
            return "dict"
        return type(val).__name__

    def detect(self, batch_records: List[Dict[str, Any]]) -> SchemaDriftReport:
        if not batch_records:
            return SchemaDriftReport(
                dataset_name=self.dataset_name,
                detected=False,
                summary="Empty batch - no drift detected.",
            )

        # Collect observed columns and types across sample of records
        sample_size = min(len(batch_records), 500)
        observed_cols: Set[str] = set()
        observed_types: Dict[str, Set[str]] = {}

        for rec in batch_records[:sample_size]:
            for col, val in rec.items():
                observed_cols.add(col)
                if col not in observed_types:
                    observed_types[col] = set()
                t = self._infer_type(val)
                if t != "null":
                    observed_types[col].add(t)

        expected_cols = set(self.expected_schema.keys())
        missing_cols = sorted(list(expected_cols - observed_cols))
        unexpected_cols = sorted(list(observed_cols - expected_cols))

        type_mismatches: Dict[str, Dict[str, str]] = {}
        for col in expected_cols.intersection(observed_cols):
            expected_type_cls = self.expected_schema[col]
            expected_type_name = expected_type_cls.__name__ if hasattr(expected_type_cls, "__name__") else str(expected_type_cls)
            
            # Map Python types to simplified type names
            type_mapping = {
                "str": "str",
                "int": "int",
                "float": "float",
                "bool": "bool",
                "list": "list",
                "dict": "dict",
            }
            mapped_expected = type_mapping.get(expected_type_name.lower(), expected_type_name.lower())

            actual_types = observed_types.get(col, set())
            if actual_types:
                # If all observed non-null types differ from expected (allowing int -> float promotion)
                divergent = True
                for act in actual_types:
                    if act == mapped_expected:
                        divergent = False
                        break
                    if mapped_expected == "float" and act == "int":
                        divergent = False
                        break

                if divergent:
                    type_mismatches[col] = {
                        "expected": mapped_expected,
                        "observed": ", ".join(sorted(list(actual_types))),
                    }

        total_expected = len(expected_cols) or 1
        # Drift score calculated by weighted penalty
        drift_penalty = (len(missing_cols) * 0.4) + (len(unexpected_cols) * 0.2) + (len(type_mismatches) * 0.4)
        drift_score = min(1.0, round(drift_penalty / total_expected, 3))
        drift_detected = len(missing_cols) > 0 or len(unexpected_cols) > 0 or len(type_mismatches) > 0

        summary_parts = []
        if missing_cols:
            summary_parts.append(f"Missing columns: {missing_cols}")
        if unexpected_cols:
            summary_parts.append(f"Unexpected columns: {unexpected_cols}")
        if type_mismatches:
            summary_parts.append(f"Type mismatches: {type_mismatches}")

        summary = "; ".join(summary_parts) if summary_parts else "Schema matches contract perfectly."

        return SchemaDriftReport(
            dataset_name=self.dataset_name,
            detected=drift_detected,
            missing_columns=missing_cols,
            unexpected_columns=unexpected_cols,
            type_mismatches=type_mismatches,
            drift_score=drift_score,
            summary=summary,
        )
