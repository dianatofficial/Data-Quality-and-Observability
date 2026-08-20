#!/usr/bin/env bash
set -e

echo "Starting Data Quality Gatekeeper Service..."
python scripts/init_db.py

exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
