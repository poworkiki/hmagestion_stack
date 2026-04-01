# Agent IA HMA — Présentation du projet

## Contexte

HMA est un cabinet de gestion/expertise comptable basé en Guyane qui gère 4 structures : **HMA, STIVMAT, STA, ETPA** (commerce, BTP, services, industrie).

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
| kb_conventions | Conventions collectives Guyane (Commerce, BTP) | 6 |
| kb_modeles | Modèles de documents (à alimenter) | 0 |
| kb_jurisprudence | Jurisprudence (à alimenter) | 0 |
| kb_precedents_cabinet | Dossiers internes (à alimenter) | 0 |

**Exemples de questions :**
- "Quelles sont les conditions d'éligibilité au Girardin IS pour un investissement productif en Guyane ?"
- "Quel est le plafond d'exonération LODEOM régime renforcé pour 2025 ?"
- "Quelles sont les indemnités de déplacement prévues par la CC BTP Guyane ?"
- "Comment comptabiliser une subvention d'investissement selon le PCG ?"

### 2. Interroger les données comptables des 4 structures (API Pennylane)

Les 4 tokens API Pennylane sont connectés et fonctionnels :

| Structure | Activité | API |
|---|---|---|
| HMA | Gestion / Holding | Lecture seule |
| STIVMAT | Commerce | Lecture seule |
| STA | Services / BTP | Lecture seule |
| ETPA | Industrie / BTP | Lecture seule |

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
- "ETPA a un taux de sous-traitance de 35%. Est-ce cohérent avec la CC BTP Guyane ?"
- "Calcule les SIG de STIVMAT pour l'exercice 2025 et identifie les postes anormaux"
- "Quel dispositif fiscal LODEOM est applicable pour l'investissement matériel qu'ETPA prévoit ?"
- "Simule l'impact sur l'EBE de HMA si les charges de personnel augmentent de 5%"

---

## Architecture technique prévue

### Flux de données

```
Utilisateur (question)
       │
       ▼
   n8n Agent IA ──────────────────────────────────────────┐
       │                                                   │
       ├── Question métier/théorique ?                     │
       │   └── Qdrant (RAG)                                │
       │       ├── kb_manuels (18k chunks DCG/DSCG)       │
       │       ├── kb_reglementation (fiscal, social)      │
       │       ├── kb_conventions (CC Guyane)              │
       │       └── kb_pcg_analytique (mapping PCG)         │
       │                                                   │
       ├── Question sur les données d'une structure ?      │
       │   └── Pennylane API (lecture seule)                │
       │       ├── Trial balance                           │
       │       ├── Écritures comptables                    │
       │       ├── Factures                                │
       │       └── Tiers                                   │
       │                                                   │
       ├── Calcul / Analyse financière ?                   │
       │   └── Supabase (SQL)                              │
       │       ├── fec_ecriture (FEC centralisé)           │
       │       ├── pcg_analytique (mapping)                │
       │       ├── budget_ligne (prévisionnel)             │
       │       └── Vues matérialisées (SIG, Bilan, BF...) │
       │                                                   │
       ▼                                                   │
   Réponse enrichie ◄─────────────────────────────────────┘
```

### Composants

| Composant | Rôle | Déjà déployé |
|---|---|---|
| n8n | Orchestrateur agent IA + workflows sync | Oui |
| Qdrant | Base vectorielle RAG (KB comptable) | Oui |
| Supabase | PostgreSQL + Auth (données FEC, mapping, budget) | Oui |
| Pennylane API | Source des données comptables (4 structures) | Oui (tokens OK) |
| OpenAI API | Embeddings (text-embedding-3-small) + LLM | Oui (clé OK) |
| Metabase | Dashboards visuels (SIG, Bilan, Budget vs Réalisé) | Oui |
| Appsmith | Interface de saisie (budget, paramétrage) | Oui |
| Vaultwarden | Stockage sécurisé des secrets | Oui |

### Nouvelle collection Qdrant : kb_pcg_analytique

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
| `profil_nature_charge` | Override V/F par profil sectoriel (commerce, BTP, services) |
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
- Budget saisonnalisé (proratisation BTP)
- 20+ ratios financiers (liquidité, solvabilité, rentabilité, rotation, BTP)
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

### Agent IA (chat n8n)
- Questions métier → RAG Qdrant
- Questions données → API Pennylane / SQL Supabase
- Analyse croisée → KB + données

---

## Livrables attendus

1. **Schéma Supabase** : 6 tables + 3 auxiliaires + 7 vues matérialisées + 1 vue contrôle
2. **Mapping PCG analytique** : 1 412 comptes catégorisés (SIG, CR, Bilan, BF, V/F)
3. **Collection Qdrant** : `kb_pcg_analytique` avec embeddings
4. **Workflow n8n** : sync Pennylane → Supabase (4 structures, pattern staging)
5. **Workflow n8n** : agent IA (Qdrant RAG + Pennylane API + Supabase SQL)
6. **Dashboards Metabase** : SIG, CR, Bilan, BF, Budget vs Réalisé, Ratios
7. **Interface Appsmith** : saisie budget + paramétrage

---

*Document préparé le 1er avril 2026 — HMA Stack*
