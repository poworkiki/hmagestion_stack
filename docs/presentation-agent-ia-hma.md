# Agent IA HMA — Présentation du projet

## Contexte

HMA est un cabinet de gestion/expertise comptable basé en Guyane qui gère 4 structures : **HMA, STIVMAT, STA, ETPA**.

Le stack technique est entièrement self-hosted sur un VPS Hostinger piloté par Coolify :
- **Pennylane** : logiciel comptable (API connectée aux 4 structures)
- **n8n** : orchestrateur de workflows (n8n.hma.business)
- **Supabase** : base de données PostgreSQL + Auth (self-hosted)
- **Metabase** : dashboards et reporting (metabase.hma.business)
- **Appsmith** : interface low-code (appsmith.hma.business)
- **Qdrant** : base vectorielle pour le RAG (KB interne)
- **Vaultwarden** : gestionnaire de secrets

---

## Le besoin

Construire un **agent IA comptable et financier** capable de :

### 1. Répondre à des questions métier (RAG sur le KB Qdrant)

Le KB Qdrant contient déjà :

| Collection | Contenu | Points |
|---|---|---|
| kb_manuels | Manuels DCG/DSCG (droit, fiscal, social, compta, finance) | 18 132 |
| kb_reglementation | Textes de loi — Girardin, LODEOM, dispositifs ultramarins | 11 |
| kb_conventions | Conventions collectives Guyane (Transport, Agroalimentaire) | 6 |
| kb_modeles | Modèles de documents (à alimenter) | 0 |
| kb_jurisprudence | Jurisprudence (à alimenter) | 0 |
| kb_precedents_cabinet | Dossiers internes (à alimenter) | 0 |

**Exemples de questions :**
- "Quelles sont les conditions d'éligibilité au Girardin IS pour un investissement productif en Guyane ?"
- "Quel est le plafond d'exonération LODEOM régime renforcé pour 2025 ?"
- "Quelles sont les indemnités de déplacement prévues par la CC Transport Guyane ?"
- "Comment comptabiliser une subvention d'investissement selon le PCG ?"

### 2. Interroger les données comptables des 4 structures (API Pennylane)

Les 4 tokens API Pennylane sont connectés et fonctionnels :

| Structure | Activité | API |
|---|---|---|
| HMA | Holding | Lecture seule |
| STIVMAT | Transport de personnes | Lecture seule |
| STA | Transport de personnes | Lecture seule |
| ETPA | Transformation de produits agricoles | Lecture seule |

**Endpoints disponibles :**
- `/trial_balance` : balance des comptes par période
- `/ledger_entries` : écritures comptables (reconstitution FEC)
- `/ledger_accounts` : plan comptable (1 412 comptes PCG)
- `/supplier_invoices` / `/customer_invoices` : factures
- `/suppliers` / `/customers` : tiers
- `/journals` : journaux comptables
- `/categories` : catégories analytiques (lecture/écriture)

**Exemples de questions :**
- "Quel est le chiffre d'affaires de STIVMAT au T3 2025 ?"
- "Donne-moi la balance fournisseurs d'ETPA au 31/12/2025"
- "Compare les charges de personnel des 4 structures"
- "Quelles sont les factures impayées de STA ?"

### 3. Analyser et croiser (KB + données)

**Exemples de questions avancées :**
- "ETPA a un taux de matières premières de 45%. Est-ce cohérent pour une entreprise de transformation agricole ?"
- "Calcule les SIG de STIVMAT pour l'exercice 2025 et identifie les postes anormaux"
- "Quel dispositif fiscal LODEOM est applicable pour l'investissement matériel qu'ETPA prévoit ?"
- "Simule l'impact sur l'EBE de HMA si les charges de personnel augmentent de 5%"

---

## Architecture technique — Système multi-agents

### Vue d'ensemble

Le système repose sur **5 agents spécialisés** organisés en pipeline : le Directeur de Mission route la question vers les experts, les experts produisent, le Réviseur contrôle avant que la réponse ne parte à l'utilisateur.

