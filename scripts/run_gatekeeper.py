"""
CLI Entrypoint for running the Data Quality Gatekeeper on input data files.
Usage:
    python scripts/run_gatekeeper.py --dataset orders --input data/sample_corrupted_batch.json
"""
import argparse
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.table import Table

from src.alerts.notifier import AlertDispatcher
from src.core.engine import GatekeeperEngine
from src.core.reporter import DataDocsReporter
from src.ingestion.extractor import BatchExtractor
from src.ingestion.generator import EnterpriseDataGenerator
from src.storage.database import get_db_manager
from src.storage.repositories import DataWarehouseRepository, QuarantineRepository

console = Console()


def run_pipeline(dataset: str, input_path: str | None, generate_mock: bool = False, count: int = 100) -> None:
    console.rule("[bold blue]Data Quality Gatekeeper Pipeline[/bold blue]")

    # Extract or generate records
    if generate_mock or not input_path:
        console.print(f"[yellow]Generating {count} synthetic {dataset} records (with anomalies)...[/yellow]")
        if dataset == "orders":
            records = EnterpriseDataGenerator.generate_corrupted_orders(total_count=count, corruption_rate=0.20)
        else:
            records = EnterpriseDataGenerator.generate_customers(count=count, corrupted_count=15)
    else:
        path = Path(input_path)
        console.print(f"[cyan]Loading input file: {path}[/cyan]")
        if path.suffix == ".csv":
            records = BatchExtractor.extract_from_csv(path)
        else:
            records = BatchExtractor.extract_from_json(path)

    console.print(f"Extracted [bold]{len(records)}[/bold] records.")

    # Initialize Engine & Process Batch
    engine = GatekeeperEngine()
    summary, clean_records, quarantine_records = engine.process_batch(
        dataset_name=dataset,
        records=records,
    )

    # Persist to Database
    db_mgr = get_db_manager()
    db_mgr.init_schema()
    with db_mgr.get_session() as session:
        dw_repo = DataWarehouseRepository(session)
        q_repo = QuarantineRepository(session)

        if dataset == "orders":
            dw_repo.save_clean_orders(clean_records, summary.batch_id)
        elif dataset == "customers":
            dw_repo.save_clean_customers(clean_records, summary.batch_id)

        q_repo.save_quarantine_records(quarantine_records)
        dw_repo.save_metrics(summary)

    # Export HTML Report
    reporter = DataDocsReporter()
    report_file = reporter.export_to_file(summary)

    # Display Rich Terminal Output
    table = Table(title=f"Gatekeeper Outcome: {summary.batch_id}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")

    status_color = "green" if not summary.sla_breached else "red"
    table.add_row("Dataset Name", summary.dataset_name)
    table.add_row("Total Records", str(summary.total_records))
    table.add_row("Clean Ingested", f"[green]{summary.passed_records} ({summary.pass_rate}%)[/green]")
    table.add_row("Quarantined", f"[red]{summary.quarantined_records} ({summary.error_rate * 100:.2f}%)[/red]")
    table.add_row("Health Score", f"[{status_color}]{summary.health_score.overall_score}%[/{status_color}]")
    table.add_row("Completeness", f"{summary.health_score.completeness}%")
    table.add_row("Validity", f"{summary.health_score.validity}%")
    table.add_row("Uniqueness", f"{summary.health_score.uniqueness}%")
    table.add_row("Timeliness", f"{summary.health_score.timeliness}%")
    table.add_row("Consistency", f"{summary.health_score.consistency}%")
    table.add_row("Schema Drift", "[YES]" if summary.schema_drift.detected else "[NONE]")
    table.add_row("SLA Compliance", f"[{status_color}]{'PASSED' if not summary.sla_breached else 'BREACHED'}[/{status_color}]")
    table.add_row("Processing Duration", f"{summary.processing_duration_ms} ms")

    console.print(table)
    console.print(f"[bold green][+] HTML Data Docs generated:[/bold green] {report_file.resolve()}")

    # Dispatch alerts if SLA is breached
    if summary.sla_breached:
        console.print("[bold red][!] SLA Breached - Dispatching Slack Notification...[/bold red]")
        dispatcher = AlertDispatcher()
        dispatcher.notify_batch_evaluation(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Data Quality Gatekeeper CLI")
    parser.add_argument("--dataset", type=str, default="orders", choices=["orders", "customers"], help="Dataset name")
    parser.add_argument("--input", type=str, default=None, help="Path to input JSON/CSV file")
    parser.add_argument("--mock", action="store_true", help="Generate synthetic mock batch")
    parser.add_argument("--count", type=int, default=100, help="Record count for synthetic mock")

    args = parser.parse_args()
    run_pipeline(args.dataset, args.input, args.mock, args.count)


if __name__ == "__main__":
    main()
