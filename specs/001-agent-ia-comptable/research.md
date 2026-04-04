# Research: Chantier A — Socle de données financières

**Branch**: `001-agent-ia-comptable` | **Date**: 2026-04-02

## R1 — Format FEC (Fichier des Écritures Comptables)

**Decision**: 18 colonnes normalisées selon l'Art. A.47 A-1 du Livre des Procédures Fiscales.

**Rationale**: Le FEC est le format légal français obligatoire pour l'export des écritures comptables. L'alignement sur ce format garantit la compatibilité avec les outils d'audit et facilite les contrôles fiscaux.

**Colonnes FEC normalisées** :
1. JournalCode
2. JournalLib
3. EcritureNum
4. EcritureDate
5. CompteNum
6. CompteLib
7. CompAuxNum
8. CompAuxLib
9. PieceRef
10. PieceDate
11. EcritureLib
12. Debit
13. Credit
14. EcrtureLet (lettrage)
15. DateLet
16. ValidDate
17. Montantdevise
18. Idevise

**Champs calculés ajoutés** : `entite_id`, `exercice_id`, `fec_import_id`, `pcg_numero` (résolu via `resolve_compte()`), `hash_md5` (anti-doublons).

**Alternatives considérées** :
- Stocker les données au format Pennylane natif → rejeté : format propriétaire, pas de standard
- Stocker au format XBRL → rejeté : trop lourd pour l'usage interne

---

## R2 — API Pennylane v2 — Mapping vers FEC

**Decision**: Utiliser `/ledger_entries` comme source principale pour reconstituer le FEC.

**Rationale**: C'est le seul endpoint qui retourne les écritures individuelles avec débit/crédit, journal et lettrage.

**Mapping Pennylane → FEC** :

| Champ FEC | Source Pennylane `/ledger_entries` |
|---|---|
| JournalCode | `journal.code` |
| JournalLib | `journal.label` |
| EcritureNum | `document_number` |
| EcritureDate | `date` |
| CompteNum | `planitem.number` |
| CompteLib | `planitem.label` |
| CompAuxNum | `planitem.auxiliary_code` (si compte auxiliaire) |
| CompAuxLib | `planitem.auxiliary_label` |
| PieceRef | `document_number` |
| PieceDate | `date` |
| EcritureLib | `label` |
| Debit | `debit` |
| Credit | `credit` |
| EcrtureLet | `lettering_code` |
| DateLet | `lettering_date` |
| ValidDate | `validated_at` |

**Pagination** : L'API Pennylane pagine à 100 résultats par défaut (max 100). Utiliser le paramètre `page` pour itérer.

**Filtres utiles** : `updated_at[gte]` pour sync incrémentale (ne récupérer que les nouvelles écritures depuis le dernier import).

**Alternatives considérées** :
- `/trial_balance` → ne donne que les soldes agrégés, pas les écritures individuelles
- Export CSV Pennylane → pas d'API, nécessite une action manuelle

---

## R3 — Résolution de comptes auxiliaires

**Decision**: Table `compte_resolution` avec fonction `resolve_compte()` par préfixe décroissant.

**Rationale**: Les écritures Pennylane utilisent des comptes auxiliaires (ex: "411CLIENT001") qui doivent être résolus vers le compte PCG racine ("411"). La résolution par préfixe décroissant est la méthode standard.

**Algorithme** :
1. Chercher le CompteNum exact dans `pcg_analytique`
2. Si pas trouvé, retirer le dernier caractère et recommencer
3. Jusqu'à trouver une correspondance ou atteindre 3 caractères (classe de compte)

**Cas particuliers** :
- Comptes de tiers (41x, 40x) : auxiliaire fréquent
- Comptes bancaires (512x) : auxiliaire par banque

---

## R4 — Vues matérialisées — Stratégie de rafraîchissement

**Decision**: REFRESH MATERIALIZED VIEW CONCURRENTLY après chaque sync Pennylane.

**Rationale**: Le `CONCURRENTLY` permet de ne pas bloquer les lectures pendant le rafraîchissement. Nécessite un index UNIQUE sur chaque vue matérialisée.

