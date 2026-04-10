#!/bin/bash
set -e

echo "[entrypoint] Demarrage FastAPI (port 8000)..."
cd /app
uvicorn api:app --host 0.0.0.0 --port 8000 &

echo "[entrypoint] Demarrage Streamlit (port 8501)..."
exec streamlit run app_streamlit.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
