# Data Model: Dashboard CRD sur mesure

**Feature**: 002-dashboard-crd-custom
**Date**: 2026-04-10

## Vues SQL existantes (lecture seule)

Le dashboard ne cree aucune table — il consomme les vues PostgreSQL HMA existantes.

### v_crd (source principale)

CRD agrege par entite/exercice/trimestre.

| Colonne | Type | Description |
|---------|------|-------------|
| entite_id | int | FK vers entite |
| entite_nom | text | Nom de la structure |
| exercice_id | int | FK vers exercice |
| exercice_label | text | Label exercice |
| annee | int | Annee |
| trimestre | int | Trimestre (1-4) |
| ca | numeric | Chiffre d'affaires |
| charges_variables | numeric | Total charges variables |
| mcv | numeric | Marge sur cout variable (CA - charges_variables) |
| charges_fixes | numeric | Total charges fixes exploitation |
| resultat_exploitation | numeric | MCV - charges fixes |
| resultat_financier | numeric | Produits - charges financiers |
| rcai | numeric | Resultat courant avant impot |
| resultat_exceptionnel | numeric | Produits - charges exceptionnels |
| impot_sur_societes | numeric | IS |
| resultat_net | numeric | Resultat net |
| caf | numeric | Capacite d'autofinancement |
| pct_charges_var | numeric | % charges variables / CA |
| pct_mcv | numeric | % MCV / CA (taux de marge) |
| pct_charges_fixes | numeric | % charges fixes / CA |
| pct_res_exploit | numeric | % resultat exploitation / CA |
| pct_rcai | numeric | % RCAI / CA |
| pct_res_net | numeric | % resultat net / CA |
| pct_caf | numeric | % CAF / CA |
| seuil_rentabilite | numeric | Seuil de rentabilite en euros |
| point_mort_jours | numeric | Point mort en jours |
| marge_securite | numeric | Marge de securite en euros |
| pct_marge_securite | numeric | % marge securite / CA |

### v_crd_drilldown (drilldown)

Detail par categorie/rubrique/compte avec dimension temporelle.

| Colonne | Type | Description |
|---------|------|-------------|
| entite_id | int | FK vers entite |
| entite_nom | text | Nom structure |
| exercice_id | int | FK vers exercice |
| exercice_label | text | Label exercice |
| annee | int | Annee |
| trimestre | int | Trimestre |
| mois | int | Mois (1-12) |
| mois_label | text | Label mois (ex: "2026-01") |
| crd_ordre | int | Ordre dans le CRD (1-6) |
| crd_categorie | text | Categorie CRD (ex: "Charges variables") |
| crd_rubrique | text | Sous-rubrique (ex: "Achats matieres") |
| crd_signe | int | Signe (+1 ou -1) |
| compte_numero | text | Numero de compte PCG |
| compte_libelle | text | Libelle du compte |
| nature_defaut | text | Variable ou Fixe |
| montant | numeric | Montant calcule (signe * (credit - debit)) |

### v_ytd_mensuel (evolution temporelle)

CA, charges, produits, resultat par mois.

| Colonne | Type | Description |
|---------|------|-------------|
| entite_id | int | FK vers entite |
| entite_nom | text | Nom structure |
| exercice_id | int | FK vers exercice |
| exercice_label | text | Label exercice |
| annee | int | Annee |
| mois | int | Mois (1-12) |
| mois_label | text | Label mois |
| trimestre | int | Trimestre |
| debut_mois | date | Premier jour du mois |
| ca | numeric | Chiffre d'affaires du mois |
| charges | numeric | Total charges du mois |
| produits | numeric | Total produits du mois |
| resultat | numeric | Produits - charges |

## Flux de donnees

```
PostgreSQL HMA (vues existantes)
    │
    ├── v_crd ──────────→ KPI cards + tableau CRD + seuil rentabilite
    ├── v_crd_drilldown ─→ Drilldown 3 niveaux + barres par rubrique
    └── v_ytd_mensuel ───→ Courbes evolution mensuelle + donut charges
    │
    ▼
Dashboard Dash (lecture seule, pas d'ecriture)
```

## Requetes SQL prevues

### KPI cards (v_crd)
```sql
SELECT * FROM v_crd
WHERE entite_id = :entite AND annee = :annee AND trimestre = :trimestre
```

### KPI evolution (v_crd, periode de reference)
```sql
-- Periode courante + reference (ex: N-1)
SELECT * FROM v_crd
WHERE entite_id = :entite AND annee IN (:annee, :annee_ref)
```

### Drilldown niveau 1 : categories (v_crd_drilldown)
```sql
SELECT crd_categorie, SUM(montant) AS total
FROM v_crd_drilldown
WHERE entite_id = :entite AND annee = :annee
GROUP BY crd_ordre, crd_categorie
ORDER BY crd_ordre
```

### Drilldown niveau 2 : rubriques
```sql
SELECT crd_rubrique, SUM(montant) AS total
FROM v_crd_drilldown
WHERE entite_id = :entite AND annee = :annee AND crd_categorie = :categorie
GROUP BY crd_rubrique
ORDER BY SUM(montant) DESC
```

### Drilldown niveau 3 : comptes PCG
```sql
SELECT compte_numero, compte_libelle, SUM(montant) AS total
FROM v_crd_drilldown
WHERE entite_id = :entite AND annee = :annee AND crd_rubrique = :rubrique
GROUP BY compte_numero, compte_libelle
ORDER BY SUM(montant) DESC
```

### Evolution mensuelle (v_ytd_mensuel)
```sql
SELECT * FROM v_ytd_mensuel
WHERE entite_id = :entite AND annee = :annee
ORDER BY mois
```
