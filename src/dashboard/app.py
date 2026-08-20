"""
Data Quality Gatekeeper & Observability Dashboard Module.
"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def run_dashboard():
    """Execute dashboard from CLI or script."""
    import streamlit.web.cli as stcli
    app_path = str(BASE_DIR / "streamlit_app.py")
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())


if __name__ == "__main__":
    run_dashboard()
