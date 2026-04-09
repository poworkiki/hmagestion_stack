"""Configuration centralisée HMAGENTS — secrets depuis variables d'environnement."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Tous les secrets sont injectés via env vars (Coolify/Vaultwarden)."""

    # LLM — Anthropic Claude
    anthropic_api_key: str
    anthropic_model: str = "anthropic/claude-sonnet-4-6"
    anthropic_model_thinking: str = "anthropic/claude-sonnet-4-6"

    # Embeddings — OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"

    # Qdrant — stockage vectoriel
    qdrant_url: str = "https://qdrant.hma.business"
    qdrant_api_key: str = ""
    qdrant_port: int = 443

    # PostgreSQL HMA — données comptables
    hma_db_url: str

    # Pennylane API — tokens par structure
    pennylane_token_hma: str = ""
    pennylane_token_stivmat: str = ""
    pennylane_token_sta: str = ""
    pennylane_token_etpa: str = ""
    pennylane_base_url: str = "https://app.pennylane.com/api/external/v2"

    # Collections Qdrant — KB statiques
    kb_manuels: str = "kb_manuels"
    kb_reglementation: str = "kb_reglementation"
    kb_conventions: str = "kb_conventions"
    kb_pcg_analytique: str = "kb_pcg_analytique"

    # CrewAI
    crew_max_rpm: int = 30
    crew_verbose: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Mapping structure → token Pennylane
PENNYLANE_TOKENS: dict[str, str] = {
    "HMA": settings.pennylane_token_hma,
    "STIVMAT": settings.pennylane_token_stivmat,
    "STA": settings.pennylane_token_sta,
    "ETPA": settings.pennylane_token_etpa,
}
