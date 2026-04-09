"""HMAGENTS — API FastAPI pour le système multi-agents comptable."""

from fastapi import FastAPI, HTTPException

from app.models import QuestionRequest, QuestionResponse, HealthResponse
from app.crew import ask_hmagents

app = FastAPI(
    title="HMAGENTS",
    description="Système multi-agents IA comptable — 5 agents (CrewAI + LlamaIndex + mem0 + Claude)",
    version="1.0.0",
)


@app.post("/ask", response_model=QuestionResponse)
async def ask(req: QuestionRequest):
    """Point d'entrée principal — envoie une question au crew HMAGENTS."""
    # Valider la structure si fournie
    if req.entite and req.entite.upper() not in ("HMA", "STIVMAT", "STA", "ETPA"):
        raise HTTPException(
            status_code=400,
            detail=f"Structure inconnue : {req.entite}. Valides : HMA, STIVMAT, STA, ETPA",
        )

    try:
        result = ask_hmagents(
            question=req.question,
            entite=req.entite,
            exercice=req.exercice,
        )
        return QuestionResponse(
            reponse=result,
            entite=req.entite,
            exercice=req.exercice,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check pour Uptime Kuma / Coolify."""
    return HealthResponse()