```
Utilisateur (chat)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DIRECTEUR DE MISSION                         │
│            Route, délègue, arbitre, synthétise                   │
│     Identifie : intent + structure(s) + expert(s) requis        │
└──────────┬──────────────┬──────────────┬────────────────────────┘
           │              │              │
           ▼              ▼              ▼
┌────────────────┐ ┌────────────┐ ┌──────────────────┐
│ EXPERT-        │ │ JURISTE    │ │ ANALYSTE         │
│ COMPTABLE      │ │ SENIOR     │ │ FINANCIER        │
│ SENIOR         │ │            │ │ SENIOR           │
│                │ │ Droit      │ │                  │
│ Chiffres       │ │ fiscal     │ │ Stratégie        │
│ + Social       │ │ sociétés   │ │ simulations      │
│                │ │ contrats   │ │ ratios           │
│                │ │ travail    │ │                  │
└───────┬────────┘ └─────┬──────┘ └────────┬─────────┘
        │                │                  │
        └────────────────┼──────────────────┘
                         ▼
              ┌─────────────────────┐
              │  RÉVISEUR QUALITÉ   │
              │  Vérifie, croise,   │
              │  score confiance    │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ DIRECTEUR DE MISSION│  ← synthèse finale
              └──────────┬──────────┘
                         ▼
                    Utilisateur
```

### Les 5 agents — Profils et périmètres

#### 1. Directeur de Mission (Orchestrateur)

Ne produit jamais de contenu métier. Il comprend la question, identifie les structures concernées, choisit les experts, et synthétise les réponses contrôlées.

| Capacité | Détail |
|---|---|
| Classification d'intent | Comptable / Fiscal / Financier / Mixte / Hors dossier |
| Résolution de structure | "STIVMAT" / "toutes" / implicite (contexte session) |
| Délégation multi-expert | Question mixte → plusieurs experts en parallèle |
| Arbitrage | Si deux experts divergent, tranche avec le contexte |
| Synthèse finale | Fusionne les réponses après contrôle du Réviseur |

#### 2. Expert-Comptable Senior (Chiffres + Social)

| Domaine | Sources | Exemples |
|---|---|---|
| PCG / écritures / FEC | Supabase `fec_ecriture`, Pennylane `/ledger_entries` | "Écritures du journal AC de mars" |
| Révision des comptes | Supabase vues + Pennylane balance | "Balance fournisseurs d'ETPA au 31/12" |
| Paie & charges sociales | Supabase comptes 64*, Qdrant `kb_conventions` | "Coût chargé chauffeur CC Transport" |
| LODEOM social | Qdrant `kb_reglementation` | "Exonération cotisations patronales régime renforcé" |
| Conventions collectives | Qdrant `kb_conventions` | "Grille salariale CC Transport Guyane" |
| Normes ANC/PCG | Qdrant `kb_manuels` | "Durée amortissement véhicule utilitaire" |
| Consolidation groupe | Supabase multi-entité + flag intra-groupe | "Élimination flux intra-groupe HMA/STIVMAT" |

#### 3. Juriste Senior (Droit pur)

| Domaine | Sources | Exemples |
|---|---|---|
| Droit fiscal (IS, TVA, CET) | Qdrant `kb_manuels` + `kb_reglementation` | "Taux IS PME applicable pour STA" |
| LODEOM fiscal / Girardin / ZFA | Qdrant `kb_reglementation` | "Éligibilité Girardin IS investissement productif Guyane" |
| Droit des sociétés | Qdrant `kb_manuels` | "PV AG approbation comptes — mentions obligatoires" |
| Droit des contrats | Qdrant `kb_manuels` | "Contrat d'affrètement transport : obligations réglementaires" |
| Droit du travail (contentieux) | Qdrant `kb_manuels` | "Procédure licenciement économique transport de personnes" |
| Structuration / transmission | Qdrant `kb_reglementation` | "Intégration fiscale HMA holding — conditions" |

Répartition du social entre Expert-Comptable et Juriste :
- **Social chiffré (quotidien)** → Expert-Comptable : paie, cotisations, coût chargé, DSN
- **Social juridique (ponctuel)** → Juriste : licenciement, contentieux prud'homal, rupture

#### 4. Analyste Financier Senior (Stratégie)

