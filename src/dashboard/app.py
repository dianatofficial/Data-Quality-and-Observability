"""
Automated Data Quality Gatekeeper & Observability Dashboard Module.
"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Mirror implementation from streamlit_app.py
from streamlit_app import *
