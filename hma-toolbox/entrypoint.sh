#!/bin/bash
set -e

echo "[entrypoint] Installation des dependances..."
apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
pip install --no-cache-dir pg8000 requests fastapi uvicorn streamlit streamlit-echarts 2>&1 | tail -1

echo "[entrypoint] Clone du repo..."
rm -rf /tmp/repo
git clone --depth 1 --branch 002-dashboard-crd-custom \
  https://${GITHUB_PAT}@github.com/poworkiki/hmagestion_stack.git /tmp/repo

echo "[entrypoint] Copie des fichiers..."
mkdir -p /app/scripts
cp /tmp/repo/hma-toolbox/api.py /app/api.py
cp /tmp/repo/hma-toolbox/app_streamlit.py /app/app_streamlit.py
cp /tmp/repo/hma-toolbox/scripts/*.py /app/scripts/
rm -rf /tmp/repo

echo "[entrypoint] Demarrage FastAPI (port 8000)..."
cd /app
uvicorn api:app --host 0.0.0.0 --port 8000 &

echo "[entrypoint] Demarrage Streamlit (port 8501)..."
exec streamlit run app_streamlit.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
