from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ValidationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    RECONCILED = "RECONCILED"
    DROPPED = "DROPPED"


class RuleViolation(BaseModel):
    """Specific rule violation details."""

    rule_name: str
    column: Optional[str] = None
    rule_type: str
    severity: ValidationSeverity
    message: str
    actual_value: Any = None
    expected: Any = None

    model_config = ConfigDict(extra="ignore")


class RecordValidationResult(BaseModel):
    """Validation result for a single record."""

    record_index: int
    entity_id: Optional[str] = None
    is_valid: bool
    violations: List[RuleViolation] = Field(default_factory=list)
    raw_payload: Dict[str, Any]
    cleaned_payload: Optional[Dict[str, Any]] = None

    @property
    def max_severity(self) -> Optional[ValidationSeverity]:
        if not self.violations:
            return None
        priority = {
            ValidationSeverity.CRITICAL: 4,
            ValidationSeverity.HIGH: 3,
            ValidationSeverity.MEDIUM: 2,
            ValidationSeverity.LOW: 1,
        }
        return max(self.violations, key=lambda v: priority[v.severity]).severity


class QuarantineRecord(BaseModel):
    """Quarantined entity stored for review and remediation."""

    quarantine_id: str = Field(default_factory=lambda: f"QR-{uuid4().hex[:12]}")
    batch_id: str
    entity_type: str
    record_index: int
    raw_payload: Dict[str, Any]
    violations: List[RuleViolation]
    severity: ValidationSeverity
    status: ValidationStatus = ValidationStatus.QUARANTINED
    quarantined_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class HealthScore(BaseModel):
    """Data quality dimensions and overall composite score (0-100)."""

    completeness: float = Field(ge=0.0, le=100.0)
    validity: float = Field(ge=0.0, le=100.0)
    uniqueness: float = Field(ge=0.0, le=100.0)
    timeliness: float = Field(ge=0.0, le=100.0)
    consistency: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)
    sla_passed: bool


class SchemaDriftReport(BaseModel):
    """Schema drift detection outcome."""

    dataset_name: str
    detected: bool
    missing_columns: List[str] = Field(default_factory=list)
    unexpected_columns: List[str] = Field(default_factory=list)
    type_mismatches: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    drift_score: float = 0.0
    summary: str


class BatchSummary(BaseModel):
    """Summary of a processed batch."""

    batch_id: str
    dataset_name: str
    total_records: int
    passed_records: int
    quarantined_records: int
    pass_rate: float
    error_rate: float
    health_score: HealthScore
    schema_drift: SchemaDriftReport
    processing_duration_ms: float
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    sla_breached: bool
    violations_by_type: Dict[str, int] = Field(default_factory=dict)
    violations_by_column: Dict[str, int] = Field(default_factory=dict)


# --- Core Domain Payloads ---

class OrderPayload(BaseModel):
    """Strict domain schema for incoming order transactions."""

    order_id: str
    customer_id: str
    total_amount: float
    discount_amount: float = 0.0
    currency: str = "USD"
    status: str = "PENDING"
    order_timestamp: str
    items_count: int = 1
    shipping_country: Optional[str] = "US"

    model_config = ConfigDict(extra="allow")


class CustomerPayload(BaseModel):
    """Strict domain schema for incoming customer profile data."""

    customer_id: str
    email: str
    signup_date: str
    country_code: str = "US"
    age: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(extra="allow")