| Domaine | Sources | Exemples |
|---|---|---|
| SIG (9 soldes + CAF) | Supabase `mv_sig` | "SIG STIVMAT 2025, postes anormaux" |
| Ratios financiers | Supabase vues + calculs | "Liquidité et solvabilité des 4 structures" |
| Bilan fonctionnel | Supabase `mv_bilan_fonctionnel` | "FRNG, BFR, TN d'ETPA — évolution 3 ans" |
| Seuil de rentabilité | Supabase `mv_resultat_differentiel` | "Point mort de STA en mois" |
| Budget vs Réalisé | Supabase `mv_budget_vs_realise` | "Écarts budget STIVMAT, alertes dépassement" |
| Simulations | Supabase SQL + calculs | "Impact +5% charges personnel sur EBE HMA" |
| Comparatif groupe | Supabase multi-entité | "Rentabilité comparée des 4 structures" |

#### 5. Réviseur Qualité (Contrôle)

Ne produit jamais de contenu métier. Intervient **après** les experts, **avant** la synthèse finale. C'est la porte de qualité du système.

| Contrôle | Ce qu'il fait | Exemple |
|---|---|---|
| Vérification calculs | Refait le calcul indépendamment via Supabase SQL | EC dit "5 950€ chargé" → recalcule brut + charges - exo LODEOM |
| Contrôle des sources | Vérifie que les articles/normes cités existent dans Qdrant | Juriste cite "art. 244 quater W CGI" → cross-check KB |
| Détection contradictions | Compare les outputs de plusieurs experts | EC dit X, Juriste dit Y → alerte le Directeur |
| Cohérence de la réponse | Vérifie que la réponse correspond à la question posée | Question sur ETPA → la réponse parle bien d'ETPA, pas de STA |
| Score de confiance | Attribue un niveau : haute / moyenne / à vérifier | Calcul vérifié + sources OK → confiance haute |

Output enrichi par le Réviseur :
```
"Le coût chargé est de 4 850€/mois.

 📊 Confiance : haute
 ✅ Brut CC Transport vérifié (3 200€)
 ✅ Exo LODEOM vérifiée (barème 2025)
 ⚠️  Le montant inclut les primes de conduite et indemnités repas — détail ci-dessous
 📎 Sources : CC Transport Guyane, Code SS art. L752-3-2"
```

### Couches de chaque agent

Chaque agent est structuré en 5 couches :

```
┌─────────────────────────────────────┐
│           ORCHESTRATEUR             │  ← logique de décision interne
├─────────────────────────────────────┤
│              SKILLS                 │  ← compétences métier spécifiques
├─────────────────────────────────────┤
│               TOOLS                 │  ← accès aux sources de données
├─────────────────────────────────────┤
│              MÉMOIRE                │  ← 3 niveaux (voir section Mémoire)
├─────────────────────────────────────┤
│               LLM                   │  ← Claude (raisonnement)
└─────────────────────────────────────┘
```

| Agent | Orchestrateur | Skills | Tools |
|---|---|---|---|
| Directeur de Mission | Routage, arbitrage | Classification, synthèse, reformulation | Appel des 4 autres agents |
| Expert-Comptable | Plan de révision | Comptabiliser, réviser, paie/charges, lettrer | Pennylane API, Supabase SQL, Qdrant KB |
| Juriste Senior | Raisonnement juridique | Qualifier, argumenter, rédiger, citer | Qdrant KB (manuels, réglementation, conventions) |
| Analyste Financier | Plan d'analyse | Calculer SIG/ratios, simuler, projeter | Supabase SQL (vues mat.), Pennylane API, Qdrant KB |
| Réviseur Qualité | Pipeline de contrôle | Vérifier calculs, cross-check sources, scorer | Supabase SQL (recompute), Qdrant KB, Pennylane API |

### Mémoire structurée — 3 niveaux

Chaque agent dispose de trois niveaux de mémoire complémentaires :

#### Mémoire long terme — sémantique (Qdrant)

Ce que l'agent a appris au fil des dossiers. Les outputs passés sont indexés et retrouvés par similarité. Quand un agent traite un dossier, il retrouve automatiquement ce qu'il a produit sur des dossiers similaires — même structure, même secteur, même problématique.

| Collection Qdrant | Agent | Contenu indexé |
|---|---|---|
| `agent_mem_expert_comptable` | Expert-Comptable | Écritures traitées, résolutions de comptes, révisions |
| `agent_mem_juriste` | Juriste Senior | Avis rendus, montages analysés, articles cités |
| `agent_mem_analyste` | Analyste Financier | Analyses SIG/ratios, simulations, recommandations |
| `agent_mem_reviseur` | Réviseur Qualité | Erreurs détectées, patterns d'erreur, seuils d'alerte |

