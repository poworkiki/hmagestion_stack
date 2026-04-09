# HMAGENTS — Configuration du Stack Multi-Agents

**Date** : 2026-04-09 | **Chantier** : D (Agents) + E (Mémoire)
**Prérequis** : Chantier A terminé (socle données PostgreSQL HMA)

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HMAGENTS (Docker)                            │
│                                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐    ┌───────────┐ │
│  │   CrewAI     │    │  LlamaIndex  │    │   mem0    │    │  FastAPI  │ │
│  │ Orchestration│◄──►│  RAG + Tools │    │  Mémoire  │    │  API HTTP │ │
│  │ 5 agents     │    │  KB + SQL    │    │  agents   │    │  webhook  │ │
│  └──────┬───────┘    └──────┬───────┘    └─────┬─────┘    └─────┬─────┘ │
│         │                   │                  │                │       │
└─────────┼───────────────────┼──────────────────┼────────────────┼───────┘
          │                   │                  │                │
          ▼                   ▼                  ▼                ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  ┌───────────┐
   │   Claude     │    │   Qdrant    │    │   Qdrant    │  │    n8n    │
   │  (Anthropic) │    │  KB (read)  │    │  mem (r/w)  │  │  trigger  │
   │   LLM        │    │ 4 collections│   │ 4 collections│ │  + ETL   │
   └─────────────┘    └──────┬───────┘    └─────────────┘  └───────────┘
                             │
                      ┌──────┴───────┐
                      │ PostgreSQL   │
                      │ HMA (vues    │
                      │ matérialisées│
                      │ + FEC)       │
                      └──────────────┘
```

---

## Stack technique

| Composant | Rôle | Version | Déploiement |
|-----------|------|---------|-------------|
| **CrewAI** | Orchestration multi-agents (hierarchical process) | latest | Docker (hmagents) |
| **LlamaIndex** | RAG framework — QueryEngine sur Qdrant + PostgreSQL | latest | Docker (hmagents) |
| **mem0 OSS** | Mémoire long terme agents (add/search/update/delete) | latest | Docker (hmagents) |
| **FastAPI** | API HTTP — point d'entrée pour n8n, chat, webhooks | latest | Docker (hmagents) |
| **Claude** | LLM raisonnement (Anthropic API) | claude-sonnet-4-6 | API externe |
| **OpenAI** | Embeddings uniquement | text-embedding-3-small | API externe |
| **Qdrant** | Stockage vectoriel (KB + mémoire agents) | déjà déployé | qdrant.hma.business |
| **PostgreSQL HMA** | Données comptables (FEC, vues matérialisées) | déjà déployé | hma-db |
| **n8n** | ETL Pennylane + déclencheur HMAGENTS | déjà déployé | n8n.hma.business |

---

## Rôle de chaque framework

### CrewAI — Orchestration des 5 agents

CrewAI gère le **qui fait quoi** : routage, délégation, parallélisme, synthèse.

| Concept CrewAI | Mapping HMAGENTS |
|---|---|
| `Crew` | L'équipe complète HMAGENTS |
| `Process.hierarchical` | Le Directeur de Mission est le `manager_agent` |
| `Agent` (×4) | Expert-Comptable, Juriste, Analyste Financier, Réviseur Qualité |
| `Task` | La question utilisateur décomposée en sous-tâches par le manager |
| `Tool` | Les outils LlamaIndex + mem0 assignés à chaque agent |
| `LLM` | Claude (Anthropic) pour tous les agents |

**Pourquoi CrewAI** : le pattern `hierarchical` avec `manager_agent` correspond exactement à l'architecture Directeur de Mission → Experts → Réviseur. CrewAI gère nativement la délégation parallèle (FR-002), le routage (FR-001) et la synthèse.

### LlamaIndex — Accès aux données (RAG + SQL)

LlamaIndex gère le **accès aux données** : recherche sémantique dans les KB Qdrant + requêtes SQL sur PostgreSQL HMA.

| Concept LlamaIndex | Mapping HMAGENTS |
|---|---|
| `QdrantVectorStore` | Connexion aux 4 KB Qdrant (manuels, réglementation, conventions, PCG) |
| `VectorStoreIndex` | Index de recherche sémantique sur chaque KB |
| `QueryEngine` | Moteur de requête RAG (question → chunks pertinents → réponse) |
| `QueryEngineTool` | Outil CrewAI wrappant un QueryEngine (un par KB) |
| `SQLDatabase` | Connexion PostgreSQL HMA (vues matérialisées) |
| `NLSQLTableQueryEngine` | Requêtes SQL en langage naturel sur les vues |
| `OpenAIEmbedding` | Modèle d'embeddings `text-embedding-3-small` |

**Pourquoi LlamaIndex** : il fournit l'abstraction RAG (Qdrant) + SQL (PostgreSQL) en outils natifs que CrewAI consomme directement. Pas besoin de code custom pour le retrieval.

### mem0 OSS — Mémoire agents

mem0 gère le **apprentissage** : ce que chaque agent retient d'une session à l'autre.

| Concept mem0 | Mapping HMAGENTS |
|---|---|
| `Memory.from_config()` | Instance mem0 configurée sur Qdrant + OpenAI embeddings |
| `memory.add()` | Stocker un output d'agent après validation |
| `memory.search()` | Retrouver les outputs similaires passés (mémoire long terme) |
| `memory.update()` | Mettre à jour une mémoire après correction (feedback) |
| `memory.delete()` | Supprimer une mémoire obsolète |
| `user_id` | Identifiant de l'agent (`expert_comptable`, `juriste`, etc.) |
| `metadata` | Tags : entité, exercice, domaine, score |

**Pourquoi mem0** : il remplace le code custom de gestion mémoire Qdrant (embeddings manuels, upsert, déduplication). mem0 gère tout ça nativement + résolution de conflits mémoire.

**Ce que mem0 ne remplace PAS** :
- `agent_session` (PostgreSQL) → contexte court terme partagé entre agents dans une conversation
- `agent_feedback` (PostgreSQL) → scoring 1-5, corrections, few-shot injection

---

## Configuration CrewAI — Les 5 agents

```python
from crewai import Agent, Crew, Process, Task, LLM

