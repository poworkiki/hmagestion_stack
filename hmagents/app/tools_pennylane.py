"""Outil Pennylane API — Accès direct aux données comptables des 4 structures."""

import requests
from crewai.tools import tool

from app.config import settings, PENNYLANE_TOKENS

PENNYLANE_BASE = settings.pennylane_base_url


def _pennylane_get(
    endpoint: str,
    structure: str,
    params: dict | None = None,
) -> dict | list:
    """Appel GET paginé à l'API Pennylane v2."""
    token = PENNYLANE_TOKENS.get(structure.upper())
    if not token:
        return {"error": f"Structure inconnue : {structure}. Valides : HMA, STIVMAT, STA, ETPA"}

    headers = {"Authorization": f"Bearer {token}"}
    all_results = []
    cursor = None
    page_params = {"limit": 100, "use_2026_api_changes": "true"}
    if params:
        page_params.update(params)

    while True:
        if cursor:
            page_params["cursor"] = cursor

        resp = requests.get(
            f"{PENNYLANE_BASE}/{endpoint}",
            headers=headers,
            params=page_params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # Les résultats sont dans une clé variable selon l'endpoint
        for key in data:
            if isinstance(data[key], list):
                all_results.extend(data[key])
                break

        if not data.get("has_more", False):
            break
        cursor = data.get("cursor")

    return all_results


@tool("pennylane_trial_balance")
def tool_pennylane_trial_balance(structure: str, period_start: str, period_end: str) -> str:
    """Balance des comptes d'une structure via l'API Pennylane.
    Structure : HMA, STIVMAT, STA ou ETPA.
    Dates : format YYYY-MM-DD (ex: 2025-01-01, 2025-12-31)."""
    try:
        results = _pennylane_get(
            "trial_balance",
            structure,
            {"period_start": period_start, "period_end": period_end},
        )
        if isinstance(results, dict) and "error" in results:
            return results["error"]

        lines = []
        for r in results[:50]:  # Limiter pour le contexte
            num = r.get("number", "?")
            label = r.get("label", "?")
            debit = r.get("debit", 0)
            credit = r.get("credit", 0)
            balance = r.get("balance", 0)
            lines.append(f"{num} {label}: D={debit:.2f} C={credit:.2f} S={balance:.2f}")

        header = f"Balance {structure} ({period_start} → {period_end}) — {len(results)} comptes"
        if len(results) > 50:
            header += f" (50 premiers affichés sur {len(results)})"
        return f"{header}\n" + "\n".join(lines)
    except Exception as e:
        return f"Erreur API Pennylane : {e}"


@tool("pennylane_ledger_entries")
def tool_pennylane_ledger_entries(
    structure: str,
    journal_code: str = "",
    start_date: str = "",
    end_date: str = "",
) -> str:
    """Écritures comptables d'une structure via l'API Pennylane.
    Structure : HMA, STIVMAT, STA ou ETPA.
    Filtres optionnels : journal_code, start_date, end_date (YYYY-MM-DD)."""
    try:
        params = {}
        if journal_code:
            params["journal_code"] = journal_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        results = _pennylane_get("ledger_entries", structure, params)
        if isinstance(results, dict) and "error" in results:
            return results["error"]

        lines = []
        for r in results[:30]:
            date = r.get("date", "?")
            journal = r.get("journal", {}).get("code", "?")
            label = r.get("label", "?")[:60]
            lines.append(f"{date} [{journal}] {label}")

        header = f"Écritures {structure} — {len(results)} entrées"
        if len(results) > 30:
            header += f" (30 premières sur {len(results)})"
        return f"{header}\n" + "\n".join(lines)
    except Exception as e:
        return f"Erreur API Pennylane : {e}"


@tool("pennylane_ledger_accounts")
def tool_pennylane_ledger_accounts(structure: str, search: str = "") -> str:
    """Plan comptable d'une structure via l'API Pennylane (1 412 comptes).
    Structure : HMA, STIVMAT, STA ou ETPA.
    search : filtrer par numéro ou libellé (optionnel)."""
    try:
        results = _pennylane_get("ledger_accounts", structure, {"limit": 1000})
        if isinstance(results, dict) and "error" in results:
            return results["error"]

        if search:
            search_lower = search.lower()
            results = [
                r for r in results
                if search_lower in str(r.get("number", "")).lower()
                or search_lower in str(r.get("label", "")).lower()
            ]

        lines = []
        for r in results[:50]:
            num = r.get("number", "?")
            label = r.get("label", "?")
            lines.append(f"{num} — {label}")

        return f"Comptes {structure} — {len(results)} résultats\n" + "\n".join(lines)
    except Exception as e:
        return f"Erreur API Pennylane : {e}"


# Export pour crew.py
ALL_PENNYLANE_TOOLS = [
    tool_pennylane_trial_balance,
    tool_pennylane_ledger_entries,
    tool_pennylane_ledger_accounts,
]
