#!/usr/bin/env bash
set -e

echo "========================================================="
echo "  Data Quality Gatekeeper & Observability Platform"
echo "========================================================="

# Create and activate virtualenv if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Initializing database & seeding sample records..."
python scripts/seed_data.py

echo "Starting Streamlit Observability Dashboard..."
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