# ── LLM ──────────────────────────────────────────────────────────────
claude = LLM(
    model="anthropic/claude-sonnet-4-6",
    api_key=ANTHROPIC_API_KEY,       # depuis Vaultwarden
    max_tokens=8192,
    temperature=0.3,                  # déterministe pour la comptabilité
)

claude_thinking = LLM(
    model="anthropic/claude-sonnet-4-6",
    api_key=ANTHROPIC_API_KEY,
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 8000},  # extended thinking
    temperature=1.0,                  # requis par Anthropic pour thinking
)

# ── Agent 1 : Directeur de Mission (manager_agent) ──────────────────
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
        "et synthétises. Les 4 structures ont des exercices calés sur l'année civile."
    ),
    llm=claude,
    allow_delegation=True,
    verbose=True,
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
        "du social juridique (qui relève du Juriste)."
    ),
    llm=claude_thinking,
    tools=[
        tool_kb_manuels,              # LlamaIndex QueryEngineTool
        tool_kb_reglementation,
        tool_kb_conventions,
        tool_kb_pcg,
        tool_sql_balance,             # LlamaIndex NLSQLTableQueryEngine
        tool_sql_fec,
        tool_sql_sig,
        tool_pennylane_api,           # Custom Tool : appel API Pennylane
        tool_mem0_expert_comptable,   # mem0 search/add
    ],
    allow_delegation=False,
    verbose=True,
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
        "Tu ne traites PAS le social chiffré (paie, cotisations → Expert-Comptable)."
    ),
    llm=claude_thinking,
    tools=[
        tool_kb_manuels,
        tool_kb_reglementation,
        tool_kb_conventions,
        tool_mem0_juriste,
    ],
    allow_delegation=False,
    verbose=True,
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
        "matérialisées PostgreSQL HMA (mv_sig, mv_bilan, mv_bilan_fonctionnel, "
        "mv_compte_resultat, mv_resultat_differentiel). "
        "Tu compares les 4 structures entre elles et identifies les anomalies."
    ),
    llm=claude_thinking,
    tools=[
        tool_sql_sig,
        tool_sql_bilan,
        tool_sql_bilan_fonctionnel,
        tool_sql_cr,
        tool_sql_crd,
        tool_sql_balance,
        tool_kb_manuels,
        tool_pennylane_api,
        tool_mem0_analyste,
    ],
    allow_delegation=False,
    verbose=True,
)

