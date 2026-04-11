"""
API hma-toolbox — Mini serveur FastAPI pour orchestration depuis n8n.

Endpoints :
  GET  /health              → Health check
  POST /sync                → Sync Pennylane → grand_livre (toutes structures)
  POST /sync/{structure}    → Sync une seule structure
  POST /sync-full           → Force re-sync complet
  POST /refresh             → Refresh conditionnel balance_generale
  GET  /status              → Dernier etat sync (sync_metadata)

Reseau Docker : coolify (accessible depuis n8n via http://toolbox-xxx:8000)
"""
import asyncio
import os
import subprocess
import sys
from datetime import datetime

import pg8000
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse

app = FastAPI(title="hma-toolbox", version="1.0.0")

# --- State ---
_running_sync = None  # asyncio.Task en cours


def get_db():
    """Connexion PostgreSQL HMA."""
    conn = pg8000.connect(
        host=os.environ.get('PG_HOST', 'postgresql_hma'),
        port=int(os.environ.get('PG_PORT', '5432')),
        database=os.environ.get('PG_DATABASE', 'postgres'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ['PG_PASSWORD'],
    )
    conn.autocommit = True
    return conn


def run_sync(args: list[str] | None = None) -> dict:
    """Execute sync-pennylane-gl.py en subprocess et retourne le resultat."""
    cmd = [sys.executable, '/app/scripts/sync-pennylane-gl.py']
    if args:
        cmd.extend(args)

    t0 = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    duree = round((datetime.now() - t0).total_seconds(), 1)

    stdout = result.stdout or ''
    stderr = result.stderr or ''
    lines = stdout.split('\n')

    resume = [l for l in lines if '|' in l and 'lignes' in l]
    erreurs = [l for l in lines if 'ERREUR' in l]
    termine = any('Termine' in l or 'Termine' in l for l in lines)

    return {
        'status': 'ok' if termine and not erreurs and result.returncode == 0 else 'error',
        'returncode': result.returncode,
        'duree_s': duree,
        'resume': resume,
        'erreurs': erreurs if erreurs else None,
        'stderr': stderr.strip() if stderr.strip() else None,
        'nb_lines_stdout': len([l for l in lines if l.strip()]),
    }


# --- Endpoints ---

@app.get("/health")
def health():
    """Health check — verifie la connexion DB."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM grand_livre")
        nb = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return {"status": "ok", "grand_livre_rows": nb, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


@app.post("/sync")
def sync_all():
    """Sync les 4 structures Pennylane → grand_livre."""
    global _running_sync
    if _running_sync and not _running_sync.done():
        return JSONResponse(status_code=409, content={"status": "busy", "detail": "Sync deja en cours"})

    result = run_sync()
    return result


@app.post("/sync/{structure}")
def sync_one(structure: str):
    """Sync une seule structure."""
    code = structure.upper()
    if code not in ('HMA', 'STIVMAT', 'STA', 'ETPA'):
        return JSONResponse(status_code=400, content={"status": "error", "detail": f"Structure inconnue: {code}"})

    result = run_sync(['--structure', code])
    return result


@app.post("/sync-full")
def sync_full():
    """Force re-sync complet (purge + re-import) des 4 structures."""
    result = run_sync(['--full'])
    return result


@app.post("/sync-full/{structure}")
def sync_full_one(structure: str):
    """Force re-sync complet d'une seule structure."""
    code = structure.upper()
    if code not in ('HMA', 'STIVMAT', 'STA', 'ETPA'):
        return JSONResponse(status_code=400, content={"status": "error", "detail": f"Structure inconnue: {code}"})

    result = run_sync(['--full', '--structure', code])
    return result


@app.post("/refresh")
def refresh_views():
    """Refresh conditionnel balance_generale."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_views_if_needed()")
        row = cursor.fetchone()
        refreshed, reason = row[0], row[1]
        cursor.close()
        conn.close()
        return {"status": "ok", "refreshed": refreshed, "reason": reason}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/status")
def sync_status():
    """Retourne l'etat de synchronisation depuis sync_metadata."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.code, sm.endpoint, sm.status, sm.last_sync_at,
                   sm.row_count_local, sm.sync_duration_s
            FROM sync_metadata sm
            JOIN entite e ON e.id = sm.entite_id
            ORDER BY e.code, sm.endpoint
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "status": "ok",
            "structures": [
                {
                    "code": r[0], "endpoint": r[1], "sync_status": r[2],
                    "last_sync": r[3].isoformat() if r[3] else None,
                    "rows_local": r[4], "duration_s": float(r[5]) if r[5] else None,
                }
                for r in rows
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
