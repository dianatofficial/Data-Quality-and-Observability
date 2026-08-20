from typing import Any, Dict, List

import pytest

from src.core.engine import GatekeeperEngine
from src.core.models import ValidationSeverity
from src.core.rules import (
    AllowedValuesRule,
    CrossColumnExpressionRule,
    NotNullRule,
    RangeRule,
    RegexMatchRule,
    TimestampRangeRule,
)


def test_not_null_rule():
    rule = NotNullRule(name="test_null", column="user_id", severity=ValidationSeverity.CRITICAL)
    
    assert rule.validate_record({"user_id": "123"}, 0) is None
    
    violation = rule.validate_record({"user_id": None}, 0)
    assert violation is not None
    assert violation.rule_type == "not_null"
    assert violation.severity == ValidationSeverity.CRITICAL

    violation_empty = rule.validate_record({"user_id": "  "}, 0)
    assert violation_empty is not None


def test_range_rule():
    rule = RangeRule(name="test_range", column="amount", min_val=10.0, max_val=100.0)
    
    assert rule.validate_record({"amount": 50.0}, 0) is None
    assert rule.validate_record({"amount": 10.0}, 0) is None
    
    v_low = rule.validate_record({"amount": 5.0}, 0)
    assert v_low is not None
    assert "below minimum" in v_low.message

    v_high = rule.validate_record({"amount": 150.0}, 0)
    assert v_high is not None
    assert "exceeds maximum" in v_high.message


def test_regex_match_rule():
    rule = RegexMatchRule(name="test_regex", column="email", pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    
    assert rule.validate_record({"email": "valid@enterprise.io"}, 0) is None
    
    v = rule.validate_record({"email": "invalid-email-address"}, 0)
    assert v is not None
    assert v.rule_type == "regex_match"


def test_allowed_values_rule():
    rule = AllowedValuesRule(name="test_allowed", column="currency", values=["USD", "EUR"])
    
    assert rule.validate_record({"currency": "USD"}, 0) is None
    
    v = rule.validate_record({"currency": "DOGE"}, 0)
    assert v is not None
    assert v.rule_type == "allowed_values"


def test_cross_column_expression_rule():
    rule = CrossColumnExpressionRule(
        name="test_expr",
        expression="discount_amount <= total_amount",
        severity=ValidationSeverity.HIGH,
    )
    
    assert rule.validate_record({"total_amount": 100, "discount_amount": 20}, 0) is None
    
    v = rule.validate_record({"total_amount": 50, "discount_amount": 100}, 0)
    assert v is not None
    assert v.rule_type == "cross_column_expression"


def test_gatekeeper_process_batch(
    gatekeeper_engine: GatekeeperEngine,
    sample_corrupted_orders: List[Dict[str, Any]],
):
    summary, clean_records, quarantine_records = gatekeeper_engine.process_batch(
        dataset_name="orders",
        records=sample_corrupted_orders,
        batch_id="TEST-BATCH-001",
    )

    assert summary.batch_id == "TEST-BATCH-001"
    assert summary.total_records == 3
    assert summary.passed_records == 1
    assert summary.quarantined_records == 2
    assert len(clean_records) == 1
    assert len(quarantine_records) == 2
    assert clean_records[0]["order_id"] == "ORD-VALID001"
    assert summary.sla_breached is True