**Ordre de rafraîchissement** (respecte les dépendances) :
1. `mv_balance_generale`
2. `mv_bilan` + `mv_compte_resultat` + `mv_sig` (parallélisables, dépendent de balance)
3. `mv_bilan_fonctionnel` (dépend de mv_bilan)
4. `mv_resultat_differentiel` (dépend de mv_compte_resultat)

**Performance estimée** : < 60 secondes pour 200k écritures sur PostgreSQL 15.

---

## R5 — SIG — Les 9 soldes intermédiaires de gestion

**Decision**: Calculer les 9 soldes + CAF selon le PCG, en utilisant le mapping `pcg_analytique.sig_solde`.

**Les 9 soldes** :
1. **Marge commerciale** = Ventes de marchandises (707) − Achats de marchandises (607) − Variation de stock marchandises (6037)
2. **Production de l'exercice** = Production vendue (70 hors 707) + Production stockée (713) + Production immobilisée (72)
3. **Valeur ajoutée** = Marge commerciale + Production − Consommations en provenance de tiers (60 hors 607/6037 + 61 + 62)
4. **EBE (Excédent Brut d'Exploitation)** = VA + Subventions d'exploitation (74) − Impôts et taxes (63) − Charges de personnel (64)
5. **Résultat d'exploitation** = EBE + Reprises/transferts (781/791) + Autres produits (75) − DAP (681) − Autres charges (65)
6. **Résultat courant avant impôts** = Résultat d'exploitation + Produits financiers (76) − Charges financières (66)
7. **Résultat exceptionnel** = Produits exceptionnels (77) − Charges exceptionnelles (67)
8. **Résultat de l'exercice** = RCAI + Résultat exceptionnel − Participation (691) − IS (695)
9. **CAF (Capacité d'autofinancement)** = Résultat + DAP (681+686+687) − Reprises (781+786+787) + VNC cessions (675) − Produits cessions (775)

**Points techniques** :
- Le 791 (transferts de charges) va au résultat d'exploitation, pas à la VA
- Distinction 6037 (marge commerciale) vs 6031/6032 (valeur ajoutée)
- Les à-nouveaux sont filtrés pour le CR et le SIG (journal OD/AN)

---

## R6 — Bilan fonctionnel

**Decision**: Calculer en valeurs brutes, les amortissements et dépréciations passent en ressources stables.

**Structure** :
- **Emplois stables** = Actif immobilisé brut
- **Ressources stables** = Capitaux propres + Amortissements/Dépréciations + Dettes financières > 1 an
- **FRNG** = Ressources stables − Emplois stables
- **BFR d'exploitation** = Actif circulant d'exploitation − Passif circulant d'exploitation
- **BFR hors exploitation** = Actif circulant hors exploitation − Passif circulant hors exploitation
- **TN (Trésorerie nette)** = FRNG − BFR total = Trésorerie active − Trésorerie passive

**Classification exploitation/hors exploitation** : définie dans `pcg_analytique.bilan_poste` avec un suffixe _exploit ou _hors_exploit.

---

## R7 — Pattern staging → merge pour n8n

**Decision**: Table temporaire `_staging_fec` vidée à chaque run, puis UPSERT vers `fec_ecriture`.

**Workflow n8n** :
1. **Staging** : Créer/vider `_staging_fec` → récupérer toutes les pages de `/ledger_entries` → INSERT dans staging
2. **Merge** : `INSERT INTO fec_ecriture SELECT ... FROM _staging_fec ON CONFLICT (hash_md5) DO NOTHING`
3. **Refresh** : Appeler `refresh_all_views()`
4. **Log** : INSERT dans `fec_import` avec stats (nb lignes, durée, statut)

**Hash anti-doublons** : MD5 de la concaténation `entite_id || EcritureNum || CompteNum || EcritureDate || Debit || Credit || JournalCode`.

**Alternatives considérées** :
- UPSERT direct sans staging → rejeté : pas de visibilité sur le delta, pas de rollback facile
- CDC (Change Data Capture) → rejeté : Pennylane ne propose pas de webhook ni de stream