Le Directeur de Mission n'a pas de collection propre — il utilise les patterns de routage stockés en mémoire procédurale.

#### Mémoire court terme — session (Supabase + n8n)

Ce que l'agent sait sur la mission en cours. Partagée entre les 5 agents d'une même session pour éviter de répéter les informations à chaque délégation.

```sql
CREATE TABLE agent_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users,
    entite_id UUID REFERENCES entite(id),       -- NULL si hors dossier
    exercice_id UUID REFERENCES exercice(id),    -- NULL si hors dossier
    context JSONB DEFAULT '{}',                  -- décisions, hypothèses, données collectées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    closed_at TIMESTAMPTZ                        -- NULL = session active
);
```

Contenu typique du `context` JSONB :
```json
{
  "entite_active": "ETPA",
  "secteur": "Transformation de produits agricoles",
  "exercice": "2025",
  "donnees_collectees": { "ca": 1850000, "ebe": 222000 },
  "decisions": ["embauche 3 opérateurs de production validée"],
  "agents_sollicites": ["expert_comptable", "juriste"]
}
```

#### Mémoire procédurale — feedback (Supabase)

Ce que l'agent a appris de ses erreurs. Chaque output est scoré. Les bonnes réponses deviennent des exemples injectés dans les futurs prompts (few-shot). Les corrections manuelles deviennent des contre-exemples. L'agent s'améliore progressivement sans être réentraîné.

```sql
CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES agent_session(id),
    agent_profile TEXT NOT NULL CHECK (agent_profile IN (
        'directeur_mission',
        'expert_comptable',
        'juriste',
        'analyste_financier',
        'reviseur'
    )),
    entite_id UUID REFERENCES entite(id),
    prompt_original TEXT NOT NULL,
    output_original TEXT NOT NULL,
    score SMALLINT CHECK (score BETWEEN 1 AND 5),
    correction TEXT,                             -- NULL si score >= 4
    is_positive_example BOOLEAN GENERATED ALWAYS AS (score >= 4) STORED,
    tags TEXT[] DEFAULT '{}',                    -- ex: {'sig', 'etpa', 'transport', 'lodeom'}
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_feedback_profile_positive
    ON agent_feedback(agent_profile, is_positive_example)
    WHERE is_positive_example = true;
CREATE INDEX idx_feedback_tags ON agent_feedback USING GIN(tags);
```

### Flux de collaboration — Exemple concret

```
Utilisateur : "ETPA veut embaucher 3 opérateurs de production. Quel impact global ?"

DIRECTEUR DE MISSION
├── Intent : question mixte (social + fiscal + financier)
├── Structure : ETPA (Transformation de produits agricoles)
├── Délègue en parallèle → 3 experts

EXPERT-COMPTABLE SENIOR
├── CC Agroalimentaire → brut 2 100€
├── Charges patronales 42% → 882€
├── Exo LODEOM compétitivité renforcée → -650€/mois
├── Coût chargé : 2 332€ + primes (panier + insalubrité) = 2 700€
├── × 3 = 8 100€/mois → +97k€/an masse salariale
└── Comptes impactés : 641, 645, 431, 437

JURISTE SENIOR
├── CDD ou CDI → période d'essai CC Agroalimentaire = 1 mois
├── Obligations : visite médicale, formation hygiène HACCP
├── Fiscal : +97k€ charges déductibles → économie IS ~24 250€
└── TVA : pas d'impact (charges de personnel hors champ)

ANALYSTE FINANCIER SENIOR
├── EBE : passe de 12% à 9.5% du CA
├── Seuil de rentabilité : repoussé de 1 mois
├── BFR : +25k€ (décalage paie)
└── Recommandation : embauche phasée (2 puis 1 à M+3)

RÉVISEUR QUALITÉ
├── ✅ Brut CC Agroalimentaire vérifié (barème 2025)
├── ✅ Exo LODEOM vérifiée (art. L752-3-2)
├── ✅ Calcul IS cohérent (25% × 97k)
├── ⚠️  EBE : recalcul donne 9.3% (écart 0.2 pts, arrondi IS)
├── ✅ Recommandation phasage cohérente avec trésorerie
└── 📊 Confiance globale : haute

DIRECTEUR DE MISSION → synthèse finale enrichie → Utilisateur
```

