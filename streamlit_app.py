"""
Root entrypoint for Streamlit Community Cloud and HuggingFace Spaces.
Explicitly executes dashboard rendering on every session lifecycle run.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
from src.dashboard.app import render_dashboard

# Streamlit Page Config
st.set_page_config(
    page_title="Data Quality Gatekeeper & Observability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Execute main dashboard view
render_dashboard()
