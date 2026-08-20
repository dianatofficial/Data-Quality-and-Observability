"""
Root entrypoint for Streamlit Community Cloud and HuggingFace Spaces.
Automatically manages Python path and launches the Data Quality Gatekeeper UI.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import and execute main dashboard
from src.dashboard.app import *