### Composants techniques

| Composant | Rôle | Déjà déployé |
|---|---|---|
| **HMAGENTS** | Système multi-agents IA (CrewAI + LlamaIndex + mem0 + Claude) | 🚧 En cours |
| n8n | ETL Pennylane + trigger HMAGENTS + workflows sync | Oui |
| Qdrant | Base vectorielle RAG (KB comptable + mémoire agents) | Oui |
| PostgreSQL HMA | Base standalone (FEC, mapping, vues matérialisées) | Oui |
| Pennylane API | Source des données comptables (4 structures) | Oui (tokens OK) |
| OpenAI API | Embeddings (text-embedding-3-small) | Oui (clé OK) |
| Claude (Anthropic) | LLM raisonnement agents HMAGENTS | Oui (clé OK) |
| Superset | Dashboards visuels (SIG, Bilan, CRD, Grand Livre) | Oui |
| Appsmith | Interface de saisie (budget, paramétrage) | Oui |
| Vaultwarden | Stockage sécurisé des secrets | Oui |

### Chantier A — Socle données (terminé)

- **25 779 écritures FEC** synchronisées (HMA: 830, STIVMAT: 23 536, STA: 126, ETPA: 1 287)
- **1 412 comptes PCG** mappés (SIG, CR, Bilan, BF, V/F) dans PostgreSQL + Qdrant
- **6 vues** opérationnelles : balance, bilan, bilan fonctionnel, CR, résultat différentiel, SIG
- **Refresh** : 0.12s (objectif < 60s)
- **Sync Pennylane** : toutes les 2h via n8n (cron) + sync incrémental + anti-doublons MD5

### Collection Qdrant : kb_pcg_analytique

Mapping des 1 412 comptes PCG avec catégories analytiques pour le RAG :

```json
{
  "number": "607",
  "label": "Achats de marchandises",
  "contenu": "607 - Achats de marchandises. SIG: entre dans la Marge commerciale (soustraction). CR: Charges d'exploitation > Achats > Marchandises. Bilan: n/a. Nature: variable. Résultat différentiel: Coût variable d'achat.",
  "sig_solde": "Marge commerciale",
  "cr_rubrique": "Charges d'exploitation",
  "bilan_poste": null,
  "nature_defaut": "variable"
}
```

Permet à l'agent de répondre : "Le compte 607 entre dans la marge commerciale du SIG. C'est une charge variable par défaut."

---

## Modèle de données Supabase

### Tables principales (6)

| Table | Description | Volume estimé |
|---|---|---|
| `entite` | Les 4 structures + futures (parent/enfant, activité, profil) | ~10 lignes |
| `exercice` | Exercices comptables par entité | ~20 lignes |
| `fec_import` | Traçabilité des imports (hash anti-doublons) | ~50 lignes |
| `fec_ecriture` | Écritures FEC normalisées (18 colonnes + champs calculés) | ~200k lignes |
| `pcg_analytique` | Plan comptable + mapping (SIG, CR, Bilan, BF, V/F) | 1 412 lignes |
| `budget_ligne` | Budget par ligne ou catégorie, en montant ou % | ~2k lignes |

### Tables auxiliaires

| Table | Description |
|---|---|
| `compte_resolution` | Résolution préfixe FEC → numéro PCG (ex: "411CLIENT001" → "411") |
| `profil_nature_charge` | Override V/F par profil sectoriel (transport, agroalimentaire, holding) |
| `entite_override_charge` | Override V/F par entité spécifique |

### Vues matérialisées (7)

| Vue | Calcul |
|---|---|
| `mv_balance_generale` | Soldes par compte, entité, mois |
| `mv_compte_resultat` | CR structuré (produits/charges par rubrique) |
| `mv_sig` | 9 soldes intermédiaires de gestion + CAF |
| `mv_bilan` | Actif / Passif (brut, amort, net) |
| `mv_bilan_fonctionnel` | FRNG, BFR exploitation/hors exploitation, TN |
| `mv_resultat_differentiel` | MCV, taux MCV, seuil de rentabilité, charges V/F |
| `mv_budget_vs_realise` | Écarts montant + % réalisation + % CA |