# ── Agent 5 : Réviseur Qualité ──────────────────────────────────────
reviseur = Agent(
    role="Réviseur Qualité",
    goal=(
        "Vérifier CHAQUE réponse d'expert avant synthèse : "
        "recalculer indépendamment les chiffres via SQL, "
        "vérifier que les articles/normes cités existent dans KB_QDRANT, "
        "détecter les contradictions entre experts, "
        "et attribuer un score de confiance (haute/moyenne/à vérifier)."
    ),
    backstory=(
        "Tu es le gardien de la qualité. Tu ne produis JAMAIS de contenu métier. "
        "Tu recalcules, tu vérifies, tu croises. Si un chiffre est faux, "
        "tu bloques la réponse. Si une source n'existe pas dans Qdrant, "
        "tu signales. Tu es la dernière porte avant l'utilisateur."
    ),
    llm=claude_thinking,
    tools=[
        tool_sql_balance,
        tool_sql_sig,
        tool_sql_fec,
        tool_kb_manuels,
        tool_kb_reglementation,
        tool_kb_conventions,
        tool_kb_pcg,
        tool_pennylane_api,
        tool_mem0_reviseur,
    ],
    allow_delegation=False,
    verbose=True,
)
```

---

## Configuration LlamaIndex — Outils RAG + SQL

```python
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from sqlalchemy import create_engine
import qdrant_client

# ── Embeddings (partagés) ────────────────────────────────────────────
embed_model = OpenAIEmbedding(
    model_name="text-embedding-3-small",
    api_key=OPENAI_API_KEY,            # depuis Vaultwarden
)
Settings.embed_model = embed_model

# ── Client Qdrant ────────────────────────────────────────────────────
qclient = qdrant_client.QdrantClient(
    url="https://qdrant.hma.business",
    api_key=QDRANT_API_KEY,            # depuis Vaultwarden
    port=443,
    https=True,
)

# ── KB Qdrant → QueryEngineTools ─────────────────────────────────────
def make_kb_tool(collection_name: str, description: str) -> QueryEngineTool:
    """Crée un outil LlamaIndex RAG sur une collection Qdrant."""
    vector_store = QdrantVectorStore(
        client=qclient,
        collection_name=collection_name,
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )
    query_engine = index.as_query_engine(
        similarity_top_k=10,
        response_mode="tree_summarize",
    )
    return QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name=f"kb_{collection_name}",
            description=description,
        ),
    )

tool_kb_manuels = make_kb_tool(
    "kb_manuels",
    "Recherche dans les manuels DCG/DSCG (comptabilité, fiscalité, droit, finance). "
    "18 132 documents. Utiliser pour les questions théoriques et normatives."
)

tool_kb_reglementation = make_kb_tool(
    "kb_reglementation",
    "Recherche dans les textes de loi : Girardin, LODEOM, dispositifs ultramarins. "
    "Utiliser pour les questions fiscales et réglementaires spécifiques Guyane/DOM."
)

tool_kb_conventions = make_kb_tool(
    "kb_conventions",
    "Recherche dans les conventions collectives Guyane (Transport, Agroalimentaire). "
    "Utiliser pour les questions de paie, grilles salariales, indemnités."
)

tool_kb_pcg = make_kb_tool(
    "kb_pcg_analytique",
    "Recherche dans le mapping des 1 412 comptes PCG avec catégories analytiques "
    "(SIG, CR, Bilan, BF, V/F). Utiliser pour identifier le rôle d'un compte."
)

# ── PostgreSQL HMA → SQL Tools ───────────────────────────────────────
pg_engine = create_engine(HMA_DB_URL)   # depuis Vaultwarden
sql_database = SQLDatabase(pg_engine, include_tables=[
    # Vues matérialisées (lecture seule)
    "mv_balance_generale",
    "mv_sig",
    "mv_compte_resultat",
    "mv_bilan",
    "mv_bilan_fonctionnel",
    "mv_resultat_differentiel",
    # Vues enrichies
    "v_sig_drilldown",
    "v_crd_drilldown",
    "v_grand_livre",
    "v_balance_auxiliaire",
    # Tables de référence
    "entite",
    "exercice",
    "pcg_analytique",
    # Données
    "fec_ecriture",
])

tool_sql_balance = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_balance_generale", "v_balance_auxiliaire", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_balance",
        description=(
            "Requête SQL sur la balance générale et balance auxiliaire. "
            "Soldes par compte, entité, exercice et mois. "
            "Colonnes : entite_id, exercice_id, pcg_numero, mois, debit, credit, solde."
        ),
    ),
)

