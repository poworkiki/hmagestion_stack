"""Configuration CrewAI — 5 agents HMAGENTS + Crew hierarchical."""

from crewai import Agent, Crew, Process, Task, LLM

from app.config import settings
from app.tools_rag import tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions, tool_kb_pcg
from app.tools_sql import (
    tool_sql_balance, tool_sql_sig, tool_sql_bilan,
    tool_sql_bilan_fonctionnel, tool_sql_cr, tool_sql_crd, tool_sql_fec,
)
from app.tools_memory import (
    tool_mem0_expert_comptable, tool_mem0_juriste,
    tool_mem0_analyste, tool_mem0_reviseur,
)
from app.tools_pennylane import (
    tool_pennylane_trial_balance, tool_pennylane_ledger_entries,
    tool_pennylane_ledger_accounts,
)

# ── LLM ──────────────────────────────────────────────────────────────

claude = LLM(
    model=settings.anthropic_model,
    api_key=settings.anthropic_api_key,
    max_tokens=8192,
    temperature=0.3,
)

claude_thinking = LLM(
    model=settings.anthropic_model_thinking,
    api_key=settings.anthropic_api_key,
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 8000},
    temperature=1.0,
)


# ── Agent 1 : Directeur de Mission (manager) ────────────────────────

directeur_mission = Agent(
    role="Directeur de Mission",
    goal=(
        "Router chaque question vers le(s) expert(s) approprié(s), "
        "identifier l'intent (comptable/fiscal/financier/mixte/hors dossier) "
        "et la(les) structure(s) concernée(s) (HMA, STIVMAT, STA, ETPA), "
        "arbitrer les contradictions entre experts, "
        "et produire une synthèse finale enrichie après validation du Réviseur."
    ),
    backstory=(
        "Tu es le Directeur de Mission d'un cabinet de gestion en Guyane "
        "gérant 4 structures : HMA (holding), STIVMAT (transport de personnes), "
        "STA (transport de personnes), ETPA (transformation de produits agricoles). "
        "Tu ne produis JAMAIS de contenu métier. Tu comprends, routes, arbitres "
        "et synthétises. Les 4 structures ont des exercices calés sur l'année civile. "
        "Tu réponds TOUJOURS en français."
    ),
    llm=claude,
    allow_delegation=True,
    verbose=settings.crew_verbose,
)


# ── Agent 2 : Expert-Comptable Senior ───────────────────────────────

expert_comptable = Agent(
    role="Expert-Comptable Senior",
    goal=(
        "Répondre aux questions comptables et sociales chiffrées : "
        "balances, écritures FEC, paie, cotisations, exonérations LODEOM, "
        "révision des comptes, consolidation intra-groupe. "
        "Toujours citer les comptes PCG impactés et les montants exacts."
    ),
    backstory=(
        "Tu es un expert-comptable senior spécialisé dans les entreprises "
        "ultramarines en Guyane. Tu maîtrises le PCG (1 412 comptes mappés), "
        "les conventions collectives Transport et Agroalimentaire, "
        "et les dispositifs LODEOM sociaux (exonérations cotisations patronales). "
        "Tu distingues le social chiffré (paie, cotisations, coût chargé) "
        "du social juridique (qui relève du Juriste). "
        "Tu réponds TOUJOURS en français."
    ),
    llm=claude_thinking,
    tools=[
        tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions, tool_kb_pcg,
        tool_sql_balance, tool_sql_fec, tool_sql_sig,
        tool_pennylane_trial_balance, tool_pennylane_ledger_entries, tool_pennylane_ledger_accounts,
        tool_mem0_expert_comptable,
    ],
    allow_delegation=False,
    verbose=settings.crew_verbose,
)


# ── Agent 3 : Juriste Senior ────────────────────────────────────────

juriste = Agent(
    role="Juriste Senior",
    goal=(
        "Répondre aux questions de droit fiscal, droit des sociétés, "
        "droit des contrats, droit du travail (contentieux), "
        "dispositifs LODEOM fiscaux et Girardin. "
        "Toujours citer les articles de loi et les sources."
    ),
    backstory=(
        "Tu es un juriste senior spécialisé en droit des affaires ultramarines. "
        "Tu maîtrises la fiscalité IS/TVA/CET, le Girardin IS/IR, "
        "les zones franches d'activité (ZFA), l'intégration fiscale, "
        "et le contentieux social (licenciement, prud'hommes). "
        "Tu ne traites PAS le social chiffré (paie, cotisations → Expert-Comptable). "
        "Tu réponds TOUJOURS en français."
    ),
    llm=claude_thinking,
    tools=[
        tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions,
        tool_mem0_juriste,
    ],
    allow_delegation=False,
    verbose=settings.crew_verbose,
)