### Vue de contrôle

| Vue | Vérification |
|---|---|
| `v_controles_coherence` | Équilibre D=C, clôture N-1 = ouverture N, doublons |

---

## Points techniques validés par les experts

### Expert-comptable
- SIG : 9 soldes + CAF (flux, pas un SIG stricto sensu)
- Distinction 6037 (marge commerciale) vs 6031/6032 (valeur ajoutée) vs 713 (production)
- 791 transferts de charges → Résultat d'exploitation, pas VA
- Bilan fonctionnel en valeurs brutes (amort/dépréc → ressources stables)
- Gestion des à-nouveaux (filtre pour CR, inclus pour bilan)
- Budget saisonnalisé (proratisation transport / saisons agricoles)
- 20+ ratios financiers (liquidité, solvabilité, rentabilité, rotation, sectoriels)
- Exercice comptable ≠ année civile (exercices décalés possibles)

### Architecte données
- Vues matérialisées avec REFRESH CONCURRENTLY (performance Metabase)
- Table `compte_resolution` avec fonction `resolve_compte()` par préfixe décroissant
- Contrainte UNIQUE par hash MD5 de la ligne (gère les ventilations)
- Tokens API dans Vaultwarden uniquement (pas en base)
- Pattern staging → merge → refresh pour la sync n8n
- RLS Supabase pour isolation multi-entité
- Backup chiffré GPG + off-site, rétention 90 jours
- Scalable jusqu'à 20+ entités sans partitionnement

---

## Consolidation groupe

Niveau 1 (suffisant pour HMA) : **agrégation + élimination intra-groupe par flag**
- Activable/désactivable par toggle dans les dashboards
- Détection automatique des flux intra-groupe via `comp_aux_num`
- Contrôle de réciprocité des comptes courants (451/455)
- Pas de consolidation légale IFRS (hors périmètre)
- Architecture prévue pour accueillir de nouvelles sociétés (ajout d'une ligne dans `entite`)

---

## Interfaces utilisateur

### Metabase (dashboards)
- SIG mensuel par entité (sparklines, comparatif N/N-1)
- Compte de résultat structuré
- Bilan comptable et bilan fonctionnel
- Résultat différentiel + seuil de rentabilité
- Budget vs Réalisé (écarts, % réalisation, alertes)
- Ratios financiers (jauges, code couleur seuils)
- Synthèse cabinet (4 entités en colonnes)
- Consolidation groupe (toggle on/off)

### Appsmith (saisie)
- Formulaire de saisie budget (par compte ou catégorie, montant ou %)
- Paramétrage des entités et profils V/F
- Override nature charges par entité

### Agent IA (chat n8n — système multi-agents)
- Directeur de Mission → comprend et route la question
- Expert-Comptable Senior → chiffres, écritures, paie, social
- Juriste Senior → fiscal, sociétés, contrats, droit du travail
- Analyste Financier Senior → SIG, ratios, simulations, recommandations
- Réviseur Qualité → vérifie calculs, sources, cohérence avant réponse

---

## Livrables attendus

1. **Schéma Supabase** : 6 tables + 3 auxiliaires + 7 vues matérialisées + 1 vue contrôle + 2 tables mémoire agents (`agent_session`, `agent_feedback`)
2. **Mapping PCG analytique** : 1 412 comptes catégorisés (SIG, CR, Bilan, BF, V/F)
3. **Collections Qdrant** : `kb_pcg_analytique` + 4 collections mémoire agents (`agent_mem_expert_comptable`, `agent_mem_juriste`, `agent_mem_analyste`, `agent_mem_reviseur`)
4. **Workflow n8n** : sync Pennylane → Supabase (4 structures, pattern staging)
5. **Workflow n8n** : système multi-agents (5 agents : Directeur de Mission, Expert-Comptable, Juriste, Analyste Financier, Réviseur Qualité)
6. **Dashboards Metabase** : SIG, CR, Bilan, BF, Budget vs Réalisé, Ratios
7. **Interface Appsmith** : saisie budget + paramétrage + interface feedback agents (scoring 1-5)

---

*Document préparé le 1er avril 2026 — HMA Stack*