tool_sql_sig = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_sig", "v_sig_drilldown", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_sig",
        description=(
            "Requête SQL sur les 9 Soldes Intermédiaires de Gestion + CAF. "
            "Soldes : Marge commerciale, Production, Valeur ajoutée, EBE, "
            "Résultat exploitation, RCAI, Résultat exceptionnel, Résultat exercice, CAF. "
            "Drilldown par compte disponible via v_sig_drilldown."
        ),
    ),
)

tool_sql_bilan = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_bilan", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_bilan",
        description=(
            "Requête SQL sur le bilan comptable. Actif/Passif structurés "
            "(brut, amortissements, net) par bilan_section et bilan_poste."
        ),
    ),
)

tool_sql_bilan_fonctionnel = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_bilan_fonctionnel", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_bilan_fonctionnel",
        description=(
            "Requête SQL sur le bilan fonctionnel. FRNG, BFR exploitation, "
            "BFR hors exploitation, Trésorerie nette."
        ),
    ),
)

tool_sql_cr = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_compte_resultat", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_compte_resultat",
        description=(
            "Requête SQL sur le compte de résultat structuré. "
            "Produits et charges par cr_rubrique."
        ),
    ),
)

tool_sql_crd = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["mv_resultat_differentiel", "v_crd_drilldown", "entite", "exercice"],
    ),
    metadata=ToolMetadata(
        name="sql_resultat_differentiel",
        description=(
            "Requête SQL sur le Compte de Résultat Différentiel. "
            "CA, charges variables, MCV, taux MCV, charges fixes, "
            "seuil de rentabilité, point mort en jours."
        ),
    ),
)

tool_sql_fec = QueryEngineTool(
    query_engine=NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["fec_ecriture", "v_grand_livre", "entite", "exercice", "pcg_analytique"],
    ),
    metadata=ToolMetadata(
        name="sql_ecritures_fec",
        description=(
            "Requête SQL sur les écritures comptables FEC et le grand livre. "
            "25 000+ écritures normalisées avec solde progressif. "
            "Colonnes : journal_code, ecriture_num, ecriture_date, compte_num, "
            "piece_ref, ecriture_lib, debit, credit, pcg_numero."
        ),
    ),
)
```

---

## Configuration mem0 — Mémoire agents

```python
from mem0 import Memory

# ── Config mem0 → Qdrant + OpenAI embeddings ────────────────────────
mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": "https://qdrant.hma.business",
            "api_key": QDRANT_API_KEY,
            "port": 443,
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": OPENAI_API_KEY,
        }
    },
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-sonnet-4-6",
            "api_key": ANTHROPIC_API_KEY,
            "max_tokens": 4096,
        }
    },
}

# ── Instances mémoire par agent ──────────────────────────────────────
# Chaque agent a sa propre collection Qdrant via user_id

mem0_memory = Memory.from_config(mem0_config)

# ── Fonctions mémoire pour les agents ────────────────────────────────

def memorize(agent_id: str, content: str, metadata: dict = None):
    """Stocker un output d'agent en mémoire long terme."""
    mem0_memory.add(
        content,
        user_id=agent_id,         # ex: "expert_comptable", "juriste"
        metadata=metadata or {},   # ex: {"entite": "ETPA", "domaine": "sig"}
    )

def recall(agent_id: str, query: str, limit: int = 5) -> list:
    """Retrouver les souvenirs pertinents d'un agent."""
    results = mem0_memory.search(
        query,
        user_id=agent_id,
        limit=limit,
    )
    return results.get("results", [])

# ── Outils CrewAI wrappant mem0 ─────────────────────────────────────
from crewai.tools import tool

@tool("memoire_expert_comptable")
def tool_mem0_expert_comptable(query: str) -> str:
    """Recherche dans la mémoire long terme de l'Expert-Comptable.
    Retrouve les analyses passées similaires (écritures, révisions, paie)."""
    memories = recall("expert_comptable", query)
    if not memories:
        return "Aucun souvenir pertinent trouvé."
    return "\n---\n".join(m["memory"] for m in memories)

@tool("memoire_juriste")
def tool_mem0_juriste(query: str) -> str:
    """Recherche dans la mémoire long terme du Juriste Senior.
    Retrouve les avis juridiques, montages et articles cités passés."""
    memories = recall("juriste", query)
    if not memories:
        return "Aucun souvenir pertinent trouvé."
    return "\n---\n".join(m["memory"] for m in memories)

@tool("memoire_analyste")
def tool_mem0_analyste(query: str) -> str:
    """Recherche dans la mémoire long terme de l'Analyste Financier.
    Retrouve les analyses SIG, ratios et simulations passées."""
    memories = recall("analyste_financier", query)
    if not memories:
        return "Aucun souvenir pertinent trouvé."
    return "\n---\n".join(m["memory"] for m in memories)

