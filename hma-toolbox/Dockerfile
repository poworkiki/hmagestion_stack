FROM python:3.13-slim

LABEL maintainer="HMA Gestion <hmagestion@gmail.com>"
LABEL description="Toolbox HMA — API ETL FastAPI (sync Pennylane pour n8n)"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API + scripts ETL
COPY api.py ./
COPY scripts/ ./scripts/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# FastAPI uniquement (Streamlit deplace vers hma-streamlit)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
