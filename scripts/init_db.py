"""
Database schema bootstrap script.
Initializes all necessary clean tables, quarantine tables, and metrics logs.
"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.storage.database import get_db_manager


def main() -> None:
    print("[*] Bootstrapping database schema...")
    db_mgr = get_db_manager()
    db_mgr.init_schema()
    print("[+] Database schema initialized successfully.")


if __name__ == "__main__":
    main()
