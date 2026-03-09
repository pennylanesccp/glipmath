$ErrorActionPreference = "Stop"
$env:PYTHONPATH = (Resolve-Path ".").Path
python -m streamlit run app/streamlit_app.py
