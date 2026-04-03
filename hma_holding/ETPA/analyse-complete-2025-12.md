# Analyse complète — ETPA

**Société** : ENTREPRISE DE PRODUCTION ET DE TRANSFORMATION AGRO-ALIMENTAIRE
**SIREN** : 944 867 696
**Période** : 07/05/2025 → 31/12/2026 (1er exercice — exercice de création)
**Générée le** : 03/04/2026
**Source** : API Pennylane v2 (token lecture seule)

---

## 1. Synthèse exécutive

ETPA est en **phase de démarrage** (premier exercice depuis mai 2025). L'activité principale est la vente de produits finis (sorbés) pour un CA de **10 730 €**. La structure est **fortement déficitaire** avec un résultat net de **-13 388 €**, ce qui est normal pour un exercice de création. Les principaux points d'alerte sont :

- **Trésorerie nette négative** (-21 977 €) avec un compte Bred en découvert (-12 583 €) et une caisse espèces au solde créditeur anormal (-15 443 €)
- **Consommations intermédiaires disproportionnées** (224% du CA) — les charges de services extérieurs (13 204 €) dépassent le CA
- **Taux de matières premières élevé** (58,3%) — au-dessus de la fourchette haute du secteur agroalimentaire (30-50%)
- **Charges de personnel quasi inexistantes** (43 € de tickets restaurant) — pas de salariés déclarés

---

## 2. Balance par classe

| Classe | Intitulé | Débit | Crédit | Solde |
|---|---|---:|---:|---:|
| 1 | Comptes de capitaux | 0,00 | 0,00 | 0,00 |
| 2 | Immobilisations | 7 000,00 | 0,00 | 7 000,00 |
| 3 | Stocks | 0,00 | 0,00 | 0,00 |
| 4 | Tiers | 44 096,18 | 40 741,91 | 3 354,27 |
| 5 | Financiers / Trésorerie | 47 225,18 | 70 967,14 | -23 741,96 |
| 6 | Charges | 24 418,44 | 300,27 | 24 118,17 |
| 7 | Produits | 1 890,00 | 12 620,48 | -10 730,48 |

**Observations** :
- **Classe 1 vide** : aucun capital social, aucun emprunt enregistré — situation anormale même pour une création
- **Classe 2** : 7 000 € de matériels industriels (compte 2154)
- **Classe 3 vide** : pas de stocks comptabilisés malgré une activité de transformation

---

## 3. Soldes Intermédiaires de Gestion

| SIG | Montant (€) | % CA |
|---|---:|---:|
| **CA HT** | 10 730,48 | 100,0% |
| Ventes marchandises (707) | 0,00 | 0,0% |
| Production vendue (701) | 10 730,48 | 100,0% |
| **Production de l'exercice** | 10 730,48 | 100,0% |
| Achats marchandises (607) | -45,00 | -0,4% |
| **Marge commerciale** | -45,00 | -0,4% |
| Achats MP et fournitures (601-602) | -6 258,59 | -58,3% |
| Autres achats (604-608) | -4 524,65 | -42,2% |
| Services extérieurs (61-62) | -13 203,91 | -123,1% |
| **Consommations intermédiaires** | -23 987,15 | -223,6% |
| **Valeur ajoutée** | -13 301,67 | -124,0% |
| Subventions exploitation (74) | 0,00 | 0,0% |
| Impôts et taxes (63) | 0,00 | 0,0% |
| Charges de personnel (64) | -43,02 | -0,4% |
| **EBE** | -13 344,69 | -124,4% |
| Autres produits/charges exploitation | -43,00 | -0,4% |
| **Résultat d'exploitation** | -13 387,69 | -124,8% |
| Produits / charges financiers | 0,00 | 0,0% |
| **RCAI** | -13 387,69 | -124,8% |
| Résultat exceptionnel | 0,00 | 0,0% |
| IS (695) | 0,00 | 0,0% |
| **Résultat net** | -13 387,69 | -124,8% |

---

## 4. Ratios clés

| Ratio | Valeur | Seuil | Commentaire |
|---|---:|---|---|
| Taux VA / CA | -124,0% | > 20% | 🔴 VA négative — les consommations dépassent largement la production |
| Taux EBE / CA | -124,4% | > 5% | 🔴 Structure non viable en l'état |
| Rentabilité nette | -124,8% | > 0% | 🔴 Normal en phase de démarrage, à surveiller |
| Charges personnel / VA | -0,3% | < 80% | 🟡 Quasi nul — pas de masse salariale |
| Achats MP / Production | 58,3% | 30-50% | 🟠 Au-dessus de la norme agroalimentaire |
| Taux d'endettement | N/A | < 100% | Pas de capitaux propres ni dettes financières enregistrés |
| Liquidité générale | N/A | > 1 | Non calculable (classes 1-3 vides) |
| Délai clients | ~196 j | < 60 j | 🔴 Créances 411 : 5 768 € / CA 10 730 € |
| Délai fournisseurs | ~8 j | < 60 j | Dettes 401 : 580 € / Achats 24 032 € |

