"""
Apache Airflow DAG: Quarantine Reconciliation & Replay Pipeline
Scans approved/resolved quarantine records and replays them into clean warehouse tables.
"""
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None
    PythonOperator = None

from src.storage.database import get_db_manager
from src.storage.repositories import DataWarehouseRepository, QuarantineRepository

logger = logging.getLogger("airflow.task")


def task_process_reconciliation_queue(**context) -> int:
    """Scan and promote reconciled quarantine records to clean production tables."""
    db = get_db_manager()
    reconciled_count = 0

    with db.get_session() as session:
        q_repo = QuarantineRepository(session)
        dw_repo = DataWarehouseRepository(session)

        # Fetch records approved for reconciliation
        pending_replays = q_repo.get_quarantined_records(status="RECONCILED", limit=200)

        orders_to_reingest = []
        for rec in pending_replays:
            raw_payload = rec.get("raw_payload", {})
            if rec.get("entity_type") == "orders" and "order_id" in raw_payload:
                orders_to_reingest.append(raw_payload)
                reconciled_count += 1

        if orders_to_reingest:
            batch_id = f"REPLAY-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            dw_repo.save_clean_orders(orders_to_reingest, batch_id=batch_id)
            logger.info("Successfully replayed %d reconciled records into clean_orders", len(orders_to_reingest))

    return reconciled_count


default_args = {
    "owner": "data-engineering-team",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

if DAG is not None:
    with DAG(
        dag_id="quarantine_reconciliation_pipeline",
        default_args=default_args,
        description="Replays and syncs approved quarantine records into primary clean tables",
        schedule="0 */4 * * *",  # Every 4 hours
        catchup=False,
        max_active_runs=1,
        tags=["data-quality", "quarantine", "reconciliation"],
    ) as dag:

        reconcile_task = PythonOperator(
            task_id="process_reconciliation_queue",
            python_callable=task_process_reconciliation_queue,
        )
