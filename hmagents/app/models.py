"""Pydantic schemas — requêtes et réponses API HMAGENTS."""

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Requête utilisateur vers le crew HMAGENTS."""
    question: str = Field(..., description="Question en français", min_length=3)
    entite: str | None = Field(None, description="Structure : HMA, STIVMAT, STA ou ETPA")
    exercice: str | None = Field(None, description="Année d'exercice (ex: 2025)")


class QuestionResponse(BaseModel):
    """Réponse du crew HMAGENTS."""
    reponse: str
    entite: str | None = None
    exercice: str | None = None


class HealthResponse(BaseModel):
    """Health check."""
    status: str = "ok"
    service: str = "HMAGENTS"
    version: str = "1.0.0"
