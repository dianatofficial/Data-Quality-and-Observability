import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import RuleViolation, ValidationSeverity


class BaseRule(ABC):
    """Abstract base class for all data quality expectation rules."""

    def __init__(
        self,
        name: str,
        column: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.HIGH,
        description: str = "",
    ):
        self.name = name
        self.column = column
        self.severity = severity
        self.description = description

    @abstractmethod
    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        """Validate a single record dictionary. Returns RuleViolation if failed, None if valid."""
        pass


class NotNullRule(BaseRule):
    """Asserts that a specified column exists and is not null or whitespace."""

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        if not self.column:
            return None

        val = record.get(self.column)
        if val is None or (isinstance(val, str) and str(val).strip() == ""):
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="not_null",
                severity=self.severity,
                message=f"Column '{self.column}' is missing or null.",
                actual_value=val,
                expected="non-null value",
            )
        return None


class RegexMatchRule(BaseRule):
    """Asserts that a string column matches a given regex pattern."""

    def __init__(
        self,
        name: str,
        column: str,
        pattern: str,
        severity: ValidationSeverity = ValidationSeverity.HIGH,
        description: str = "",
    ):
        super().__init__(name=name, column=column, severity=severity, description=description)
        self.pattern = pattern
        self.compiled = re.compile(pattern)

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        if not self.column:
            return None

        val = record.get(self.column)
        if val is None:
            return None  # Nullity should be checked by NotNullRule

        val_str = str(val)
        if not self.compiled.match(val_str):
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="regex_match",
                severity=self.severity,
                message=f"Column '{self.column}' value '{val_str}' does not match pattern '{self.pattern}'.",
                actual_value=val_str,
                expected=self.pattern,
            )
        return None


class RangeRule(BaseRule):
    """Asserts that a numeric column falls within [min_val, max_val]."""

    def __init__(
        self,
        name: str,
        column: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        severity: ValidationSeverity = ValidationSeverity.HIGH,
        description: str = "",
    ):
        super().__init__(name=name, column=column, severity=severity, description=description)
        self.min_val = min_val
        self.max_val = max_val

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        if not self.column:
            return None

        val = record.get(self.column)
        if val is None:
            return None

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="range",
                severity=self.severity,
                message=f"Column '{self.column}' value '{val}' is not a valid number.",
                actual_value=val,
                expected="numeric",
            )

        if self.min_val is not None and num_val < self.min_val:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="range",
                severity=self.severity,
                message=f"Column '{self.column}' value {num_val} is below minimum allowed {self.min_val}.",
                actual_value=num_val,
                expected=f">= {self.min_val}",
            )

        if self.max_val is not None and num_val > self.max_val:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="range",
                severity=self.severity,
                message=f"Column '{self.column}' value {num_val} exceeds maximum allowed {self.max_val}.",
                actual_value=num_val,
                expected=f"<= {self.max_val}",
            )

        return None


class AllowedValuesRule(BaseRule):
    """Asserts that a column value belongs to a set of allowed values."""

    def __init__(
        self,
        name: str,
        column: str,
        values: List[Any],
        severity: ValidationSeverity = ValidationSeverity.MEDIUM,
        description: str = "",
    ):
        super().__init__(name=name, column=column, severity=severity, description=description)
        self.allowed_values = set(values)

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        if not self.column:
            return None

        val = record.get(self.column)
        if val is None:
            return None

        if val not in self.allowed_values:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="allowed_values",
                severity=self.severity,
                message=f"Column '{self.column}' value '{val}' is not in allowed set {sorted(list(self.allowed_values))}.",
                actual_value=val,
                expected=list(self.allowed_values),
            )
        return None


