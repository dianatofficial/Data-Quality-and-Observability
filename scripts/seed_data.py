"""
Data Seeding & Sample Generation Utility.
Generates test JSON files in the data/ folder and seeds the local SQLite/PostgreSQL database.
"""
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ingestion.generator import EnterpriseDataGenerator
from scripts.run_gatekeeper import run_pipeline


def main() -> None:
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Generating sample data batches in data/ directory...")

    # 1. Clean Batch
    clean_orders = EnterpriseDataGenerator.generate_clean_orders(count=150)
    (data_dir / "sample_clean_batch.json").write_text(
        json.dumps(clean_orders, indent=2), encoding="utf-8"
    )
    print("  -> Created data/sample_clean_batch.json (150 clean records)")

    # 2. Corrupted Batch
    corrupted_orders = EnterpriseDataGenerator.generate_corrupted_orders(
        total_count=150, corruption_rate=0.20
    )
    (data_dir / "sample_corrupted_batch.json").write_text(
        json.dumps(corrupted_orders, indent=2), encoding="utf-8"
    )
    print("  -> Created data/sample_corrupted_batch.json (150 records, 20% corrupted)")

    # 3. Schema Drifted Batch
    drifted_orders = EnterpriseDataGenerator.generate_drifted_orders(count=100)
    (data_dir / "sample_drifted_batch.json").write_text(
        json.dumps(drifted_orders, indent=2), encoding="utf-8"
    )
    print("  -> Created data/sample_drifted_batch.json (100 drifted records)")

    print("\n[*] Seeding local database with validation runs...")
    run_pipeline("orders", str(data_dir / "sample_clean_batch.json"))
    run_pipeline("orders", str(data_dir / "sample_corrupted_batch.json"))

    print("\n[+] Database and sample data successfully seeded!")


if __name__ == "__main__":
    main()
