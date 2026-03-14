$ErrorActionPreference = "Stop"

python scripts/bootstrap_streamlit_secrets.py

$port = if ($env:PORT) { $env:PORT } else { "8501" }
python -m streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port $port
