FROM python:3.13-slim

LABEL maintainer="HMA Gestion <hmagestion@gmail.com>"
LABEL description="Toolbox HMA — API sync (FastAPI) + Dashboard checks (Streamlit)"

WORKDIR /app

# Dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python (pre-installees dans l'image = demarrage instantane)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY api.py app_streamlit.py entrypoint.sh ./
COPY scripts/ ./scripts/
RUN chmod +x entrypoint.sh

EXPOSE 8000 8501

# FastAPI :8000 (API sync pour n8n) + Streamlit :8501 (dashboard checks)
CMD ["bash", "entrypoint.sh"]