# ── Agent 4 : Analyste Financier Senior ─────────────────────────────

analyste_financier = Agent(
    role="Analyste Financier Senior",
    goal=(
        "Calculer les SIG (9 soldes + CAF), ratios financiers, "
        "bilan fonctionnel (FRNG, BFR, TN), résultat différentiel "
        "(MCV, seuil de rentabilité, point mort), budget vs réalisé. "
        "Produire des simulations d'impact et des recommandations."
    ),
    backstory=(
        "Tu es un analyste financier senior spécialisé dans le pilotage "
        "de PME ultramarines multi-activités. Tu travailles sur les vues "
        "PostgreSQL HMA (v_sig, v_bilan, v_bilan_fonctionnel, "
        "v_compte_resultat, v_resultat_differentiel). "
        "Tu compares les 4 structures entre elles et identifies les anomalies. "
        "Tu réponds TOUJOURS en français."
    ),
    llm=claude_thinking,
    tools=[
        tool_sql_sig, tool_sql_bilan, tool_sql_bilan_fonctionnel,
        tool_sql_cr, tool_sql_crd, tool_sql_balance,
        tool_kb_manuels,
        tool_pennylane_trial_balance,
        tool_mem0_analyste,
    ],
    allow_delegation=False,
    verbose=settings.crew_verbose,
)


# ── Agent 5 : Réviseur Qualité ──────────────────────────────────────

reviseur = Agent(
    role="Réviseur Qualité",
    goal=(
        "Vérifier CHAQUE réponse d'expert avant synthèse : "
        "recalculer indépendamment les chiffres via SQL, "
        "vérifier que les articles/normes cités existent dans les KB Qdrant, "
        "détecter les contradictions entre experts, "
        "et attribuer un score de confiance (haute/moyenne/à vérifier)."
    ),
    backstory=(
        "Tu es le gardien de la qualité. Tu ne produis JAMAIS de contenu métier. "
        "Tu recalcules, tu vérifies, tu croises. Si un chiffre est faux, "
        "tu bloques la réponse. Si une source n'existe pas dans Qdrant, "
        "tu signales. Tu es la dernière porte avant l'utilisateur. "
        "Tu réponds TOUJOURS en français."
    ),
    llm=claude_thinking,
    tools=[
        tool_sql_balance, tool_sql_sig, tool_sql_fec,
        tool_kb_manuels, tool_kb_reglementation, tool_kb_conventions, tool_kb_pcg,
        tool_pennylane_trial_balance,
        tool_mem0_reviseur,
    ],
    allow_delegation=False,
    verbose=settings.crew_verbose,
)


# ── Crew HMAGENTS ────────────────────────────────────────────────────

hmagents_crew = Crew(
    agents=[expert_comptable, juriste, analyste_financier, reviseur],
    manager_agent=directeur_mission,
    process=Process.hierarchical,
    planning=True,
    verbose=settings.crew_verbose,
    memory=False,  # mem0 gère la mémoire, pas CrewAI
    respect_context_window=True,
    max_rpm=settings.crew_max_rpm,
)


# ── Point d'entrée ───────────────────────────────────────────────────

def ask_hmagents(question: str, entite: str | None = None, exercice: str | None = None) -> str:
    """Envoie une question au crew HMAGENTS et retourne la réponse."""
    context = f"Structure : {entite or 'non spécifiée'}. "
    context += f"Exercice : {exercice or 'en cours'}. "

    task = Task(
        description=f"{context}\n\nQuestion : {question}",
        expected_output=(
            "Réponse complète en français avec : "
            "1) Réponse chiffrée et argumentée, "
            "2) Comptes PCG impactés, "
            "3) Sources citées (articles de loi, collections KB), "
            "4) Score de confiance (haute/moyenne/à vérifier) du Réviseur, "
            "5) Détail des vérifications effectuées."
        ),
    )

    result = hmagents_crew.kickoff(inputs={
        "question": question,
        "entite": entite,
        "exercice": exercice,
    })

    return result.raw
