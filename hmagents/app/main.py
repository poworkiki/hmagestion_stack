"""HMAGENTS — API FastAPI pour le système multi-agents comptable."""

import os
import re
import json
import time
import logging
import threading
import urllib.request
import urllib.error
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.models import QuestionRequest, QuestionResponse, HealthResponse
from app.crew import ask_hmagents

log = logging.getLogger("hmagents.telegram")

# ── Telegram Bot (polling) ─────────────────────────────────────────

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ENTITES = ["HMA", "STIVMAT", "STA", "ETPA"]
POLL_TIMEOUT = 30

WELCOME_MSG = (
    "Salut {name} !\n\n"
    "Je suis le bot des agents comptables HMA.\n\n"
    "Pose-moi une question sur les 4 structures :\n"
    "- HMA (Holding)\n"
    "- STIVMAT (Transport)\n"
    "- STA (Transport)\n"
    "- ETPA (Agro-alimentaire)\n\n"
    "Exemples :\n"
    "- Quel est le CA de STIVMAT en 2025 ?\n"
    "- Analyse le SIG de ETPA\n"
    "- Montre le bilan de HMA"
)


def _tg_api(method, data=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    if data:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=POLL_TIMEOUT + 10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.error("Telegram API %s: %s", e.code, e.read().decode("utf-8", errors="replace"))
        return {"ok": False}
    except Exception as e:
        log.error("Telegram API error: %s", e)
        return {"ok": False}


def _tg_send(chat_id, text):
    if len(text) > 4000:
        text = text[:3997] + "..."
    _tg_api("sendMessage", {"chat_id": chat_id, "text": text})


def _tg_parse(text):
    entite = None
    for e in ENTITES:
        if e in text.upper():
            entite = e
            break
    year_match = re.search(r"\b(202[0-9])\b", text)
    exercice = year_match.group(1) if year_match else str(time.localtime().tm_year)
    return entite, exercice


def _tg_handle(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    first_name = message.get("from", {}).get("first_name", "Utilisateur")

    if not text:
        return

    if text.strip() in ("/start", "/help"):
        _tg_send(chat_id, WELCOME_MSG.format(name=first_name))
        return

    entite, exercice = _tg_parse(text)
    _tg_api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    _tg_send(chat_id, "Analyse en cours... Les agents travaillent sur ta question.")

    try:
        reponse = ask_hmagents(question=text, entite=entite, exercice=exercice)
    except Exception as e:
        log.error("HMAGENTS error: %s", e)
        reponse = f"Erreur lors de la consultation des agents : {e}"

    header = f"{entite or 'Toutes structures'} - Exercice {exercice}\n\n"
    _tg_send(chat_id, header + reponse)


def _tg_polling_loop():
    _tg_api("deleteWebhook")
    log.info("Telegram bot demarre en mode polling")
    offset = 0
    while True:
        try:
            result = _tg_api("getUpdates", {
                "offset": offset,
                "timeout": POLL_TIMEOUT,
                "allowed_updates": ["message"],
            })
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    try:
                        _tg_handle(update["message"])
                    except Exception as e:
                        log.error("Handle error: %s", e)
                        chat_id = update["message"].get("chat", {}).get("id")
                        if chat_id:
                            _tg_send(chat_id, f"Erreur interne : {e}")
        except Exception as e:
            log.error("Polling error: %s", e)
            time.sleep(5)


# ── FastAPI lifecycle ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if TELEGRAM_TOKEN:
        t = threading.Thread(target=_tg_polling_loop, daemon=True)
        t.start()
        log.info("Telegram polling thread started")
    else:
        log.info("TELEGRAM_BOT_TOKEN absent — bot Telegram desactive")
    yield


app = FastAPI(
    title="HMAGENTS",
    description="Systeme multi-agents IA comptable — 5 agents (CrewAI + LlamaIndex + mem0 + Claude)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/ask", response_model=QuestionResponse)
async def ask(req: QuestionRequest):
    """Point d'entree principal — envoie une question au crew HMAGENTS."""
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
