# Data Model: Chantier A — Socle de données financières

**Branch**: `001-agent-ia-comptable` | **Date**: 2026-04-02

## Vue d'ensemble

```
entite (4 structures)
  │
  ├──< exercice (exercices comptables)
  │       │
  │       ├──< fec_import (traçabilité imports)
  │       │       │
  │       │       └──< fec_ecriture (écritures FEC normalisées)
  │       │               │
  │       │               └──> pcg_analytique (résolu via resolve_compte())
  │       │
  │       └──< budget_ligne (chantier B/C — hors périmètre)
  │
  └──< entite_override_charge (chantier B/C — hors périmètre)

pcg_analytique (1 412 comptes PCG — table de référence autonome)
  │
  └──< compte_resolution (résolution préfixe → PCG)
```

---

## Tables de référence

### entite

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| code | TEXT | UNIQUE, NOT NULL | Code court : HMA, STIVMAT, STA, ETPA |
| nom | TEXT | NOT NULL | Nom complet |
| activite | TEXT | NOT NULL | Transport de personnes, Transformation agricole, Holding |
| siren | TEXT | | Numéro SIREN |
| parent_id | UUID | FK → entite(id) | HMA = parent des 3 autres |
| profil | TEXT | NOT NULL, DEFAULT 'general' | Profil sectoriel (transport, agroalimentaire, holding) |
| actif | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### exercice

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| entite_id | UUID | FK → entite(id), NOT NULL | |
| label | TEXT | NOT NULL | Ex: "2025", "2024-2025" |
| date_debut | DATE | NOT NULL | |
| date_fin | DATE | NOT NULL | |
| cloture | BOOLEAN | DEFAULT false | Exercice clôturé ou non |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| UNIQUE | | (entite_id, date_debut) | Un seul exercice par entité et date |

