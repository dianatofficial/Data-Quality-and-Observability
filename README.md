# Automated Data Quality Gatekeeper & Observability Platform

[![CI Pipeline](https://github.com/dianatofficial/Data-Quality-and-Observability/actions/workflows/ci.yml/badge.svg)](https://github.com/dianatofficial/Data-Quality-and-Observability/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A distributed, enterprise-grade pre-ingestion data quality validation gate and observability engine. Intercepts incoming raw streaming and batch feeds, executes multi-tier structural and statistical expectation suites, isolates corrupted records into quarantine storage, alerts on SLA breaches, and generates automated HTML Data Quality certificates.

---

## Architecture Overview

```
                          ┌────────────────────────┐
                          │   Raw Ingestion Feeds  │
                          │ (REST APIs, CSV, JSON) │
                          └───────────┬────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │    Bronze Raw Event Staging   │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
                ┌───────────────────────────────────────────┐
                │       Data Quality Gatekeeper Engine      │
                ├───────────────────────────────────────────┤
                │  1. Pydantic v2 Structural Contract Gate  │
                │  2. Expectation Suites (Null, Range, Reg) │
                │  3. Cross-Column Invariant Constraints    │
                │  4. Schema Drift & Mutation Detector      │
                └─────────────────────┬─────────────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
        [100% Compliant]                          [Violations Detected]
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │  Primary Data Warehouse   │             │    Quarantine Storage     │
   │      (Clean Tables)       │             │  (Audit & Root-Cause Log) │
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │                                         │
                 │                                ┌────────┴────────┐
                 │                                ▼                 ▼
                 │                      ┌──────────────────┐ ┌───────────────┐
                 │                      │ Slack/Webhook    │ │ Quarantine    │
                 │                      │ SLA Incident     │ │ Reconciliation│
                 │                      │ Dispatcher       │ │ Replay Queue  │
                 │                      └──────────────────┘ └───────┬───────┘
                 │                                                   │
                 │              [Approved Replay]                    │
                 └───────────────────────────────────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │  Observability Dashboard & Automated Data Docs│
                 └───────────────────────────────────────────────┘
```

---

## Core Capabilities

1. **Pre-Ingestion Contract Gate:** Strict Pydantic v2 schemas combined with declarative YAML expectation suites to intercept data anomalies *before* landing in production tables.
2. **Quarantine & Error Attribution:** Automated routing of non-compliant records to isolated quarantine storage with full JSON payload preservation, severity attribution, and violation detail logs.
3. **Schema Drift Detection:** Real-time schema introspection computing drift scores (0.0 to 1.0) and tracking missing columns, unexpected additions, and type divergences.
4. **Data Observability KPIs:** Real-time computation of 5 quality dimensions:
   - **Completeness:** Required and optional nullity ratios.
   - **Validity:** Business constraint and format compliance.
   - **Uniqueness:** Primary key duplication monitoring.
   - **Timeliness:** Event latency and freshness enforcement.
   - **Consistency:** Cross-column invariants (e.g., `discount_amount <= total_amount`).
5. **Automated Data Docs:** Self-contained HTML data quality certificates generated per batch.
6. **Dual-Mode Interactive UI:** Streamlit Observability Dashboard supporting live database connections or zero-dependency in-memory simulation for 1-click cloud deployment.

---

## Directory Structure

```
.
├── .github/workflows/ci.yml       # Automated GitHub Actions test and lint pipeline
├── config/
│   ├── settings.py                # Environment configuration and SLA thresholds
│   └── expectations_config.yaml   # Declarative expectation suites
├── dags/
│   ├── data_quality_gatekeeper_dag.py     # Production daily batch validation DAG
│   └── quarantine_reconciliation_dag.py   # Scheduled quarantine replay DAG
├── data/                          # Sample clean, corrupted, and drifted JSON batches
├── src/
│   ├── alerts/notifier.py         # Slack webhook and incident dispatcher
│   ├── core/
│   │   ├── engine.py              # Main Gatekeeper orchestration engine
│   │   ├── models.py              # Pydantic domain models & schemas
│   │   ├── rules.py               # Expectation rule implementations
│   │   ├── drift.py               # Schema drift detection logic
│   │   ├── metrics.py             # 5-dimension quality metrics calculator
│   │   ├── quarantine.py          # Quarantine lifecycle manager
│   │   └── reporter.py            # HTML Data Docs compiler
│   ├── dashboard/                 # Streamlit Observability UI & Simulator
│   ├── ingestion/                 # Synthetic generator and batch extractors
│   └── storage/                   # Database engine, schema DDL, and repositories
├── scripts/
│   ├── init_db.py                 # Database initialization script
│   ├── run_gatekeeper.py          # CLI batch runner
│   └── seed_data.py               # Test dataset seeding script
├── tests/                         # Pytest test suite
├── docker-compose.yml             # Local multi-service infrastructure
├── Dockerfile                     # Dashboard container definition
├── Dockerfile.airflow             # Airflow container definition
├── requirements.txt               # Production Python dependencies
├── requirements-dev.txt           # Development and testing dependencies
└── streamlit_app.py               # 1-Click Streamlit Cloud entrypoint
```

---

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11+
- Virtualenv

### 2. Installation
```bash
git clone https://github.com/dianatofficial/Data-Quality-and-Observability.git
cd Data-Quality-and-Observability

python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python scripts/seed_data.py
```

### 4. Run CLI Gatekeeper Validation
```bash
# Validate sample corrupted batch
python scripts/run_gatekeeper.py --dataset orders --input data/sample_corrupted_batch.json

# Run synthetic stream with 200 records
python scripts/run_gatekeeper.py --dataset orders --mock --count 200
```

### 5. Launch Streamlit Observability Dashboard
```bash
streamlit run streamlit_app.py
```
Access the dashboard at `http://localhost:8501`.

---

## Docker Deployment

To launch the complete infrastructure (PostgreSQL Data Warehouse, Airflow Webserver, Airflow Scheduler, and Streamlit Observability Dashboard):

```bash
docker-compose up -d --build
```

### Port Mapping:
- **Streamlit Observability Dashboard:** `http://localhost:8501`
- **Apache Airflow Webserver:** `http://localhost:8080` (Credentials: `admin` / `admin`)
- **PostgreSQL Data Warehouse:** `localhost:5432` (`postgres` / `postgres`)

To tear down services:
```bash
docker-compose down -v
```

---

## Cloud Deployment (Streamlit Community Cloud / HuggingFace Spaces)

The platform includes a built-in **In-Memory Simulation Engine** that operates automatically when external database services are not connected.

1. Fork or push this repository to your GitHub account.
2. Log into [share.streamlit.io](https://share.streamlit.io/).
3. Connect your repository:
   - **Repository:** `dianatofficial/Data-Quality-and-Observability`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
4. Click **Deploy**. The app launches with interactive streaming batches, real-time quarantine management, and downloadable HTML reports without requiring external cloud databases.

---

## Testing & Quality Assurance

Run the comprehensive test suite with code coverage:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=src --cov-report=term-missing
```

Run code formatting and linting:
```bash
ruff check src/ tests/ config/ scripts/
flake8 src/ tests/ config/ scripts/
black --check src/ tests/ config/ scripts/
```

---

## Business Use Cases

- **E-Commerce & Retail Transaction Gates:** Prevent negative pricing, invalid currencies, and fraudulent order IDs from entering revenue reporting tables.
- **Financial Services & Banking:** Intercept transactions violating referential integrity or regulatory limits before loading into core accounting ledgers.
- **Healthcare & Telemetry Pipelines:** Quarantine out-of-range sensor readings, missing patient identifiers, or corrupted telemetry events.
- **Marketing CRM Integration:** Validate partner lead ingestion and flag malformed email addresses or missing geographic tags before sync.

---

## License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
