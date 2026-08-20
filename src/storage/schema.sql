-- Automated Data Quality Gatekeeper & Observability Database Schema

-- 1. Bronze Layer: Raw Event Ingestion Log
CREATE TABLE IF NOT EXISTS bronze_raw_events (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    dataset_name VARCHAR(64) NOT NULL,
    record_index INT NOT NULL,
    raw_payload_json TEXT NOT NULL,
    ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Silver/Gold Layer: Clean Production Orders
CREATE TABLE IF NOT EXISTS clean_orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) DEFAULT 0.0,
    currency VARCHAR(8) NOT NULL,
    status VARCHAR(32) NOT NULL,
    order_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    items_count INT DEFAULT 1,
    shipping_country VARCHAR(8),
    batch_id VARCHAR(64) NOT NULL,
    ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Silver/Gold Layer: Clean Production Customers
CREATE TABLE IF NOT EXISTS clean_customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    signup_date DATE NOT NULL,
    country_code VARCHAR(8) NOT NULL,
    age INT,
    is_active BOOLEAN DEFAULT TRUE,
    batch_id VARCHAR(64) NOT NULL,
    ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Quarantine Storage for Corrupted & Drifted Records
CREATE TABLE IF NOT EXISTS quarantine_records (
    quarantine_id VARCHAR(64) PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    record_index INT NOT NULL,
    raw_payload_json TEXT NOT NULL,
    violations_json TEXT NOT NULL,
    severity VARCHAR(16) NOT NULL,
    status VARCHAR(32) DEFAULT 'QUARANTINED',
    quarantined_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITHOUT TIME ZONE,
    resolution_notes TEXT
);

-- 5. Data Quality & Observability Historical Metrics
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL UNIQUE,
    dataset_name VARCHAR(64) NOT NULL,
    total_records INT NOT NULL,
    passed_records INT NOT NULL,
    quarantined_records INT NOT NULL,
    pass_rate NUMERIC(6, 2) NOT NULL,
    error_rate NUMERIC(6, 4) NOT NULL,
    completeness NUMERIC(6, 2) NOT NULL,
    validity NUMERIC(6, 2) NOT NULL,
    uniqueness NUMERIC(6, 2) NOT NULL,
    timeliness NUMERIC(6, 2) NOT NULL,
    consistency NUMERIC(6, 2) NOT NULL,
    overall_health_score NUMERIC(6, 2) NOT NULL,
    sla_breached BOOLEAN NOT NULL,
    processing_duration_ms NUMERIC(10, 2) NOT NULL,
    schema_drift_detected BOOLEAN DEFAULT FALSE,
    schema_drift_score NUMERIC(6, 4) DEFAULT 0.0,
    executed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Schema Drift History
CREATE TABLE IF NOT EXISTS schema_drift_history (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    dataset_name VARCHAR(64) NOT NULL,
    drift_score NUMERIC(6, 4) NOT NULL,
    missing_columns TEXT,
    unexpected_columns TEXT,
    type_mismatches_json TEXT,
    summary TEXT,
    detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Reconciliation & Audit Log
CREATE TABLE IF NOT EXISTS reconciliation_audit_logs (
    id SERIAL PRIMARY KEY,
    quarantine_id VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    actor VARCHAR(64) DEFAULT 'SYSTEM',
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-throughput queries
CREATE INDEX IF NOT EXISTS idx_quarantine_batch ON quarantine_records(batch_id);
CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine_records(status);
CREATE INDEX IF NOT EXISTS idx_metrics_batch ON data_quality_metrics(batch_id);
CREATE INDEX IF NOT EXISTS idx_metrics_dataset ON data_quality_metrics(dataset_name);