### pcg_analytique

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| numero | TEXT | UNIQUE, NOT NULL | Numéro PCG (ex: "607", "411") |
| libelle | TEXT | NOT NULL | Libellé du compte |
| classe | SMALLINT | NOT NULL | Classe 1-8 |
| sig_solde | TEXT | | Solde SIG associé (Marge commerciale, VA, EBE...) |
| sig_signe | SMALLINT | | +1 (addition) ou -1 (soustraction) dans le SIG |
| cr_rubrique | TEXT | | Rubrique CR (Produits d'exploitation, Charges financières...) |
| cr_signe | SMALLINT | | +1 (produit) ou -1 (charge) |
| bilan_poste | TEXT | | Poste bilan (Immobilisations corporelles, Dettes fournisseurs...) |
| bilan_section | TEXT | | actif_immobilise, actif_circulant, passif_capitaux, passif_dettes |
| bf_categorie | TEXT | | Catégorie bilan fonctionnel (emplois_stables, bfr_exploit...) |
| nature_defaut | TEXT | DEFAULT 'fixe' | Variable ou fixe (pour résultat différentiel) |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### compte_resolution

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| prefixe | TEXT | NOT NULL | Préfixe FEC (ex: "411", "401", "512") |
| pcg_numero | TEXT | FK → pcg_analytique(numero), NOT NULL | Numéro PCG cible |
| priorite | SMALLINT | DEFAULT 0 | Ordre de priorité si plusieurs matchs |
| UNIQUE | | (prefixe) | Un seul mapping par préfixe |

---

## Tables FEC

### _staging_fec (table temporaire)

Même structure que `fec_ecriture`, sans contraintes d'intégrité (pas de FK, pas de UNIQUE sur hash_md5). **Cycle de vie** : TRUNCATE au début de chaque run de synchronisation, INSERT batch depuis Pennylane, puis MERGE vers `fec_ecriture`. N'est jamais lue en dehors du workflow n8n.

### fec_import

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| entite_id | UUID | FK → entite(id), NOT NULL | |
| exercice_id | UUID | FK → exercice(id), NOT NULL | |
| source | TEXT | DEFAULT 'pennylane' | Source de l'import |
| date_import | TIMESTAMPTZ | DEFAULT now() | |
| nb_lignes_brut | INTEGER | | Lignes récupérées depuis la source |
| nb_lignes_inserees | INTEGER | | Lignes effectivement insérées (hors doublons) |
| duree_secondes | NUMERIC | | Durée de l'import |
| statut | TEXT | DEFAULT 'en_cours' | en_cours, termine, erreur |
| erreur | TEXT | | Message d'erreur si échec |

### fec_ecriture

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| entite_id | UUID | FK → entite(id), NOT NULL | |
| exercice_id | UUID | FK → exercice(id), NOT NULL | |
| fec_import_id | UUID | FK → fec_import(id) | Import source |
| journal_code | TEXT | NOT NULL | JournalCode FEC |
| journal_lib | TEXT | | JournalLib FEC |
| ecriture_num | TEXT | NOT NULL | EcritureNum FEC |
| ecriture_date | DATE | NOT NULL | EcritureDate FEC |
| compte_num | TEXT | NOT NULL | CompteNum FEC (auxiliaire possible) |
| compte_lib | TEXT | | CompteLib FEC |
| comp_aux_num | TEXT | | CompAuxNum FEC |
| comp_aux_lib | TEXT | | CompAuxLib FEC |
| piece_ref | TEXT | | PieceRef FEC |
| piece_date | DATE | | PieceDate FEC |
| ecriture_lib | TEXT | | EcritureLib FEC |
| debit | NUMERIC(15,2) | DEFAULT 0 | |
| credit | NUMERIC(15,2) | DEFAULT 0 | |
| ecriture_let | TEXT | | Lettrage |
| date_let | DATE | | Date de lettrage |
| valid_date | DATE | | Date de validation |
| montant_devise | NUMERIC(15,2) | | Montant en devise |
| idevise | TEXT | | Code devise ISO |
| pcg_numero | TEXT | | Numéro PCG résolu (via resolve_compte) |
| hash_md5 | TEXT | UNIQUE, NOT NULL | Hash anti-doublons (voir formule ci-dessous) |

**Formule hash_md5** :
```sql
MD5(entite_id::text || journal_code || ecriture_num || ecriture_date::text || compte_num || debit::text || credit::text)
```
Champs choisis : identifient de manière unique une ligne d'écriture pour une entité donnée. Le `entite_id` est inclus car le même `ecriture_num` peut exister dans deux structures différentes.
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**Index** :
- `idx_fec_entite_exercice` ON (entite_id, exercice_id)
- `idx_fec_compte` ON (compte_num)
- `idx_fec_pcg` ON (pcg_numero)
- `idx_fec_date` ON (ecriture_date)
- `idx_fec_hash` ON (hash_md5) — UNIQUE

---

## Fonction resolve_compte()

```sql
-- Résout un numéro de compte FEC vers le numéro PCG racine
-- Ex: "411CLIENT001" → "411", "60110001" → "6011" → "601"
CREATE OR REPLACE FUNCTION resolve_compte(p_compte_num TEXT)
RETURNS TEXT AS $$
DECLARE
    v_prefix TEXT := p_compte_num;
    v_result TEXT;
BEGIN
    WHILE length(v_prefix) >= 3 LOOP
        SELECT numero INTO v_result
        FROM pcg_analytique
        WHERE numero = v_prefix;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;

        -- Vérifier la table de résolution explicite
        SELECT pcg_numero INTO v_result
        FROM compte_resolution
        WHERE prefixe = v_prefix;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;

        v_prefix := left(v_prefix, length(v_prefix) - 1);
    END LOOP;

    RETURN left(p_compte_num, 3); -- Fallback sur la classe
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

---

## Vues matérialisées

### mv_balance_generale

Soldes par compte, entité, exercice et mois.

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture.entite_id |
| exercice_id | fec_ecriture.exercice_id |
| pcg_numero | fec_ecriture.pcg_numero |
| mois | date_trunc('month', ecriture_date) |
| total_debit | SUM(debit) |
| total_credit | SUM(credit) |
| solde | SUM(debit) - SUM(credit) |

**Filtre à-nouveaux (classes 6-7)** : Exclut les écritures dont `journal_code IN ('AN', 'RAN')` (journaux d'à-nouveaux). Les écritures OD normales sont conservées — seuls les journaux spécifiquement dédiés aux à-nouveaux sont filtrés.

### mv_bilan

Actif et Passif structurés (brut, amortissements, net).

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture |
| exercice_id | fec_ecriture |
| bilan_section | pcg_analytique.bilan_section |
| bilan_poste | pcg_analytique.bilan_poste |
| montant_brut | SUM(solde) pour comptes principaux |
| amortissements | SUM(solde) pour comptes 28x, 29x, 39x |
| montant_net | montant_brut - amortissements |

**Filtre** : Inclut les à-nouveaux. Classes 1-5 uniquement.

### mv_bilan_fonctionnel

FRNG, BFR exploitation, BFR hors exploitation, Trésorerie nette.

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture |
| exercice_id | fec_ecriture |
| bf_categorie | pcg_analytique.bf_categorie |
| montant | SUM(solde) en valeurs brutes |

**Agrégats calculés** :
- FRNG = ressources_stables − emplois_stables
- BFR_exploit = actif_circulant_exploit − passif_circulant_exploit
- BFR_hors_exploit = actif_circulant_hors_exploit − passif_circulant_hors_exploit
- TN = FRNG − BFR_total

### mv_compte_resultat

CR structuré par rubrique.

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture |
| exercice_id | fec_ecriture |
| cr_rubrique | pcg_analytique.cr_rubrique |
| cr_signe | pcg_analytique.cr_signe |
| montant | SUM(credit - debit) * cr_signe |

**Filtre** : Classes 6 et 7 uniquement. Exclut les à-nouveaux.

### mv_resultat_differentiel

MCV, taux MCV, seuil de rentabilité, répartition V/F.

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture |
| exercice_id | fec_ecriture |
| nature | 'variable' ou 'fixe' (pcg_analytique.nature_defaut) |
| montant | SUM des charges par nature |

**Agrégats calculés** :
- CA = total produits d'exploitation
- Charges variables = charges nature='variable'
- MCV = CA − Charges variables
- Taux MCV = MCV / CA
- Charges fixes = charges nature='fixe'
- Seuil de rentabilité = Charges fixes / Taux MCV
- Point mort (jours) = Seuil de rentabilité / CA × 365

### mv_sig

9 soldes intermédiaires de gestion + CAF (voir research.md R5 pour le détail des calculs).

| Colonne | Source |
|---|---|
| entite_id | fec_ecriture |
| exercice_id | fec_ecriture |
| sig_rang | 1-9 (ordre des soldes) |
| sig_solde | Nom du solde (Marge commerciale, VA, EBE...) |
| montant | Calcul selon sig_signe dans pcg_analytique |

### v_controles_coherence (vue simple non matérialisée)

| Contrôle | Logique |
|---|---|
| Équilibre D=C | SUM(debit) = SUM(credit) par écriture_num |
| Clôture N-1 = Ouverture N | Soldes clôture exercice N-1 = à-nouveaux exercice N |
| Doublons | Comptage de hash_md5 en double (ne devrait jamais arriver) |
| Comptes non résolus | pcg_numero IS NULL dans fec_ecriture |

---

## RLS (Row Level Security)

Chaque table avec `entite_id` sera protégée par RLS Supabase :
- Les utilisateurs ne voient que les données de leur(s) entité(s) autorisée(s)
- Politique basée sur `auth.uid()` → mapping utilisateur/entité (table à définir dans un chantier ultérieur)
- En attendant, RLS désactivé pour le service role (utilisé par n8n)
