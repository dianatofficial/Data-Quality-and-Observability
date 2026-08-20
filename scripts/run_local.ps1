# PowerShell startup script for Data Quality Gatekeeper

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  Data Quality Gatekeeper & Observability Platform" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Initializing database & seeding sample records..." -ForegroundColor Yellow
python scripts/seed_data.py

Write-Host "Starting Streamlit Observability Dashboard..." -ForegroundColor Green
streamlit run streamlit_app.py --server.port=8501