---

## 5. Anomalies détectées

### 🔴 Critiques

| # | Anomalie | Détail |
|---|---|---|
| 1 | **Classe 1 vide — capital social absent** | Aucun compte de capitaux (10x). Une société doit avoir un capital social enregistré. Le compte 101 est absent. |
| 2 | **Trésorerie Bred en découvert** | Compte 5121001 : solde -12 583,49 €. Découvert bancaire non formalisé. |
| 3 | **Caisse espèces au créditeur anormal** | Compte 530001 : solde -15 443,02 € (créditeur). Une caisse ne peut pas avoir un solde négatif — indique des retraits non justifiés ou des erreurs de saisie. |
| 4 | **Virements en attente d'affectation** | Compte 580101 : -6 387,74 € non affectés. À régulariser. |

### 🟠 Attention

| # | Anomalie | Détail |
|---|---|---|
| 5 | **Aucun stock comptabilisé** | Classe 3 vide malgré une activité de transformation agricole. Les stocks de matières premières (31x) et produits finis (35x) devraient être inventoriés. |
| 6 | **Services extérieurs > CA** | 13 204 € de charges 61-62 pour 10 730 € de CA. Détail : catalogues/imprimés 3 514 €, dons/dîmes 2 404 €, charges diverses 5 544 €. |
| 7 | **Comptes courants associés — mouvements croisés** | HMA doit 2 800 € à ETPA, STIVMAT a avancé 1 785 € à ETPA. Comptes AMEX (-3 370 €) et Crédit Agricole (-577 €) sur des comptes d'associés. |
| 8 | **Charges 656 (pertes de change)** | 43,00 € de pertes de change — inhabituel pour une activité locale en Guyane. |
| 9 | **Dons et dîmes importants** | Compte 623801 : 2 404,32 € — 22,4% du CA. À justifier fiscalement. |

### 🟡 Information

| # | Anomalie | Détail |
|---|---|---|
| 10 | **Décaissements en attente** | Compte 4716001 : 62,00 € — montant faible, à régulariser. |
| 11 | **Pas de charges sociales** | Aucun compte 64x significatif (seulement 43 € de tickets restaurant). Confirme l'absence de salariés. |

---

## 6. Analyse sectorielle — Transformation agricole

### Indicateurs spécifiques ETPA

| Indicateur | Valeur | Norme secteur | Commentaire |
|---|---:|---|---|
| Taux MP / Production vendue | 58,3% | 30-50% | 🟠 Élevé — rendement matière faible ou prix de vente trop bas |
| Rendement matière (Prod / Achats MP) | 1,71x | > 2x | 🟠 Pour 1 € de MP, seulement 1,71 € de production vendue |
| Stocks / CA | 0% | 5-15% | 🔴 Aucun stock — anormal pour de la transformation |
| Subventions / CA | 0% | Variable | 🟡 Aucune subvention FEADER, POSEI ou aide ultramarine perçue |
| Emballages / CA | 7,5% | 3-8% | OK — dans la norme |

### Détail achats matières premières

| Compte | Libellé | Montant |
|---|---|---:|
| 601001 | Matière première | 4 697,54 € |
| 601 | Achats stockés — MP et fournitures | 487,25 € |
| 601002 | Fournitures | 181,20 € |
| 602101 | Matières consommables | 92,60 € |
| 60261 | Emballages perdus | 800,00 € |
| **Total** | | **6 258,59 €** |

### Détail services extérieurs (poste anormalement élevé)

| Compte | Libellé | Montant | % CA |
|---|---|---:|---:|
| 6288 | Autres charges extérieures diverses | 5 543,80 € | 51,7% |
| 6236 | Catalogues et imprimés | 3 514,22 € | 32,7% |
| 623801 | Dons et dîmes | 2 404,32 € | 22,4% |
| 611 | Sous-traitance générale | 1 004,63 € | 9,4% |
| 627001 | Frais bancaires Bred | 259,40 € | 2,4% |
| 616101 | Assurances multirisques | 237,06 € | 2,2% |
| 6257 | Réceptions | 83,60 € | 0,8% |
| 6152 | Entretien réparation immobilier | 70,00 € | 0,7% |
| 6262 | Téléphone et internet | 33,97 € | 0,3% |
| 616 | Primes d'assurances | 29,65 € | 0,3% |
| 6251 | Voyages et déplacements | 22,40 € | 0,2% |
| 623 | Publicité, relations publiques | 0,86 € | 0,0% |

