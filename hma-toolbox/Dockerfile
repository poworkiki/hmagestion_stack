FROM python:3.13-slim

LABEL maintainer="HMA Gestion <hmagestion@gmail.com>"
LABEL description="Toolbox ETL/scripts Python — sync Pennylane, PCG seed, Qdrant embeddings"

WORKDIR /app

# Dependances systeme (pg client pour debug si besoin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Scripts
COPY scripts/ ./scripts/

# Entrypoint : permet de lancer n'importe quel script
# Usage : docker exec hma-toolbox python scripts/sync-pennylane.py --structure HMA
# Ou en mode keep-alive pour executions repetees
ENTRYPOINT ["python"]
CMD ["--version"]