@tool("memoire_reviseur")
def tool_mem0_reviseur(query: str) -> str:
    """Recherche dans la mémoire long terme du Réviseur Qualité.
    Retrouve les patterns d'erreur et alertes détectés."""
    memories = recall("reviseur", query)
    if not memories:
        return "Aucun souvenir pertinent trouvé."
    return "\n---\n".join(m["memory"] for m in memories)
```

---

## Configuration Crew — Assemblage final

```python
# ── Crew HMAGENTS ─────────────────────────────────────────────────

hmagents_crew = Crew(
    agents=[
        expert_comptable,
        juriste,
        analyste_financier,
        reviseur,
    ],
    manager_agent=directeur_mission,   # Directeur = manager hierarchical
    process=Process.hierarchical,       # Le manager route et délègue
    planning=True,                      # CrewAI planifie les sous-tâches
    verbose=True,
    memory=False,                       # mem0 gère la mémoire, pas CrewAI
    respect_context_window=True,
    max_rpm=30,                         # Rate limit Anthropic
)

# ── Exécution ────────────────────────────────────────────────────────

def ask_hmagents(question: str, entite: str = None, exercice: str = None) -> str:
    """Point d'entrée principal — une question utilisateur."""

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
```

---

## Déploiement Docker

### Structure du service

```
hmagents/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── main.py              # FastAPI — point d'entrée HTTP
│   ├── config.py             # Chargement secrets Vaultwarden
│   ├── crew.py               # Configuration CrewAI (agents, crew)
│   ├── tools_rag.py          # LlamaIndex QueryEngineTools
│   ├── tools_sql.py          # LlamaIndex SQL Tools
│   ├── tools_memory.py       # mem0 memory tools
│   ├── tools_pennylane.py    # Custom tool API Pennylane
│   └── models.py             # Pydantic schemas (request/response)
└── tests/
    ├── test_tools.py
    └── test_crew.py
```

### docker-compose.yml

```yaml
services:
  hmagents:
    build: .
    container_name: hmagents
    restart: unless-stopped
    ports:
      - "8100:8000"
    environment:
      # Secrets injectés depuis Vaultwarden via Coolify
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_URL=https://qdrant.hma.business
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - HMA_DB_URL=${HMA_DB_URL}
      - PENNYLANE_TOKEN_HMA=${PENNYLANE_TOKEN_HMA}
      - PENNYLANE_TOKEN_STIVMAT=${PENNYLANE_TOKEN_STIVMAT}
      - PENNYLANE_TOKEN_STA=${PENNYLANE_TOKEN_STA}
      - PENNYLANE_TOKEN_ETPA=${PENNYLANE_TOKEN_ETPA}
    networks:
      - hma-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hmagents.rule=Host(`agents.hma.business`)"
      - "traefik.http.services.hmagents.loadbalancer.server.port=8000"

networks:
  hma-network:
    external: true
```

### requirements.txt

```
crewai[tools]>=0.108
llama-index-core>=0.12
llama-index-vector-stores-qdrant>=0.4
llama-index-embeddings-openai>=0.3
llama-index-llms-anthropic>=0.5
mem0ai>=0.1
fastapi>=0.115
uvicorn>=0.34
sqlalchemy>=2.0
psycopg2-binary>=2.9
qdrant-client>=1.13
pydantic>=2.10
requests>=2.32
```

### API FastAPI (main.py)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.crew import ask_hmagents

app = FastAPI(title="HMAGENTS", version="1.0.0")

class QuestionRequest(BaseModel):
    question: str
    entite: str | None = None          # HMA, STIVMAT, STA, ETPA
    exercice: str | None = None        # ex: "2025"

class QuestionResponse(BaseModel):
    reponse: str
    agent_traces: list[str] | None = None

@app.post("/ask", response_model=QuestionResponse)
async def ask(req: QuestionRequest):
    """Point d'entrée principal — question utilisateur."""
    try:
        result = ask_hmagents(
            question=req.question,
            entite=req.entite,
            exercice=req.exercice,
        )
        return QuestionResponse(reponse=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "HMAGENTS"}
```

---

## Intégration n8n

n8n déclenche HMAGENTS via HTTP Request :