### Produit unique : Sorbé

| Compte | Libellé | Débit | Crédit | Solde |
|---|---|---:|---:|---:|
| 701001 | Vente de produit fini — Sorbé | 1 890,00 | 12 619,62 | -10 729,62 |
| 706 | Prestations de services | 0,00 | 0,86 | -0,86 |

Le CA est concentré à **99,99%** sur un seul produit (Sorbé). Les 1 890 € au débit du 701001 correspondent probablement à des avoirs ou retours.

---

## 7. Trésorerie détaillée

| Compte | Libellé | Solde |
|---|---|---:|
| 5121001 | Bred — ETPA EN FORMATION | -12 583,49 € |
| 5121002 | Sumup FR — Business Account | 6 209,29 € |
| 514001 | Chèques | -160,00 € |
| 530001 | Caisse espèces | -15 443,02 € |
| 580 | Virements internes | 4 623,00 € |
| 580101 | VIR en attente d'affectation | -6 387,74 € |
| **Total (hors 580)** | | **-21 977,22 €** |

---

## 8. Comptes courants et intra-groupe

| Compte | Tiers | Débit | Crédit | Solde | Sens |
|---|---|---:|---:|---:|---|
| 451001 | HMA (holding) | 3 400,00 | 600,00 | 2 800,00 | HMA doit à ETPA |
| 451002 | STIVMAT | 0,00 | 1 785,00 | -1 785,00 | ETPA doit à STIVMAT |
| 451003 | ETPA | 300,00 | 0,00 | 300,00 | Compte propre |
| 455101 | ANATOLE Henri-Michel | 240,96 | 6,20 | 234,76 | Associé débiteur |
| 455101AMEX | AMERICAN EXPRESS | 0,00 | 3 370,27 | -3 370,27 | Carte AMEX associé |
| 455102 | MARTINE ANATOLE | 143,00 | 0,00 | 143,00 | Associée débitrice |
| 455102AGRICOLE | CRÉDIT-AGRICOLE | 0,00 | 577,28 | -577,28 | CB associée |

**Solde net comptes courants associés** : -2 054,79 € (les associés ont plus avancé que prélevé)

---

## 9. Factures

| Type | Nombre | Observations |
|---|---:|---|
| Factures fournisseurs | 100+ | has_more=true → plus de 100 factures |
| Factures clients | 77 | Client principal : MEGABOEUF |

---

## 10. Recommandations

### Priorité 1 — Urgentes

1. **Enregistrer le capital social** — Le compte 101 est vide. Régulariser immédiatement l'apport en capital de constitution.
2. **Régulariser la caisse** — Le solde créditeur de -15 443 € sur la caisse est impossible physiquement. Identifier les opérations manquantes (encaissements non comptabilisés ou retraits fictifs).
3. **Affecter les virements en attente** — 6 388 € sur le compte 580101 à ventiler sur les bons comptes.

### Priorité 2 — Avant clôture

4. **Inventaire des stocks** — Comptabiliser les stocks de matières premières (31x) et produits finis (35x) pour refléter la réalité économique et améliorer le résultat.
5. **Justifier les "autres charges diverses" (6288)** — 5 544 € soit 51,7% du CA sur un compte fourre-tout. Détailler et réaffecter sur les bons comptes.
6. **Formaliser le découvert Bred** — Si le découvert est autorisé, le documenter. Sinon, rééquilibrer la trésorerie.
7. **Dons et dîmes** — Vérifier la déductibilité fiscale des 2 404 € (conditions art. 238 bis du CGI).

### Priorité 3 — Structuration

8. **Rechercher des subventions** — ETPA en Guyane est éligible au FEADER (agriculture), POSEI (ultramarin), et potentiellement au dispositif Girardin productif. Aucune subvention n'est comptabilisée.
9. **Diversifier le produit** — 99,99% du CA sur un seul produit (Sorbé) est un risque commercial majeur.
10. **Suivre le rendement matière** — Objectif : passer de 1,71x à 2x minimum (réduire le taux MP de 58% à 50%).

---

*Rapport généré par le skill pennylane-analyse — Données Pennylane lecture seule*
*77 factures clients · 100+ factures fournisseurs · 47 comptes actifs · 11 journaux*