class TimestampRangeRule(BaseRule):
    """Validates timestamp values against realistic boundaries."""

    def __init__(
        self,
        name: str,
        column: str,
        min_year: int = 2020,
        max_future_seconds: int = 300,
        severity: ValidationSeverity = ValidationSeverity.HIGH,
        description: str = "",
    ):
        super().__init__(name=name, column=column, severity=severity, description=description)
        self.min_year = min_year
        self.max_future_seconds = max_future_seconds

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        if not self.column:
            return None

        val = record.get(self.column)
        if val is None:
            return None

        parsed_dt = None
        if isinstance(val, datetime):
            parsed_dt = val
        elif isinstance(val, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    parsed_dt = datetime.strptime(val.replace("Z", ""), fmt.replace("Z", ""))
                    break
                except ValueError:
                    continue

        if not parsed_dt:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="timestamp_range",
                severity=self.severity,
                message=f"Column '{self.column}' timestamp '{val}' has an invalid format.",
                actual_value=val,
                expected="valid ISO datetime",
            )

        if parsed_dt.year < self.min_year:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="timestamp_range",
                severity=self.severity,
                message=f"Column '{self.column}' timestamp '{val}' is earlier than year {self.min_year}.",
                actual_value=val,
                expected=f"year >= {self.min_year}",
            )

        now_utc = datetime.utcnow()
        if (parsed_dt - now_utc).total_seconds() > self.max_future_seconds:
            return RuleViolation(
                rule_name=self.name,
                column=self.column,
                rule_type="timestamp_range",
                severity=self.severity,
                message=f"Column '{self.column}' timestamp '{val}' is in the future (> {self.max_future_seconds}s).",
                actual_value=val,
                expected="timestamp <= now",
            )

        return None


class CrossColumnExpressionRule(BaseRule):
    """Evaluates cross-column boolean expressions (e.g. discount_amount <= total_amount)."""

    def __init__(
        self,
        name: str,
        expression: str,
        severity: ValidationSeverity = ValidationSeverity.HIGH,
        description: str = "",
    ):
        super().__init__(name=name, column=None, severity=severity, description=description)
        self.expression = expression

    def validate_record(self, record: Dict[str, Any], record_index: int) -> Optional[RuleViolation]:
        # Safe evaluation of basic comparisons
        try:
            # We construct a safe local dict with sanitized numeric/string fields
            safe_locals = {}
            for k, v in record.items():
                if isinstance(v, (int, float, bool, str)) or v is None:
                    safe_locals[k] = 0.0 if v is None and ("amount" in k or "count" in k) else v

            # Evaluate with no builtins for security
            result = eval(self.expression, {"__builtins__": {}}, safe_locals)
            if not result:
                return RuleViolation(
                    rule_name=self.name,
                    column=None,
                    rule_type="cross_column_expression",
                    severity=self.severity,
                    message=f"Cross-column constraint failed: '{self.expression}'.",
                    actual_value={k: record.get(k) for k in safe_locals if k in self.expression},
                    expected=self.expression,
                )
        except Exception as e:
            return RuleViolation(
                rule_name=self.name,
                column=None,
                rule_type="cross_column_expression",
                severity=self.severity,
                message=f"Evaluation error for '{self.expression}': {str(e)}",
                actual_value=str(e),
                expected=self.expression,
            )
        return None


def create_rule_from_config(config: Dict[str, Any]) -> BaseRule:
    """Factory to instantiate rules from YAML configuration dictionaries."""
    rule_type = config.get("rule_type")
    name = config.get("name", "unnamed_rule")
    column = config.get("column")
    severity = ValidationSeverity(config.get("severity", "HIGH"))
    description = config.get("description", "")

    if rule_type == "not_null":
        return NotNullRule(name=name, column=column, severity=severity, description=description)
    elif rule_type == "regex_match":
        return RegexMatchRule(
            name=name,
            column=column,  # type: ignore
            pattern=config.get("pattern", ".*"),
            severity=severity,
            description=description,
        )
    elif rule_type == "range":
        return RangeRule(
            name=name,
            column=column,  # type: ignore
            min_val=config.get("min_val"),
            max_val=config.get("max_val"),
            severity=severity,
            description=description,
        )
    elif rule_type == "allowed_values":
        return AllowedValuesRule(
            name=name,
            column=column,  # type: ignore
            values=config.get("values", []),
            severity=severity,
            description=description,
        )
    elif rule_type == "timestamp_range":
        return TimestampRangeRule(
            name=name,
            column=column,  # type: ignore
            min_year=config.get("min_year", 2020),
            max_future_seconds=config.get("max_future_seconds", 300),
            severity=severity,
            description=description,
        )
    elif rule_type == "expression":
        return CrossColumnExpressionRule(
            name=name,
            expression=config.get("expression", "True"),
            severity=severity,
            description=description,
        )
    else:
        raise ValueError(f"Unsupported rule_type: {rule_type}")