```
[Chat Trigger / Webhook]
        ↓
[HTTP Request POST → https://agents.hma.business/ask]
  Body : { "question": "...", "entite": "ETPA", "exercice": "2025" }
        ↓
[Respond to Webhook / Chat Message]
  Body : {{ $json.reponse }}
```

n8n reste responsable de :
- **ETL Pennylane** (sync écritures → PostgreSQL HMA)
- **Cron** de déclenchement sync (toutes les 2h)
- **Chat UI** (trigger webhook → HMAGENTS → réponse)
- **Feedback** (écriture `agent_feedback` en PostgreSQL après notation)

---

## Collections Qdrant — Inventaire complet

### KB statiques (lecture seule par LlamaIndex)

| Collection | Contenu | Points | Géré par |
|---|---|---|---|
| `kb_manuels` | Manuels DCG/DSCG | 18 132 | Ingestion manuelle |
| `kb_reglementation` | LODEOM, Girardin, textes de loi | 11 | Ingestion manuelle |
| `kb_conventions` | CC Transport, CC Agroalimentaire | 6 | Ingestion manuelle |
| `kb_pcg_analytique` | 1 412 comptes PCG mappés | 1 372 | `generate-pcg-qdrant.py` |

### Mémoire agents (lecture/écriture par mem0)

| Collection | Agent | Contenu | Géré par |
|---|---|---|---|
| `agent_mem_expert_comptable` | Expert-Comptable | Écritures, révisions, paie | mem0 |
| `agent_mem_juriste` | Juriste Senior | Avis juridiques, articles cités | mem0 |
| `agent_mem_analyste` | Analyste Financier | Analyses SIG, simulations | mem0 |
| `agent_mem_reviseur` | Réviseur Qualité | Patterns d'erreur, alertes | mem0 |

---

## Tables PostgreSQL HMA — Mémoire court terme + feedback

### agent_session (court terme — partagé entre agents)

```sql
CREATE TABLE agent_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entite_id UUID REFERENCES entite(id),
    exercice_id UUID REFERENCES exercice(id),
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    closed_at TIMESTAMPTZ
);
```

### agent_feedback (procédurale — scoring + few-shot)

```sql
CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES agent_session(id),
    agent_profile TEXT NOT NULL CHECK (agent_profile IN (
        'directeur_mission', 'expert_comptable',
        'juriste', 'analyste_financier', 'reviseur'
    )),
    entite_id UUID REFERENCES entite(id),
    prompt_original TEXT NOT NULL,
    output_original TEXT NOT NULL,
    score SMALLINT CHECK (score BETWEEN 1 AND 5),
    correction TEXT,
    is_positive_example BOOLEAN GENERATED ALWAYS AS (score >= 4) STORED,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Mapping Requirements → Stack

| Requirement | Composant HMAGENTS |
|---|---|
| FR-001 (routage) | CrewAI `Process.hierarchical` + `manager_agent` |
| FR-002 (délégation parallèle) | CrewAI délégation native du manager |
| FR-003 (réviseur obligatoire) | CrewAI task flow : experts → réviseur → synthèse |
| FR-004 (score confiance) | Réviseur agent output parsing |
| FR-005 (sources citées) | LlamaIndex QueryEngine `response.source_nodes` |
| FR-006 (données comptables) | LlamaIndex SQL Tools + Pennylane API Tool |
| FR-007 (LODEOM) | LlamaIndex KB Tools (kb_reglementation, kb_conventions) |
| FR-008 (comptes PCG) | LlamaIndex KB Tool (kb_pcg_analytique) |
| FR-009 (KB juridique) | LlamaIndex KB Tools (kb_manuels, kb_reglementation) |
| FR-010 (distinction social) | CrewAI agent backstory + goal (routing par le manager) |
| FR-011 (SIG + CAF) | LlamaIndex SQL Tool (mv_sig) |
| FR-012 (simulations) | LlamaIndex SQL Tools + calcul dans le prompt |
| FR-013 (comparatif) | LlamaIndex SQL Tools (multi-entité) |
| FR-014 (recalcul) | LlamaIndex SQL Tools (requêtes indépendantes du Réviseur) |
| FR-015 (vérification KB) | LlamaIndex KB Tools (cross-check par le Réviseur) |
| FR-016 (contradictions) | CrewAI task output comparison par le Réviseur |
| FR-024 (mémoire LT) | **mem0** → Qdrant `agent_mem_*` |
| FR-025 (mémoire CT) | PostgreSQL HMA `agent_session` |
| FR-026 (mémoire procédurale) | PostgreSQL HMA `agent_feedback` |
