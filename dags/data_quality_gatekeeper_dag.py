"""
Apache Airflow DAG: Automated Data Quality Gatekeeper & Observability Pipeline
Orchestrates pre-ingestion validation, quarantine routing, SLA compliance check, and Slack alerting.
"""
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import sys

# Ensure project modules are available
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Airflow imports
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator, BranchPythonOperator
    from airflow.operators.empty import EmptyOperator
except ImportError:
    # Allow running in non-airflow development environments
    DAG = None
    PythonOperator = None
    BranchPythonOperator = None
    EmptyOperator = None

from src.alerts.notifier import AlertDispatcher
from src.core.engine import GatekeeperEngine
from src.core.reporter import DataDocsReporter
from src.ingestion.generator import EnterpriseDataGenerator
from src.storage.database import get_db_manager
from src.storage.repositories import DataWarehouseRepository, QuarantineRepository

logger = logging.getLogger("airflow.task")


def task_extract_raw_batch(**context) -> str:
    """Extract or simulate daily incoming batch payload."""
    ti = context["ti"]
    execution_date = context.get("ds", datetime.utcnow().strftime("%Y-%m-%d"))
    batch_id = f"BATCH-{execution_date}-{context['dag_run'].run_id[-6:]}"

    # Generate or extract daily incoming records with realistic variation
    raw_records = EnterpriseDataGenerator.generate_corrupted_orders(
        total_count=150, corruption_rate=0.12
    )

    ti.xcom_push(key="batch_id", value=batch_id)
    ti.xcom_push(key="raw_records", value=raw_records)
    logger.info("Successfully extracted %d records for batch %s", len(raw_records), batch_id)
    return batch_id


def task_validate_gatekeeper(**context) -> str:
    """Execute multi-tier validation gate, compute metrics, and partition records."""
    ti = context["ti"]
    batch_id = ti.xcom_pull(key="batch_id", task_ids="extract_raw_batch")
    raw_records = ti.xcom_pull(key="raw_records", task_ids="extract_raw_batch")

    engine = GatekeeperEngine()
    summary, clean_records, quarantine_records = engine.process_batch(
        dataset_name="orders",
        records=raw_records,
        batch_id=batch_id,
    )

    # Persist batch outcomes to database
    db = get_db_manager()
    with db.get_session() as session:
        dw_repo = DataWarehouseRepository(session)
        q_repo = QuarantineRepository(session)

        # 1. Ingest clean records to production data warehouse
        dw_repo.save_clean_orders(clean_records, batch_id=batch_id)

        # 2. Ingest corrupted records to quarantine
        q_repo.save_quarantine_records(quarantine_records)

        # 3. Store quality and observability metrics
        dw_repo.save_metrics(summary)

    # Export HTML Data Docs certificate
    reporter = DataDocsReporter()
    doc_path = reporter.export_to_file(summary)

    ti.xcom_push(key="batch_summary", value=summary.model_dump(mode="json"))
    ti.xcom_push(key="data_docs_path", value=str(doc_path))

    logger.info(
        "Gatekeeper summary for %s: Health Score=%.2f%%, Passed=%d, Quarantined=%d",
        batch_id,
        summary.health_score.overall_score,
        summary.passed_records,
        summary.quarantined_records,
    )

    if summary.sla_breached:
        return "branch_sla_breached"
    return "branch_sla_passed"


def task_alert_sla_breach(**context) -> None:
    """Dispatch immediate Slack / Webhook alert on SLA failure."""
    ti = context["ti"]
    summary_dict = ti.xcom_pull(key="batch_summary", task_ids="validate_gatekeeper")
    from src.core.models import BatchSummary

    summary = BatchSummary(**summary_dict)
    dispatcher = AlertDispatcher()
    dispatcher.notify_batch_evaluation(summary)
    logger.warning("Dispatched SLA breach alert for batch %s", summary.batch_id)


def task_log_success(**context) -> None:
    """Log successful SLA compliance and pipeline execution."""
    ti = context["ti"]
    batch_id = ti.xcom_pull(key="batch_id", task_ids="extract_raw_batch")
    logger.info("Pipeline successfully completed for batch %s with full SLA compliance.", batch_id)


# Define DAG configuration
default_args = {
    "owner": "data-engineering-team",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

if DAG is not None:
    with DAG(
        dag_id="data_quality_gatekeeper_pipeline",
        default_args=default_args,
        description="Production Data Quality Gatekeeper, Quarantine & Observability Pipeline",
        schedule="0 2 * * *",  # Daily at 02:00 UTC
        catchup=False,
        max_active_runs=1,
        tags=["data-quality", "observability", "gatekeeper", "quarantine"],
    ) as dag:

        extract_task = PythonOperator(
            task_id="extract_raw_batch",
            python_callable=task_extract_raw_batch,
        )

        validation_task = BranchPythonOperator(
            task_id="validate_gatekeeper",
            python_callable=task_validate_gatekeeper,
        )

        sla_breach_task = PythonOperator(
            task_id="branch_sla_breached",
            python_callable=task_alert_sla_breach,
        )

        sla_passed_task = PythonOperator(
            task_id="branch_sla_passed",
            python_callable=task_log_success,
        )

        join_task = EmptyOperator(
            task_id="pipeline_complete",
            trigger_rule="none_failed_min_one_success",
        )

        extract_task >> validation_task >> [sla_breach_task, sla_passed_task] >> join_task
