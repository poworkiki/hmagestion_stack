# Referentiel de comptabilite analytique et financiere — PCG

> Document de reference academique pour l'analyse financiere et la comptabilite analytique.
> Toutes les formules sont conformes au Plan Comptable General (PCG 2025, normes ANC).
> Document generique, reutilisable dans tout contexte comptable francais.

**Derniere mise a jour :** 2 avril 2026

---

## Table des matieres

1. [SIG — Soldes Intermediaires de Gestion](#1-sig--soldes-intermediaires-de-gestion)
2. [Compte de Resultat](#2-compte-de-resultat--structure-detaillee)
3. [Bilan comptable](#3-bilan-comptable)
4. [Bilan fonctionnel](#4-bilan-fonctionnel)
5. [Resultat differentiel (seuil de rentabilite)](#5-resultat-differentiel--seuil-de-rentabilite)
6. [Ratios financiers](#6-ratios-financiers)
7. [Consolidation groupe](#7-consolidation-groupe)
8. [Tableau de financement (PCG)](#8-tableau-de-financement-pcg)
9. [Comptabilite analytique d'exploitation](#9-comptabilite-analytique-dexploitation)
10. [Evaluation et depreciation des actifs](#10-evaluation-et-depreciation-des-actifs)

---

## 1. SIG — Soldes Intermediaires de Gestion

Les 9 soldes + la CAF. Chaque solde se calcule en cascade a partir du precedent.

**Regle generale** : les comptes de produits (classe 7) sont au CREDIT (solde crediteur = positif). Les comptes de charges (classe 6) sont au DEBIT (solde debiteur = positif). Dans les formules ci-dessous, `+` signifie "ajoute au solde" et `-` signifie "retranche du solde".

### 1.1. Marge commerciale

```
Marge commerciale = Ventes de marchandises - Cout d'achat des marchandises vendues
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | **707** | Ventes de marchandises |
| + | **7097** | Rabais, remises, ristournes accordes (ventes marchandises) — ATTENTION : ce compte est crediteur en cas d'annulation, il vient en deduction du 707. En pratique, on fait `707 - 7097` |
| - | **607** | Achats de marchandises |
| - | **6037** | Variation des stocks de marchandises |
| + | **6097** | Rabais, remises, ristournes obtenus sur achats de marchandises |

**Formule SQL :**
```
+ SUM(credit - debit) WHERE compte LIKE '707%'
- SUM(credit - debit) WHERE compte LIKE '7097%'
- SUM(debit - credit) WHERE compte LIKE '607%'
- SUM(debit - credit) WHERE compte LIKE '6037%'
+ SUM(credit - debit) WHERE compte LIKE '6097%'
```

**Pieges et exceptions :**
- Le compte **6037** (variation de stock de marchandises) est inclus dans la marge commerciale, PAS dans la valeur ajoutee.
- Les comptes **6031** et **6032** (variation de stocks de matieres premieres et fournitures) vont dans la valeur ajoutee via la production.
- Le **7097** est un compte de produits a solde debiteur (il diminue les ventes). Signe inverse.
- Ne pas confondre 707 (marchandises) et 701-706 (production vendue).

---

### 1.2. Production de l'exercice

```
Production de l'exercice = Production vendue + Production stockee + Production immobilisee
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | **701** | Ventes de produits finis |
| + | **702** | Ventes de produits intermediaires |
| + | **703** | Ventes de produits residuels |
| + | **704** | Travaux |
| + | **705** | Etudes |
| + | **706** | Prestations de services |
| + | **708** | Produits des activites annexes |
| - | **7091** a **7098** (sauf 7097) | RRR accordes sur production vendue |
| + | **713** | Variation des stocks (en-cours, produits) |
| + | **72** | Production immobilisee |

**Formule SQL :**
```
+ SUM(credit - debit) WHERE compte ~ '^70[1-68]'
- SUM(credit - debit) WHERE compte ~ '^709[^7]'   -- 7091-7096, 7098 (exclure 7097)
+ SUM(credit - debit) WHERE compte LIKE '713%'
+ SUM(credit - debit) WHERE compte LIKE '72%'
```

**Pieges et exceptions :**
- Le **713** (variation des stocks de produits) peut etre debiteur (destockage) ou crediteur (stockage). Son solde s'ajoute algebriquement.
- Le **72** (production immobilisee) est un produit mais ne genere pas de tresorerie. Souvent oublie.
- Les **7091 a 7096 et 7098** viennent en deduction de la production vendue, mais le **7097** reste dans la marge commerciale.
- Le **708** (produits annexes) est inclus dans la production, pas dans les "autres produits".

---

### 1.3. Valeur ajoutee

```
Valeur ajoutee = Marge commerciale + Production de l'exercice - Consommations en provenance de tiers
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | Marge commerciale (solde calcule en 1.1) |
| + | | Production de l'exercice (solde calcule en 1.2) |
| - | **601** | Achats de matieres premieres |
| - | **602** | Achats d'autres approvisionnements |
| - | **604** | Achats d'etudes et de prestations de services |
| - | **605** | Achats de materiels, equipements et travaux |
| - | **606** | Achats non stockes de matieres et fournitures |
| - | **608** | Frais accessoires d'achat |
| - | **609** (sauf 6097) | RRR obtenus sur achats (hors marchandises) — ATTENTION signe inverse, vient en deduction des achats |
| - | **6031** | Variation de stocks de matieres premieres |
| - | **6032** | Variation de stocks d'autres approvisionnements |
| - | **61** | Services exterieurs |
| - | **62** | Autres services exterieurs |

**Formule SQL (consommations en provenance de tiers) :**
```
+ SUM(debit - credit) WHERE compte ~ '^60[124568]'
- SUM(credit - debit) WHERE compte ~ '^609[^7]'   -- RRR obtenus hors marchandises
+ SUM(debit - credit) WHERE compte ~ '^603[12]'
+ SUM(debit - credit) WHERE compte LIKE '61%'
+ SUM(debit - credit) WHERE compte LIKE '62%'
```

Puis : `VA = Marge commerciale + Production - Consommations`

**Pieges et exceptions :**
- Le **6037** (variation stock marchandises) est deja dans la marge commerciale. Ne PAS le remettre ici.
- Les **6031/6032** (variation stock matieres/approvisionnements) sont dans les consommations, PAS dans la marge commerciale.
- Le **791** (transferts de charges d'exploitation) n'entre PAS dans la VA. Il va directement dans le resultat d'exploitation.
- Le **609** (sauf 6097) vient en deduction des achats (signe negatif dans les charges = positif pour la VA).
- Les **603** hors 6031, 6032, 6037 (ex: 6033, 6034, 6035, 6038) sont rares mais suivent la meme logique que les matieres si utilises.

---

### 1.4. Excedent Brut d'Exploitation (EBE)

```
EBE = Valeur ajoutee + Subventions d'exploitation - Impots, taxes et versements assimiles - Charges de personnel
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | Valeur ajoutee (solde calcule en 1.3) |
| + | **74** | Subventions d'exploitation |
| - | **63** | Impots, taxes et versements assimiles |
| - | **64** | Charges de personnel |

**Formule SQL :**
```
VA
+ SUM(credit - debit) WHERE compte LIKE '74%'
- SUM(debit - credit) WHERE compte LIKE '63%'
- SUM(debit - credit) WHERE compte LIKE '64%'
```

**Pieges et exceptions :**
- L'EBE ne contient AUCUNE dotation aux amortissements/depreciations/provisions. C'est un indicateur de performance operationnelle pure.
- Le **74** (subventions d'exploitation) est inclus dans l'EBE, mais le **77** (produits exceptionnels) et le **771** (subventions virements au resultat) NE LE SONT PAS.
- Les **631** (impots sur remuneration, taxe sur salaires) sont dans les impots, pas dans les charges de personnel.
- La **participation des salaries (691)** n'est PAS dans l'EBE, elle intervient apres le resultat courant.

---

### 1.5. Resultat d'exploitation

```
Resultat d'exploitation = EBE + Reprises sur amort/deprec/prov d'exploitation + Transferts de charges d'exploitation + Autres produits de gestion courante - Dotations aux amort/deprec/prov d'exploitation - Autres charges de gestion courante
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | EBE (solde calcule en 1.4) |
| + | **781** | Reprises sur amortissements et provisions d'exploitation |
| + | **791** | Transferts de charges d'exploitation |
| + | **75** | Autres produits de gestion courante |
| - | **681** | Dotations aux amortissements, depreciations et provisions d'exploitation |
| - | **65** | Autres charges de gestion courante |

**Formule SQL :**
```
EBE
+ SUM(credit - debit) WHERE compte LIKE '781%'
+ SUM(credit - debit) WHERE compte LIKE '791%'
+ SUM(credit - debit) WHERE compte LIKE '75%'
- SUM(debit - credit) WHERE compte LIKE '681%'
- SUM(debit - credit) WHERE compte LIKE '65%'
```

**Pieges et exceptions :**
- Le **791** (transferts de charges) entre UNIQUEMENT dans le resultat d'exploitation, jamais dans la VA ni dans l'EBE.
- Le **75** inclut les redevances pour brevets (751), les revenus d'immeubles non affectes (752), les jetons de presence (753), etc.
- Le **65** inclut les redevances versees (651), les pertes sur creances irrecouvrables (654), les quotes-parts de resultat sur operations en commun (655).
- Attention aux comptes **755** (quotes-parts de resultat sur operations en commun — benefice) et **655** (quotes-parts — perte) : ils sont en 75/65, donc dans le resultat d'exploitation.

---

### 1.6. Resultat courant avant impots (RCAI)

```
RCAI = Resultat d'exploitation + Quotes-parts de resultat sur operations en commun + Produits financiers - Charges financieres
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | Resultat d'exploitation (solde calcule en 1.5) |
| + | **76** | Produits financiers |
| + | **786** | Reprises sur provisions et depreciations financieres |
| + | **796** | Transferts de charges financieres |
| - | **66** | Charges financieres |
| - | **686** | Dotations aux provisions et depreciations financieres |

**Formule SQL :**
```
Rex
+ SUM(credit - debit) WHERE compte LIKE '76%'
+ SUM(credit - debit) WHERE compte LIKE '786%'
+ SUM(credit - debit) WHERE compte LIKE '796%'
- SUM(debit - credit) WHERE compte LIKE '66%'
- SUM(debit - credit) WHERE compte LIKE '686%'
```

**Pieges et exceptions :**
- Les **761** (produits de participations) incluent les dividendes recus — important pour les societes meres.
- Les **666** (pertes de change) et **766** (gains de change) sont financiers.
- Le **768** (autres produits financiers) inclut les escomptes obtenus.
- Le **668** (autres charges financieres) inclut les escomptes accordes.
- Note : dans certaines presentations simplifiees, les quotes-parts (755/655) sont sorties du Rex pour etre presentees entre Rex et RCAI. Dans le PCG strict, elles restent dans le Rex (classe 75/65).

---

### 1.7. Resultat exceptionnel

```
Resultat exceptionnel = Produits exceptionnels - Charges exceptionnelles
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | **77** | Produits exceptionnels |
| + | **787** | Reprises sur provisions et depreciations exceptionnelles |
| + | **797** | Transferts de charges exceptionnelles |
| - | **67** | Charges exceptionnelles |
| - | **687** | Dotations aux provisions et depreciations exceptionnelles |

**Detail des comptes 77 :**
- **771** : Produits exceptionnels sur operations de gestion
- **775** : Produits des cessions d'elements d'actif
- **777** : Quote-part des subventions d'investissement viree au resultat
- **778** : Autres produits exceptionnels

**Detail des comptes 67 :**
- **671** : Charges exceptionnelles sur operations de gestion
- **675** : Valeurs comptables des elements d'actif cedes (VCEAC)
- **678** : Autres charges exceptionnelles

**Formule SQL :**
```
+ SUM(credit - debit) WHERE compte LIKE '77%'
+ SUM(credit - debit) WHERE compte LIKE '787%'
+ SUM(credit - debit) WHERE compte LIKE '797%'
- SUM(debit - credit) WHERE compte LIKE '67%'
- SUM(debit - credit) WHERE compte LIKE '687%'
```

**Pieges et exceptions :**
- La **plus-value de cession** = 775 - 675. Le 775 est le prix de cession, le 675 est la valeur nette comptable (VNC = brut - amortissements cumules).
- Le **777** (quote-part subvention d'investissement) est un mecanisme d'etalement : la subvention (compte 13) est progressivement viree au resultat.
- Depuis la reforme 2024 (ANC 2022-06), certaines charges/produits exceptionnels sont reclasses en exploitation. Verifier le plan de comptes de chaque entite.

---

### 1.8. Resultat de l'exercice

```
Resultat de l'exercice = RCAI + Resultat exceptionnel - Participation des salaries - Impots sur les benefices
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | RCAI (solde calcule en 1.6) |
| + | | Resultat exceptionnel (solde calcule en 1.7) |
| - | **691** | Participation des salaries aux resultats |
| - | **695** | Impots sur les benefices (IS) |
| - | **696** | Supplements d'impots sur les societes lies aux distributions |
| - | **699** | Produits — reports en arriere des deficits (carry-back) — ATTENTION signe inverse |

**Formule SQL :**
```
RCAI + Rex_exceptionnel
- SUM(debit - credit) WHERE compte LIKE '691%'
- SUM(debit - credit) WHERE compte LIKE '695%'
- SUM(debit - credit) WHERE compte LIKE '696%'
- SUM(debit - credit) WHERE compte LIKE '699%'
```

**Pieges et exceptions :**
- Le **699** est crediteur quand il y a un carry-back (credit d'impot). Il vient alors en diminution de la charge d'IS.
- Le resultat de l'exercice = solde du compte **12** (resultat de l'exercice). C'est un controle : le calcul en cascade des SIG doit donner le meme resultat que le solde du 12.
- La **CVAE** (contribution sur la valeur ajoutee des entreprises, compte 6354 ou 63514) est en 63, donc dans l'EBE, PAS dans l'IS.

---

### 1.9. Capacite d'Autofinancement (CAF)

La CAF n'est pas un SIG a proprement parler mais se calcule a partir des SIG.

#### Methode additive (a partir du resultat net)

```
CAF = Resultat net
    + Dotations aux amortissements, depreciations et provisions (681 + 686 + 687)
    - Reprises sur amortissements, depreciations et provisions (781 + 786 + 787)
    + Valeur comptable des elements d'actif cedes (675)
    - Produits des cessions d'elements d'actif (775)
    - Quote-part des subventions d'investissement viree au resultat (777)
```

| Signe | Comptes | Libelle |
|-------|---------|---------|
| + | | Resultat net |
| + | **681** | Dotations exploitation |
| + | **686** | Dotations financieres |
| + | **687** | Dotations exceptionnelles |
| - | **781** | Reprises exploitation |
| - | **786** | Reprises financieres |
| - | **787** | Reprises exceptionnelles |
| + | **675** | VCEAC (valeur comptable elements actif cedes) |
| - | **775** | PCEA (produits des cessions elements actif) |
| - | **777** | Quote-part subventions d'investissement virees au resultat |

**Formule SQL (methode additive) :**
```
Resultat_net
+ SUM(debit - credit) WHERE compte LIKE '681%'
+ SUM(debit - credit) WHERE compte LIKE '686%'
+ SUM(debit - credit) WHERE compte LIKE '687%'
- SUM(credit - debit) WHERE compte LIKE '781%'
- SUM(credit - debit) WHERE compte LIKE '786%'
- SUM(credit - debit) WHERE compte LIKE '787%'
+ SUM(debit - credit) WHERE compte LIKE '675%'
- SUM(credit - debit) WHERE compte LIKE '775%'
- SUM(credit - debit) WHERE compte LIKE '777%'
```

#### Methode soustractive (a partir de l'EBE)

```
CAF = EBE
    + Transferts de charges d'exploitation (791)
    + Autres produits d'exploitation (75 sauf 755)
    - Autres charges d'exploitation (65 sauf 655)
    + Produits financiers (76)
    - Charges financieres (66)
    + Produits exceptionnels de gestion (771, 778)
    - Charges exceptionnelles de gestion (671, 678)
    - Participation des salaries (691)
    - Impots sur les benefices (695)
```

**Pieges et exceptions :**
- Les **791, 796, 797** (transferts de charges) NE SONT PAS des reprises. Ils sont inclus dans la CAF (ils correspondent a des charges reelles transferees). C'est une erreur frequente de les exclure.
- La CAF methode additive et soustractive DOIVENT donner le meme resultat. C'est un controle de coherence.
- La CAF exclut systematiquement les elements "calcules" (dotations, reprises) et les plus/moins-values de cession (675, 775).
- Le **777** est exclu car c'est un produit calcule (reprise progressive de la subvention).
- Les **755/655** (quotes-parts operations en commun) sont debattues. En pratique, elles sont souvent incluses dans la CAF car elles generent des flux.

---

## 2. Compte de Resultat — Structure detaillee

### 2.1. Produits d'exploitation

| Comptes | Libelle | Sous-rubrique |
|---------|---------|---------------|
| **701-708** | Production vendue (biens et services) | Chiffre d'affaires net |
| **7091-7098** | RRR accordes | En deduction du CA |
| **707** | Ventes de marchandises | CA marchandises |
| **7097** | RRR sur ventes de marchandises | En deduction du CA marchandises |
| **713** | Variation des stocks de produits | Production stockee |
| **72** | Production immobilisee | Production immobilisee |
| **74** | Subventions d'exploitation | Subventions |
| **75** | Autres produits de gestion courante | Autres produits |
| **781** | Reprises sur amort/deprec/prov d'exploitation | Reprises |
| **791** | Transferts de charges d'exploitation | Transferts |

**Chiffre d'affaires net HT** = `SUM(credit - debit) WHERE compte ~ '^70' - SUM(credit - debit) WHERE compte ~ '^709'`

**Total produits d'exploitation** = CA net + 713 + 72 + 74 + 75 + 781 + 791

### 2.2. Charges d'exploitation

| Comptes | Libelle | Sous-rubrique |
|---------|---------|---------------|
| **601-602** | Achats de matieres premieres et approvisionnements | Achats |
| **6031-6032** | Variation de stocks (matieres, approvisionnements) | Variation stocks |
| **604-606, 608** | Autres achats et charges externes (part achats) | Achats |
| **6091-6096, 6098** | RRR obtenus (hors marchandises) | En deduction des achats |
| **607** | Achats de marchandises | Achats marchandises |
| **6037** | Variation de stocks de marchandises | Variation stocks marchandises |
| **6097** | RRR obtenus sur marchandises | En deduction des achats marchandises |
| **61** | Services exterieurs | Services exterieurs |
| **62** | Autres services exterieurs | Autres services exterieurs |
| **63** | Impots, taxes et versements assimiles | Impots et taxes |
| **64** | Charges de personnel | Personnel |
| **65** | Autres charges de gestion courante | Autres charges |
| **681** | Dotations aux amort/deprec/prov d'exploitation | Dotations |

**Total charges d'exploitation** = SUM de tous les comptes ci-dessus (debit - credit)

### 2.3. Resultat d'exploitation

```
Resultat d'exploitation = Total produits d'exploitation - Total charges d'exploitation
```

### 2.4. Produits financiers

| Comptes | Libelle |
|---------|---------|
| **761** | Produits de participations |
| **762** | Produits des autres immobilisations financieres |
| **763** | Revenus des autres creances |
| **764** | Revenus des VMP |
| **765** | Escomptes obtenus |
| **766** | Gains de change |
| **767** | Produits nets sur cessions de VMP |
| **768** | Autres produits financiers |
| **786** | Reprises sur provisions et depreciations financieres |
| **796** | Transferts de charges financieres |

### 2.5. Charges financieres

| Comptes | Libelle |
|---------|---------|
| **661** | Charges d'interets |
| **664** | Pertes sur creances liees a des participations |
| **665** | Escomptes accordes |
| **666** | Pertes de change |
| **667** | Charges nettes sur cessions de VMP |
| **668** | Autres charges financieres |
| **686** | Dotations aux provisions et depreciations financieres |

### 2.6. Resultat financier

```
Resultat financier = Total produits financiers - Total charges financieres
= SUM(credit - debit) WHERE compte ~ '^7[69]6'
- SUM(debit - credit) WHERE compte ~ '^6[68]6'
```

### 2.7. RCAI

```
RCAI = Resultat d'exploitation + Resultat financier
```

### 2.8. Produits exceptionnels

| Comptes | Libelle |
|---------|---------|
| **771** | Produits exceptionnels sur operations de gestion |
| **775** | Produits des cessions d'elements d'actif |
| **777** | Quote-part des subventions d'investissement viree au resultat |
| **778** | Autres produits exceptionnels |
| **787** | Reprises sur provisions et depreciations exceptionnelles |
| **797** | Transferts de charges exceptionnelles |

### 2.9. Charges exceptionnelles

| Comptes | Libelle |
|---------|---------|
| **671** | Charges exceptionnelles sur operations de gestion |
| **675** | VCEAC — Valeurs comptables des elements d'actif cedes |
| **678** | Autres charges exceptionnelles |
| **687** | Dotations aux provisions et depreciations exceptionnelles |

### 2.10. Resultat exceptionnel

```
Resultat exceptionnel = Total produits exceptionnels - Total charges exceptionnelles
```

### 2.11. Participation et IS

| Comptes | Libelle |
|---------|---------|
| **691** | Participation des salaries aux resultats de l'entreprise |
| **695** | Impots sur les benefices |
| **696** | Supplements d'impot sur les benefices |
| **699** | Produits — report en arriere des deficits |

### 2.12. Resultat net

```
Resultat net = RCAI + Resultat exceptionnel - 691 - 695 - 696 + 699
```

**Controle** : le resultat net doit correspondre au solde du compte **12** (resultat de l'exercice).

---

## 3. Bilan comptable

**Regle fondamentale** : le bilan comptable est presente en **valeurs nettes**. L'actif brut est diminue des amortissements (comptes 28) et depreciations (comptes 29, 39, 49, 59) pour obtenir l'actif net.

**Filtre** : le bilan inclut les ecritures d'a-nouveau (journal AN/OD ouverture). Le compte de resultat les exclut.

### 3.1. Actif immobilise

#### Immobilisations incorporelles

| Poste | Comptes brut | Comptes amort/deprec | Net = Brut - Amort |
|-------|-------------|---------------------|---------------------|
| Frais d'etablissement | **201** | **2801** | 201 - 2801 |
| Frais de developpement | **203** | **2803, 2903** | 203 - 2803 - 2903 |
| Concessions, brevets, licences | **205** | **2805, 2905** | 205 - 2805 - 2905 |
| Fonds commercial | **206, 207** | **2806, 2807, 2906, 2907** | 206+207 - amort - deprec |
| Autres immobilisations incorporelles | **208** | **2808, 2908** | 208 - 2808 - 2908 |
| Immobilisations incorporelles en cours | **232** | **2932** | 232 - 2932 |
| Avances et acomptes | **237** | — | 237 |

#### Immobilisations corporelles

| Poste | Comptes brut | Comptes amort/deprec | Net = Brut - Amort |
|-------|-------------|---------------------|---------------------|
| Terrains | **211** | **2811, 2911** | 211 - 2811 - 2911 |
| Constructions | **213, 214** | **2813, 2814, 2913, 2914** | brut - amort - deprec |
| Installations techniques, materiel | **215** | **2815, 2915** | 215 - 2815 - 2915 |
| Autres immobilisations corporelles | **218** | **2818, 2918** | 218 - 2818 - 2918 |
| Immobilisations corporelles en cours | **231** | **2931** | 231 - 2931 |
| Avances et acomptes | **238** | — | 238 |

#### Immobilisations financieres

| Poste | Comptes brut | Comptes deprec | Net = Brut - Deprec |
|-------|-------------|----------------|----------------------|
| Participations | **261, 266** | **2961, 2966** | brut - deprec |
| Creances rattachees a des participations | **267** | **2967** | 267 - 2967 |
| Titres immobilises (TIAP + autres) | **271, 272, 273** | **2971, 2972, 2973** | brut - deprec |
| Prets | **274** | **2974** | 274 - 2974 |
| Depots et cautionnements | **275** | **2975** | 275 - 2975 |
| Autres immobilisations financieres | **276, 278** | **2976** | brut - deprec |

**Formule SQL globale Actif immobilise :**
```sql
-- Brut
SUM(debit - credit) WHERE compte ~ '^2[01345678]' AND compte NOT LIKE '28%' AND compte NOT LIKE '29%'
-- Amortissements et depreciations
SUM(credit - debit) WHERE compte LIKE '28%' OR compte LIKE '29%'
-- Net = Brut - Amort - Deprec
```

**Pieges :**
- Le **269** (versements restant a effectuer sur titres non liberes) est a l'actif en negatif (signe inversee). Il diminue les participations.
- Le **109** (actionnaires — capital souscrit non appele) est presente en haut de l'actif, AVANT l'actif immobilise.
- Les **280** (amortissements des immobilisations incorporelles) ont un sous-detail par nature (2801, 2803, 2805, etc.).

### 3.2. Actif circulant

#### Stocks et en-cours

| Poste | Comptes brut | Comptes deprec | Net |
|-------|-------------|----------------|-----|
| Matieres premieres | **31** | **391** | 31 - 391 |
| En-cours de production (biens) | **33** | **393** | 33 - 393 |
| En-cours de production (services) | **34** | **394** | 34 - 394 |
| Produits intermediaires et finis | **35** | **395** | 35 - 395 |
| Marchandises | **37** | **397** | 37 - 397 |

#### Creances

| Poste | Comptes brut | Comptes deprec | Net |
|-------|-------------|----------------|-----|
| Avances et acomptes verses sur commandes | **4091** | — | 4091 |
| Creances clients et comptes rattaches | **411, 413, 416, 417, 418** | **491** | brut - 491 |
| Autres creances | **409** (sauf 4091), **44** (solde debiteur), **4456** (TVA deductible), **4457** (TVA sur factures non parvenues), **46** (debiteurs divers) | **496** | brut - 496 |
| Capital souscrit — appele, non verse | **4562** | — | 4562 |
| Charges constatees d'avance | **486** | — | 486 |

#### Valeurs mobilieres de placement

| Poste | Comptes brut | Comptes deprec | Net |
|-------|-------------|----------------|-----|
| VMP | **50** (hors 509) | **590** | 50 - 590 |

#### Disponibilites

| Poste | Comptes | Notes |
|-------|---------|-------|
| Banques | **512** (solde debiteur) | |
| Caisse | **53** | |
| CCP | **514** | |
| Regies d'avances | **543** | |

**Formule SQL globale Actif circulant :**
```sql
-- Stocks brut
SUM(debit - credit) WHERE compte ~ '^3[134567]'
-- Depreciation stocks
SUM(credit - debit) WHERE compte ~ '^39'
-- Creances brut
SUM(debit - credit) WHERE compte ~ '^4[01]' (detail selon postes)
-- Depreciation creances
SUM(credit - debit) WHERE compte ~ '^49'
-- VMP
SUM(debit - credit) WHERE compte LIKE '50%' AND compte NOT LIKE '509%'
-- Depreciation VMP
SUM(credit - debit) WHERE compte LIKE '590%'
-- Disponibilites
SUM(debit - credit) WHERE compte ~ '^5[1234]' AND compte NOT LIKE '519%'
-- CCA
SUM(debit - credit) WHERE compte LIKE '486%'
```

### 3.3. Passif — Capitaux propres

| Poste | Comptes | Signe |
|-------|---------|-------|
| Capital social | **101** | + (crediteur) |
| Primes d'emission, de fusion, d'apport | **104** | + |
| Ecarts de reevaluation | **105** | + |
| Reserve legale | **1061** | + |
| Reserves statutaires | **1063** | + |
| Reserves reglementees | **1064** | + |
| Autres reserves | **1068** | + |
| Report a nouveau (crediteur) | **110** | + |
| Report a nouveau (debiteur) | **119** | - |
| Resultat de l'exercice (benefice) | **120** | + |
| Resultat de l'exercice (perte) | **129** | - |
| Subventions d'investissement | **13** | + |
| Provisions reglementees | **14** | + |
| Capital souscrit non appele | **109** | - (present en deduction des capitaux propres) |

**Formule SQL :**
```sql
SUM(credit - debit) WHERE compte ~ '^1[0134]' AND compte NOT LIKE '109%'
-- Attention au 109 qui est un actif
- SUM(debit - credit) WHERE compte LIKE '109%'
```

### 3.4. Passif — Provisions pour risques et charges

| Poste | Comptes |
|-------|---------|
| Provisions pour risques | **151** |
| Provisions pour charges | **153, 155, 156, 157, 158** |

**Formule SQL :** `SUM(credit - debit) WHERE compte LIKE '15%'`

### 3.5. Passif — Dettes

#### Dettes financieres

| Poste | Comptes |
|-------|---------|
| Emprunts obligataires | **161** |
| Emprunts aupres des etablissements de credit | **164** |
| Emprunts et dettes financieres divers | **165, 166, 167, 168** |
| Avances et acomptes recus | **4191** |
| Dettes fournisseurs et comptes rattaches | **401, 403, 408** |
| Dettes fiscales et sociales | **42, 43, 44** (solde crediteur), **438, 448** |
| Dettes sur immobilisations | **404** |
| Autres dettes | **45, 46** (crediteurs divers), **467** |
| Produits constates d'avance | **487** |
| Concours bancaires courants | **519** |

**Formule SQL Dettes :**
```sql
-- Emprunts
SUM(credit - debit) WHERE compte ~ '^16[1-8]'
-- Fournisseurs
SUM(credit - debit) WHERE compte ~ '^40[138]'
-- Dettes fiscales et sociales
SUM(credit - debit) WHERE compte ~ '^4[234]' (soldes crediteurs)
-- CBC
SUM(credit - debit) WHERE compte LIKE '519%'
-- PCA
SUM(credit - debit) WHERE compte LIKE '487%'
```

**Controle fondamental :**
```
Total Actif = Total Passif
```

---

## 4. Bilan fonctionnel

**REGLE FONDAMENTALE : Le bilan fonctionnel se fait en VALEURS BRUTES.** Les amortissements et depreciations quittent l'actif pour etre reclasses dans les ressources stables (au passif). Ce reclassement est la difference majeure avec le bilan comptable.

### 4.1. Emplois stables (actif)

| Poste | Comptes | Regle |
|-------|---------|-------|
| Immobilisations incorporelles | **20** | Valeur BRUTE |
| Immobilisations corporelles | **21, 22, 23** | Valeur BRUTE |
| Immobilisations financieres | **26, 27** | Valeur BRUTE |
| Charges a repartir sur plusieurs exercices | **481** | Si existant |

**Formule SQL Emplois stables :**
```sql
SUM(debit - credit) WHERE compte ~ '^2[0-7]'
    AND compte NOT LIKE '28%'
    AND compte NOT LIKE '29%'
```

Attention : on prend les immobilisations en BRUT, donc on N'EXCLUT PAS les amortissements dans le calcul de l'actif. On prend directement les soldes des comptes 20-27.

### 4.2. Ressources stables (passif)

| Poste | Comptes | Regle |
|-------|---------|-------|
| Capitaux propres | **10** (sauf 109), **11, 12, 13, 14** | Idem bilan comptable |
| Amortissements et depreciations | **28, 29, 39, 49, 59** | **RECLASSES ici** depuis l'actif |
| Provisions pour risques et charges | **15** | Idem bilan comptable |
| Dettes financieres (> 1 an) | **16** (sauf 169), **17** | Part a + 1 an |

**Formule SQL Ressources stables :**
```sql
-- Capitaux propres
SUM(credit - debit) WHERE compte ~ '^1[0-4]' AND compte NOT LIKE '109%'
-- Amortissements et depreciations (RECLASSES)
+ SUM(credit - debit) WHERE compte LIKE '28%'
+ SUM(credit - debit) WHERE compte LIKE '29%'
+ SUM(credit - debit) WHERE compte LIKE '39%'
+ SUM(credit - debit) WHERE compte LIKE '49%'
+ SUM(credit - debit) WHERE compte LIKE '59%'
-- Provisions
+ SUM(credit - debit) WHERE compte LIKE '15%'
-- Dettes financieres
+ SUM(credit - debit) WHERE compte ~ '^16' AND compte NOT LIKE '169%'
+ SUM(credit - debit) WHERE compte LIKE '17%'
```

### 4.3. FRNG — Fonds de Roulement Net Global

```
FRNG = Ressources stables - Emplois stables
```

- **FRNG > 0** : les ressources stables financent les emplois stables ET degagent un excedent pour financer le cycle d'exploitation.
- **FRNG < 0** : les emplois stables ne sont pas entierement finances par des ressources stables. Situation preoccupante.

### 4.4. Actif circulant d'exploitation (ACE)

| Poste | Comptes | Regle |
|-------|---------|-------|
| Stocks et en-cours | **31, 33, 34, 35, 37** | Valeur BRUTE |
| Avances et acomptes verses | **4091** | |
| Creances clients | **411, 413, 416, 417, 418** | Valeur BRUTE |
| Autres creances d'exploitation | **4456** (TVA deductible), **4457**, **44586** (credit TVA) | |
| Charges constatees d'avance d'exploitation | **486** (part exploitation) | |

**Formule SQL ACE :**
```sql
-- Stocks brut
SUM(debit - credit) WHERE compte ~ '^3[1345]' OR compte LIKE '37%'
-- Creances clients brut
+ SUM(debit - credit) WHERE compte ~ '^41[1-8]'
-- Avances fournisseurs
+ SUM(debit - credit) WHERE compte LIKE '4091%'
-- TVA deductible et assimiles
+ SUM(debit - credit) WHERE compte ~ '^445[6-8]'
-- CCA exploitation
+ SUM(debit - credit) WHERE compte LIKE '486%'
```

### 4.5. Passif circulant d'exploitation (PCE)

| Poste | Comptes | Regle |
|-------|---------|-------|
| Avances et acomptes recus | **4191** | |
| Dettes fournisseurs d'exploitation | **401, 403, 408** | |
| Dettes fiscales et sociales | **42, 43, 44** (solde crediteur hors IS), **438** | |
| Produits constates d'avance d'exploitation | **487** (part exploitation) | |

**Formule SQL PCE :**
```sql
SUM(credit - debit) WHERE compte ~ '^40[138]'
+ SUM(credit - debit) WHERE compte LIKE '4191%'
+ SUM(credit - debit) WHERE compte ~ '^4[23]'
+ SUM(credit - debit) WHERE compte ~ '^44' (hors 444 associes et IS)
+ SUM(credit - debit) WHERE compte LIKE '487%'
```

### 4.6. BFR d'exploitation

```
BFR d'exploitation = Actif circulant d'exploitation - Passif circulant d'exploitation
```

### 4.7. Actif circulant hors exploitation (ACHE)

| Poste | Comptes |
|-------|---------|
| Capital souscrit, appele, non verse | **4562** |
| Creances diverses (hors exploitation) | **44** (solde debiteur hors TVA deductible), **46** (debiteurs divers), **467** |
| VMP | **50** (hors 509) |
| Charges constatees d'avance hors exploitation | **486** (part hors exploitation) |

### 4.8. Passif circulant hors exploitation (PCHE)

| Poste | Comptes |
|-------|---------|
| Dettes sur immobilisations | **404, 405** |
| Dettes fiscales (IS) | **444** |
| Dettes diverses | **45, 46** (crediteurs divers), **467** (crediteur) |
| Produits constates d'avance hors exploitation | **487** (part hors exploitation) |

### 4.9. BFR hors exploitation

```
BFR hors exploitation = Actif circulant hors exploitation - Passif circulant hors exploitation
```

### 4.10. BFR total

```
BFR total = BFR d'exploitation + BFR hors exploitation
```

### 4.11. Tresorerie

| Poste | Comptes |
|-------|---------|
| Tresorerie active | **512** (solde debiteur), **514**, **53**, **54** (hors 543 selon cas) |
| Tresorerie passive | **519** (concours bancaires courants), **512** (solde crediteur si decouvert) |

```
Tresorerie nette = Tresorerie active - Tresorerie passive
```

### 4.12. Equation fondamentale du bilan fonctionnel

```
Tresorerie nette = FRNG - BFR total
```

Ou de maniere equivalente :
```
FRNG = BFR total + Tresorerie nette
```

**Cette egalite doit TOUJOURS etre verifiee.** C'est le controle de coherence du bilan fonctionnel.

**Pieges du bilan fonctionnel :**
- Les **effets escomptes non echus (EENE)** doivent etre reintegres : +ACE (creances clients) et +tresorerie passive. L'information est en hors-bilan (compte 8 ou annexe).
- Le **credit-bail** doit etre reintegre : +emplois stables (valeur d'origine) et +ressources stables (dette equivalente). Les loyers payes sont reclasses en amortissement + charges financieres.
- Les **ecarts de conversion actif** (476) sont a reclasser selon leur nature.
- Les **ecarts de conversion passif** (477) idem.
- Les **interets courus non echus (ICNE)** sur emprunts (1688, 5181) sont du passif circulant hors exploitation, pas des ressources stables.
- Les **primes de remboursement des obligations** (169) sont a deduire des emprunts obligataires.

---

## 5. Resultat differentiel — Seuil de rentabilite

Le resultat differentiel repose sur la distinction entre charges variables et charges fixes. Cette distinction est stockee dans `pcg_analytique.nature_defaut` et peut etre surchargee par `profil_nature_charge` et `entite_override_charge`.

### 5.1. Chiffre d'affaires

```
CA = Ventes de marchandises + Production vendue
   = SUM(credit - debit) WHERE compte ~ '^70[1-8]'
   - SUM(credit - debit) WHERE compte ~ '^709'
```

### 5.2. Charges variables (par defaut)

Les charges variables sont celles qui varient proportionnellement au chiffre d'affaires. Classification par defaut :

| Comptes | Libelle | Nature |
|---------|---------|--------|
| **601** | Achats de matieres premieres | Variable |
| **602** | Achats d'autres approvisionnements | Variable |
| **604** | Achats d'etudes et prestations | Variable |
| **605** | Achats de materiels et travaux | Variable |
| **606** | Achats non stockes | Variable (sauf 6061 fournitures non stockables : mixte) |
| **607** | Achats de marchandises | Variable |
| **6031, 6032, 6037** | Variations de stocks | Variable |
| **6091-6098** | RRR obtenus | Variable (en deduction) |
| **611** | Sous-traitance generale | Variable |
| **6132** | Locations mobilieres (vehicules, engins) | Variable (transport/BTP) |
| **6152** | Entretien et reparations sur biens mobiliers | Mixte (part variable estimee a 60%) |
| **6161** | Assurances multirisques | Fixe |
| **6162** | Assurances materiels de transport | Variable (transport) |
| **6226** | Honoraires | Fixe |
| **623** | Publicite, publications | Variable |
| **6241** | Transports sur achats | Variable |
| **6242** | Transports sur ventes | Variable |
| **6243** | Transports entre etablissements | Variable |
| **6247** | Transports collectifs du personnel | Fixe |
| **625** | Deplacements, missions, receptions | Mixte |
| **6261** | Frais d'affranchissement | Variable |
| **6262** | Frais de telecommunications | Fixe |
| **626** (hors 6261, 6262) | Frais postaux et telecom | Fixe |
| **627** | Services bancaires | Fixe |
| **63** | Impots et taxes | Fixe (sauf taxe sur CA) |
| **641** | Remunerations du personnel | Fixe |
| **645** | Charges de securite sociale | Fixe |
| **647** | Autres charges sociales | Fixe |
| **648** | Autres charges de personnel | Fixe |
| **651** | Redevances | Fixe |
| **654** | Pertes sur creances irrecouvrables | Variable |
| **661** | Charges d'interets | Fixe |
| **681** | Dotations aux amortissements | Fixe |

**Note importante** : la classification V/F depend fortement du secteur d'activite. Les overrides par profil sectoriel (`profil_nature_charge`) et par entite (`entite_override_charge`) priment sur la classification par defaut.

### 5.3. Charges fixes

Toutes les charges non classees "variable" sont considerees comme fixes par defaut :
- Loyers et charges locatives (613, hors 6132 si transport)
- Assurances (616, sauf 6162 transport)
- Personnel (64)
- Impots et taxes (63)
- Honoraires (6226)
- Dotations aux amortissements (681)
- Charges financieres (66)

### 5.4. Formules du resultat differentiel

```
Marge sur Couts Variables (MCV) = CA - Total charges variables
```

```
Taux de MCV = MCV / CA
```

```
Seuil de rentabilite (en euros) = Charges fixes / Taux de MCV
```

```
Point mort (en jours) = (Seuil de rentabilite / CA) x 365
```

```
Marge de securite = CA - Seuil de rentabilite
```

```
Indice de securite = Marge de securite / CA = 1 - (Seuil de rentabilite / CA)
```

```
Levier operationnel = MCV / Resultat courant
```

**Formule SQL :**
```sql
-- Charges variables : jointure avec pcg_analytique + overrides
SELECT
    SUM(CASE WHEN nature_finale = 'variable' THEN montant END) AS charges_variables,
    SUM(CASE WHEN nature_finale = 'fixe' THEN montant END) AS charges_fixes
FROM fec_ecriture e
JOIN resolve_nature(e.compte_num, e.entite_id) n ON true
WHERE e.compte_num ~ '^[67]'
```

**Pieges :**
- Le seuil de rentabilite suppose une **linearite** des charges variables, ce qui est une approximation.
- Les charges **mixtes** (partiellement variables, partiellement fixes) doivent etre ventilees. Ratio par defaut dans `profil_nature_charge`.
- Le point mort n'a de sens que si le CA est reparti de maniere **homogene** dans l'annee. Pour les activites saisonnieres (transport scolaire, agroalimentaire), il faut ajuster avec la courbe de CA mensualisee.
- Attention : les **produits financiers et exceptionnels** ne sont generalement pas inclus dans le CA pour le calcul du seuil de rentabilite. Seul le CA d'exploitation est pris en compte.

---

## 6. Ratios financiers

### 6.1. Ratios de liquidite

#### Ratio de liquidite generale

```
Liquidite generale = Actif circulant (net) / Dettes a court terme (< 1 an)
```

| Numerateur | Denominateur |
|------------|-------------|
| Stocks + Creances + VMP + Disponibilites (nets de deprec) | Dettes fournisseurs + Dettes fiscales/sociales + CBC + Autres dettes CT |
| Comptes : 3x - 39x + 4x (debiteur) + 486 + 50x - 59x + 51x/53x/54x | Comptes : 40x + 42x + 43x + 44x (crediteur) + 519 + 487 |

**Seuils de reference :**
- \> 1,5 : Bonne liquidite
- 1,0 a 1,5 : Correcte
- < 1,0 : **ALERTE** — risque de cessation de paiement

#### Ratio de liquidite reduite (acid test)

```
Liquidite reduite = (Creances + VMP + Disponibilites) / Dettes a court terme
```

Identique a la liquidite generale, mais **sans les stocks**.

**Seuils de reference :**
- \> 1,0 : Bonne
- 0,5 a 1,0 : Correcte
- < 0,5 : **ALERTE**

#### Ratio de liquidite immediate (cash ratio)

```
Liquidite immediate = Disponibilites / Dettes a court terme
```

| Numerateur | Denominateur |
|------------|-------------|
| 512 (debiteur) + 514 + 53 + 54 | Idem dettes CT |

**Seuils de reference :**
- \> 0,3 : Confortable
- 0,1 a 0,3 : Correcte
- < 0,1 : **ALERTE** — tension de tresorerie

---

### 6.2. Ratios de solvabilite

#### Taux d'endettement

```
Taux d'endettement = Total dettes / Total passif
```

Ou en variante plus utilisee :
```
Taux d'endettement = Dettes financieres / Capitaux propres
```

| Numerateur | Denominateur |
|------------|-------------|
| Comptes 16 + 17 + 519 | Comptes 10 (sauf 109) + 11 + 12 + 13 + 14 |

**Seuils de reference :**
- < 1,0 : Solvable (dettes < capitaux propres)
- 1,0 a 2,0 : Endette mais acceptable
- \> 2,0 : **ALERTE** — surendettement

#### Autonomie financiere

```
Autonomie financiere = Capitaux propres / Total passif
```

**Seuils de reference :**
- \> 33% : Autonome (regle du tiers)
- 20% a 33% : Faible autonomie
- < 20% : **ALERTE**

#### Capacite de remboursement

```
Capacite de remboursement = Dettes financieres / CAF
```

Exprime le nombre d'annees necessaires pour rembourser les dettes avec la CAF.

**Seuils de reference :**
- < 3 ans : Excellent
- 3 a 5 ans : Correct
- \> 5 ans : **ALERTE** — capacite de remboursement tendue
- \> 8 ans : **CRITIQUE**

#### Taux de couverture des interets

```
Couverture des interets = EBE / Charges d'interets (661)
```

**Seuils de reference :**
- \> 5 : Tres confortable
- 3 a 5 : Correct
- < 3 : **ALERTE**
- < 1 : **CRITIQUE** — l'EBE ne couvre meme pas les interets

---

### 6.3. Ratios de rentabilite

#### Rentabilite economique (ROCE — Return On Capital Employed)

```
ROCE = Resultat d'exploitation / (Capitaux propres + Dettes financieres)
```

Ou en variante :
```
ROCE = Resultat d'exploitation (1 - taux IS) / Actif economique
```

Avec : `Actif economique = Immobilisations nettes + BFR`

| Numerateur | Denominateur |
|------------|-------------|
| Rex (calcul SIG section 1.5) | (10-14 sauf 109) + 12 + 16 + 17 |

**Seuils de reference :**
- \> 15% : Excellente performance
- 10% a 15% : Bonne
- 5% a 10% : Moyenne
- < 5% : **ALERTE** — sous-performance

#### Rentabilite financiere (ROE — Return On Equity)

```
ROE = Resultat net / Capitaux propres
```

| Numerateur | Denominateur |
|------------|-------------|
| Resultat net (compte 12) | 10 (sauf 109) + 11 + 12 + 13 + 14 |

**Seuils de reference :**
- \> 15% : Tres bonne
- 8% a 15% : Bonne
- < 8% : Faible
- Negative : **ALERTE** — destruction de valeur

#### Rentabilite commerciale (marge nette)

```
Marge nette = Resultat net / CA HT
```

**Seuils de reference (varient fortement selon le secteur) :**
- Services : 5% a 15%
- Transport : 2% a 8%
- Industrie/transformation : 3% a 10%

#### Taux de marge brute

```
Taux de marge brute = Marge commerciale / Ventes de marchandises (707)
```

ou

```
Taux de marge brute = VA / CA HT
```

#### Taux d'EBE (marge operationnelle)

```
Taux d'EBE = EBE / CA HT
```

**Seuils de reference :**
- \> 20% : Tres performant
- 10% a 20% : Bon
- 5% a 10% : Moyen
- < 5% : **ALERTE** — marges insuffisantes

---

### 6.4. Ratios de rotation et d'activite

#### Rotation des stocks

```
Rotation des stocks = Cout d'achat des marchandises vendues / Stock moyen
```

Ou :
```
Rotation des stocks = Achats consommes / Stock moyen
```

Avec :
- Stock moyen = (Stock debut + Stock fin) / 2
- Achats consommes = Achats (601+602+607) + Variation de stocks (6031+6032+6037)

#### Delai de rotation des stocks (en jours)

```
Delai de rotation des stocks = (Stock moyen / Cout d'achat des marchandises vendues) x 365
```

Ou par type de stock :

**Marchandises :**
```
Delai stocks marchandises = (Stock moyen 37 / (607 + 6037)) x 365
```

**Matieres premieres :**
```
Delai stocks matieres = (Stock moyen 31 / (601 + 6031)) x 365
```

**Produits finis :**
```
Delai stocks produits finis = (Stock moyen 35 / Cout de production des produits vendus) x 365
```

**Seuils de reference :**
- Transport : N/A ou < 15 jours (pieces detachees)
- Industrie/transformation : 15 a 45 jours (matieres perissables)
- Commerce/marchandises : 30 a 90 jours

#### Delai de reglement clients (DSO — Days Sales Outstanding)

```
Delai clients = (Creances clients TTC / CA TTC) x 365
```

| Numerateur | Denominateur |
|------------|-------------|
| 411 + 413 + 416 + 417 + 418 - 4191 (avances recues) | CA HT x (1 + taux TVA moyen) |

**Seuils de reference :**
- < 30 jours : Excellent
- 30 a 60 jours : Correct (LME)
- 60 a 90 jours : **ALERTE**
- \> 90 jours : **CRITIQUE**

Note : la loi LME limite les delais de paiement inter-entreprises a **60 jours** date de facture ou **45 jours** fin de mois.

#### Delai de reglement fournisseurs (DPO — Days Payable Outstanding)

```
Delai fournisseurs = (Dettes fournisseurs TTC / Achats TTC) x 365
```

| Numerateur | Denominateur |
|------------|-------------|
| 401 + 403 + 408 - 4091 (avances versees) | (601+602+604+605+606+607+608+61+62) x (1 + taux TVA moyen) |

**Seuils de reference :**
- 30 a 60 jours : Correct
- < 30 jours : Paie trop vite (ou escompte)
- \> 60 jours : **ALERTE** si non negocie

#### BFR en jours de CA

```
BFR en jours de CA = (BFR / CA HT) x 365
```

**Seuils de reference :**
- < 30 jours : Faible BFR, bonne gestion
- 30 a 60 jours : Correct
- 60 a 90 jours : Eleve
- \> 90 jours : **ALERTE**

---

### 6.5. Ratios de structure

#### Taux d'investissement

```
Taux d'investissement = Investissements de l'exercice / VA
```

Les investissements = augmentation des comptes 20-27 (hors financier) sur l'exercice, ou flux du tableau de financement.

#### Taux d'amortissement (vetuste)

```
Taux d'amortissement = Amortissements cumules / Immobilisations brutes amortissables
```

| Numerateur | Denominateur |
|------------|-------------|
| 28 (hors 2961-2976) | 20+21+22+23 (hors terrains 211 et immo en cours 23) |

**Seuils de reference :**
- < 50% : Outil de production recent
- 50% a 70% : Intermediaire
- \> 70% : **ALERTE** — outil vieillissant, investissements a prevoir

#### Intensite capitalistique

```
Intensite capitalistique = Immobilisations nettes / Total actif net
```

---

### 6.6. Ratios specifiques sectoriels

#### Transport

**Taux de sous-traitance :**
```
Taux de sous-traitance = Sous-traitance (611) / CA HT
```

Seuils : < 20% = exploitation propre / > 40% = dependance sous-traitance

**Cout au km :**
```
Cout au km = Total charges d'exploitation / Kilometres parcourus
```

Note : les km parcourus ne sont pas dans la comptabilite. Donnee extra-comptable a saisir.

**Charges de carburant / CA :**
```
Ratio carburant = (6061 ou 60622 carburants) / CA HT
```

Seuils transport : 8% a 15% du CA

**Charges de personnel / CA :**
```
Ratio personnel = 64 / CA HT
```

Seuils transport : 35% a 50% du CA

**Cout d'entretien / CA :**
```
Ratio entretien = (6152 + 6155) / CA HT
```

Seuils : 3% a 8% du CA

#### Industrie / transformation

**Taux de matieres premieres :**
```
Taux MP = (601 + 602 + 6031 + 6032) / CA HT
```

Seuils transformation agricole : 30% a 50% du CA

**Rendement matiere :**
```
Rendement matiere = Production vendue (701-706) / Consommation matieres (601+602+6031+6032)
```

Donnee en coefficient. > 2 = bon rendement.

**Productivite par salarie :**
```
Productivite = CA HT / Effectif moyen
```

Ou :
```
VA par salarie = VA / Effectif moyen
```

Note : l'effectif moyen n'est pas directement disponible en comptabilite. Il provient de la DSN ou des etats annexes.

#### Societe mere / holding

**Rendement des participations :**
```
Rendement participations = Produits de participations (761) / Titres de participation (261)
```

**Taux de distribution :**
```
Taux de distribution = Dividendes verses (457 variation) / Resultat net N-1
```

---

### 6.7. Resume des 20+ ratios

| # | Ratio | Formule synthetique | Seuil d'alerte |
|---|-------|-------------------|----------------|
| 1 | Liquidite generale | AC net / DCT | < 1,0 |
| 2 | Liquidite reduite | (AC net - Stocks) / DCT | < 0,5 |
| 3 | Liquidite immediate | Dispo / DCT | < 0,1 |
| 4 | Taux d'endettement | Dettes financieres / CP | > 2,0 |
| 5 | Autonomie financiere | CP / Total passif | < 20% |
| 6 | Capacite de remboursement | Dettes fin. / CAF | > 5 ans |
| 7 | Couverture des interets | EBE / 661 | < 3 |
| 8 | ROCE | Rex / (CP + Dettes fin.) | < 5% |
| 9 | ROE | Resultat net / CP | < 8% |
| 10 | Marge nette | Resultat net / CA | < 2% |
| 11 | Taux marge brute | Marge comm. / 707 | Sectoriel |
| 12 | Taux d'EBE | EBE / CA | < 5% |
| 13 | Rotation stocks | Achats conso / Stock moy | Sectoriel |
| 14 | Delai stocks (j) | Stock moy / Achats conso x 365 | > 90j |
| 15 | Delai clients (j) | Creances TTC / CA TTC x 365 | > 60j |
| 16 | Delai fournisseurs (j) | Dettes fourn. TTC / Achats TTC x 365 | > 60j |
| 17 | BFR en jours de CA | BFR / CA x 365 | > 90j |
| 18 | Taux d'investissement | Investissements / VA | Sectoriel |
| 19 | Taux d'amortissement (vetuste) | Amort cumules / Immo brutes | > 70% |
| 20 | Intensite capitalistique | Immo nettes / Total actif | Sectoriel |
| 21 | Taux sous-traitance (transport) | 611 / CA | > 40% |
| 22 | Ratio carburant (transport) | 6061 / CA | > 15% |
| 23 | Taux MP (agro) | (601+602+6031+6032) / CA | > 50% |
| 24 | Productivite par salarie | CA / Effectif | Sectoriel |
| 25 | Rendement participations (holding) | 761 / 261 | < 3% |

---

## 7. Consolidation groupe

### 7.1. Perimetre

Exemple type : un groupe compose d'une societe mere et de plusieurs filiales operationnelles.

La consolidation niveau 1 est une **agregation simple** avec elimination des flux intra-groupe. Pas de consolidation legale IFRS (hors perimetre de ce referentiel).

### 7.2. Agregation

```
Agregation = SUM des balances des 4 entites
```

Pour chaque compte PCG :
```sql
SELECT
    compte_num,
    SUM(debit) AS debit_total,
    SUM(credit) AS credit_total,
    SUM(debit - credit) AS solde_total
FROM fec_ecriture
WHERE entite_id IN (entite_1, entite_2, entite_3, entite_4)
GROUP BY compte_num
```

### 7.3. Elimination des flux intra-groupe

Les flux intra-groupe sont des operations entre les 4 structures qui doivent etre annulees en consolidation pour ne pas gonfler artificiellement les chiffres du groupe.

#### Comptes concernes

| Compte | Libelle | Traitement |
|--------|---------|------------|
| **451** | Groupe et associes | Elimination reciproque |
| **455** | Associes — comptes courants | Elimination reciproque |
| **267** | Creances rattachees a des participations | Elimination reciproque |
| **17** | Dettes rattachees a des participations | Elimination reciproque |
| **411** + **401** | Clients / Fournisseurs intra-groupe | Detection par `comp_aux_num` |
| **761** + **661** | Produits/charges financieres intra-groupe (interets comptes courants) | Elimination reciproque |
| **70x** + **60x/61x/62x** | CA / Achats intra-groupe | Detection par `comp_aux_num` |

#### Detection automatique

La detection des flux intra-groupe s'appuie sur le champ `comp_aux_num` (numero de compte auxiliaire) dans `fec_ecriture` :

```sql
-- Identifier les ecritures intra-groupe
SELECT *
FROM fec_ecriture e1
WHERE e1.comp_aux_num IN (
    SELECT identifiant_comptable
    FROM entite
    WHERE id != e1.entite_id
)
```

Le champ `comp_aux_num` contient generalement le SIREN ou un identifiant unique du tiers. Si la societe mere facture une filiale, l'ecriture de la mere aura le SIREN de la filiale dans `comp_aux_num`.

#### Controle de reciprocite

Pour chaque flux intra-groupe, il faut verifier que les deux entites ont enregistre l'operation pour le meme montant :

```sql
-- Controle de reciprocite des comptes courants 451/455
SELECT
    e1.entite_id AS entite_1,
    e2.entite_id AS entite_2,
    SUM(e1.debit - e1.credit) AS solde_entite_1,
    SUM(e2.credit - e2.debit) AS solde_entite_2,
    ABS(SUM(e1.debit - e1.credit) - SUM(e2.credit - e2.debit)) AS ecart
FROM fec_ecriture e1
JOIN fec_ecriture e2
    ON e1.comp_aux_num = (SELECT siren FROM entite WHERE id = e2.entite_id)
    AND e2.comp_aux_num = (SELECT siren FROM entite WHERE id = e1.entite_id)
WHERE e1.compte_num LIKE '451%' OR e1.compte_num LIKE '455%'
GROUP BY e1.entite_id, e2.entite_id
HAVING ABS(SUM(e1.debit - e1.credit) - SUM(e2.credit - e2.debit)) > 0.01
```

Un ecart > 0 signale une **anomalie de reciprocite** a investiguer (facture non enregistree, ecart de date, erreur de saisie).

### 7.4. Retraitements de consolidation

| Retraitement | Description | Impact |
|---|---|---|
| Elimination CA intra-groupe | Le CA facture entre entites est annule | CA consolide diminue |
| Elimination achats intra-groupe | Les achats correspondants sont annules | Charges consolide diminuent |
| Elimination dividendes intra-groupe | Les dividendes verses par les filiales a la holding (761) sont annules | Produits financiers consolides diminuent |
| Elimination interets intra-groupe | Les interets sur comptes courants (661/761) sont annules | Resultat financier ajuste |
| Elimination creances/dettes reciproques | Les 451, 455, 411/401 intra-groupe s'annulent | Bilan consolide degonfle |

### 7.5. Formule du resultat consolide

```
Resultat consolide = SUM(Resultats individuels des 4 entites)
                   - Dividendes intra-groupe (761 intra)
                   - Marges intra-groupe sur stocks (si significatif)
```

**Pieges de la consolidation :**
- Les **dividendes** des filiales vers la holding sont des produits pour la holding mais pas pour le groupe. Il faut les eliminer.
- Les **interets sur comptes courants** sont une charge pour la filiale et un produit pour la holding. Il faut les eliminer des deux cotes.
- Les **prestations de management** (management fees) de la holding vers les filiales sont un CA pour la holding et une charge pour les filiales. Elimination reciproque.
- La **marge intra-groupe sur stocks** : si une entite vend des marchandises a une autre avec marge, et que ces marchandises sont encore en stock chez l'acheteur a la cloture, la marge doit etre eliminee.
- Le **resultat de cession intra-groupe** : si une entite cede un actif a une autre entite du groupe, la plus-value (775-675) doit etre eliminee.

---

## 8. Tableau de financement (PCG)

Le tableau de financement (systeme developpe PCG, Art. 532-8) analyse les flux de ressources et d'emplois de l'exercice. Il se decompose en deux parties :
- **Partie 1** : Variation du Fonds de Roulement Net Global (FRNG) — flux stables
- **Partie 2** : Variation du Besoin en Fonds de Roulement (BFR) et de la tresorerie — flux cycliques

**Equation de controle fondamentale :**
```
Variation FRNG = Variation BFR + Variation Tresorerie nette
```

### 8.1. Partie 1 — Tableau des emplois et ressources (variation du FRNG)

#### 8.1.1. Ressources durables de l'exercice

```
Total Ressources durables = CAF
                          + Cessions d'immobilisations incorporelles et corporelles
                          + Cessions d'immobilisations financieres
                          + Augmentation de capital ou apports
                          + Augmentation des autres capitaux propres (subventions d'investissement recues)
                          + Augmentation des dettes financieres (emprunts nouveaux)
```

| Signe | Comptes | Libelle | Methode de calcul |
|-------|---------|---------|-------------------|
| + | | CAF (cf. section 1.9) | Resultat + DAP - RAP - PCEA + VCEAC (methode additive) |
| + | **775** | Prix de cession des immobilisations corporelles et incorporelles cedees | Credit du 775 |
| + | **775** (financier) | Prix de cession des immobilisations financieres cedees | Credit du 775 pour les titres (cf. 271, 272, 273, 274) |
| + | **101, 104, 108** | Augmentation de capital ou apports | Variation credit N vs N-1 |
| + | **13** | Subventions d'investissement recues dans l'exercice | Variation credit N vs N-1 (hors quote-part viree au resultat) |
| + | **16** (sauf 169) | Emprunts nouveaux contractes dans l'exercice | Flux credit 16 (hors ICNE 1688 et remboursements) |

**Formule SQL Ressources durables :**
```sql
-- CAF (methode additive, cf. section 1.9)
Resultat_net
+ SUM(debit - credit) WHERE compte LIKE '681%'    -- DAP exploitation
+ SUM(debit - credit) WHERE compte LIKE '686%'    -- DAP financieres
+ SUM(debit - credit) WHERE compte LIKE '687%'    -- DAP exceptionnelles
- SUM(credit - debit) WHERE compte LIKE '781%'    -- RAP exploitation
- SUM(credit - debit) WHERE compte LIKE '786%'    -- RAP financieres
- SUM(credit - debit) WHERE compte LIKE '787%'    -- RAP exceptionnelles
+ SUM(debit - credit) WHERE compte LIKE '675%'    -- VCEAC
- SUM(credit - debit) WHERE compte LIKE '775%'    -- PCEA
- SUM(credit - debit) WHERE compte LIKE '777%'    -- Quote-part subv. inv. viree au resultat
+ SUM(credit - debit) WHERE compte LIKE '687%' AND nature = 'provision_reglementee'  -- si applicable

-- Cessions (prix de cession = PCEA deja retiree de la CAF, donc on la rajoute ici)
+ SUM(credit - debit) WHERE compte LIKE '775%'    -- PCEA total

-- Augmentation de capital
+ (Solde_credit_N - Solde_credit_N1) WHERE compte ~ '^10[148]' AND variation > 0

-- Subventions d'investissement recues
+ Flux_credit WHERE compte LIKE '13%' (hors 777 deja en CAF)

-- Emprunts nouveaux
+ Flux_credit WHERE compte ~ '^16' AND compte NOT LIKE '169%' AND compte NOT LIKE '1688%'
```

**Pieges et exceptions :**
- La **CAF** est la principale ressource durable. Elle est calculee par la methode additive (cf. section 1.9). Ne pas confondre avec l'EBE.
- Les **cessions d'immobilisations** (775) sont deja retirees de la CAF (PCEA). Il faut les rajouter en totalite comme ressource a part. La CAF exclut le PCEA mais le tableau de financement le reclasse en ressource.
- La **VCEAC** (675) est rajoutee dans la CAF (methode additive) car c'est une charge calculee, non decaissee. Le flux reel de la cession est le 775.
- Les **emprunts nouveaux** correspondent aux flux crediteurs du compte 16, pas au solde. Il faut isoler les nouveaux tirages des remboursements.
- Les **ICNE** (1688 — interets courus non echus) sont exclus car ils ne representent pas un flux de tresorerie.
- La **quote-part de subvention d'investissement viree au resultat** (777) est deja dans la CAF (en negatif). La ressource ici est la subvention recue (flux credit 13), pas la quote-part viree.

---

#### 8.1.2. Emplois stables de l'exercice

```
Total Emplois stables = Acquisitions d'immobilisations incorporelles
                      + Acquisitions d'immobilisations corporelles
                      + Acquisitions d'immobilisations financieres
                      + Charges a repartir (si existantes)
                      + Remboursements de dettes financieres
                      + Distributions mises en paiement (dividendes)
```

| Signe | Comptes | Libelle | Methode de calcul |
|-------|---------|---------|-------------------|
| + | **20** | Acquisitions d'immobilisations incorporelles | Flux debit 20 (hors virements internes) |
| + | **21, 22, 23** | Acquisitions d'immobilisations corporelles | Flux debit 21+22+23 |
| + | **26, 27** | Acquisitions d'immobilisations financieres | Flux debit 26+27 |
| + | **481** | Charges a repartir sur plusieurs exercices | Flux debit 481 (si utilise) |
| + | **16** (sauf 169) | Remboursements d'emprunts | Flux debit 16 (hors ICNE 1688) |
| + | **457** | Distributions (dividendes) mises en paiement | Flux debit 457 ou variation 12/11 → 457 |

**Formule SQL Emplois stables :**
```sql
-- Acquisitions d'immobilisations incorporelles
+ Flux_debit WHERE compte LIKE '20%'
-- Acquisitions d'immobilisations corporelles
+ Flux_debit WHERE compte ~ '^2[123]'
-- Acquisitions d'immobilisations financieres
+ Flux_debit WHERE compte ~ '^2[67]'
-- Charges a repartir
+ Flux_debit WHERE compte LIKE '481%'
-- Remboursements d'emprunts
+ Flux_debit WHERE compte ~ '^16' AND compte NOT LIKE '169%' AND compte NOT LIKE '1688%'
-- Distributions
+ Flux_debit WHERE compte LIKE '457%'
```

**Pieges et exceptions :**
- Les **acquisitions** doivent etre prises en flux (mouvements debiteurs), pas en variation de solde, car les cessions diminuent aussi le solde.
- La **production immobilisee** (72) ne genere pas de flux de tresorerie. Mais elle augmente le debit des comptes d'immobilisation. Il faut soit l'exclure des acquisitions, soit la neutraliser (elle est deja dans la CAF via la production de l'exercice).
- Les **remboursements d'emprunts** sont les flux debiteurs du 16. Ne pas confondre avec les ICNE (1688) qui sont des charges a payer.
- Les **dividendes** a retenir sont ceux mis en paiement dans l'exercice (mouvement au credit du 457 puis au debit a la mise en paiement). En pratique, c'est le dividende N-1 paye en N.
- Le **169** (primes de remboursement des obligations) est exclu du 16 dans le calcul.

---

#### 8.1.3. Variation du FRNG

```
Variation du FRNG = Total Ressources durables - Total Emplois stables
```

- **Variation > 0** : le FRNG augmente, les ressources durables degagees dans l'exercice sont superieures aux emplois stables. Situation favorable.
- **Variation < 0** : le FRNG diminue, les investissements et remboursements ont absorbe plus que les ressources generees.

---

### 8.2. Partie 2 — Variation du BFR et de la tresorerie

La partie 2 analyse la variation des postes du bas de bilan entre N et N-1.

#### 8.2.1. Variation du BFR d'exploitation

```
Variation BFR exploitation = Variation Actif circulant d'exploitation - Variation Passif circulant d'exploitation
```

| Poste (Besoins : augmentation actif / diminution passif) | Comptes | Calcul |
|--------------------------------------------------------|---------|--------|
| Variation des stocks et en-cours | **31, 33, 34, 35, 37** | Solde N - Solde N-1 |
| Variation des avances et acomptes verses (exploitation) | **4091** | Solde N - Solde N-1 |
| Variation des creances clients et comptes rattaches | **411, 413, 416, 417, 418** | Solde N - Solde N-1 |
| Variation des autres creances d'exploitation | **4456, 4457, 44586** | Solde N - Solde N-1 |
| Variation des charges constatees d'avance (exploitation) | **486** (part exploitation) | Solde N - Solde N-1 |

| Poste (Degagements : augmentation passif / diminution actif) | Comptes | Calcul |
|-------------------------------------------------------------|---------|--------|
| Variation des avances et acomptes recus | **4191** | Solde N - Solde N-1 |
| Variation des dettes fournisseurs d'exploitation | **401, 403, 408** | Solde N - Solde N-1 |
| Variation des dettes fiscales et sociales | **42, 43, 44** (hors IS) | Solde N - Solde N-1 |
| Variation des produits constates d'avance (exploitation) | **487** (part exploitation) | Solde N - Solde N-1 |

**Formule SQL :**
```sql
-- Variation ACE (Besoins)
(SUM(debit_N - credit_N) - SUM(debit_N1 - credit_N1)) WHERE compte ~ '^3[1345]' OR compte LIKE '37%'
+ (Solde_debiteur_N - Solde_debiteur_N1) WHERE compte LIKE '4091%'
+ (Solde_debiteur_N - Solde_debiteur_N1) WHERE compte ~ '^41[1-8]'
+ (Solde_debiteur_N - Solde_debiteur_N1) WHERE compte ~ '^445[6-8]'
+ (Solde_debiteur_N - Solde_debiteur_N1) WHERE compte LIKE '486%'  -- part exploitation

-- Variation PCE (Degagements)
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte LIKE '4191%'
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte ~ '^40[138]'
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte ~ '^4[23]'
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte ~ '^44' (hors 444)
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte LIKE '487%'  -- part exploitation

-- Variation BFR exploitation = Variation ACE - Variation PCE
-- Un resultat positif = BESOIN supplementaire (defavorable)
-- Un resultat negatif = DEGAGEMENT de ressources (favorable)
```

---

#### 8.2.2. Variation du BFR hors exploitation

```
Variation BFR hors exploitation = Variation Actif circulant hors exploitation - Variation Passif circulant hors exploitation
```

| Poste | Comptes | Calcul |
|-------|---------|--------|
| Variation des creances diverses HE | **46** (debiteur), **467** (debiteur) | Solde N - Solde N-1 |
| Variation du capital souscrit appele non verse | **4562** | Solde N - Solde N-1 |
| Variation des VMP | **50** (hors 509) | Solde N - Solde N-1 |
| Variation des CCA hors exploitation | **486** (part HE) | Solde N - Solde N-1 |
| Variation des dettes sur immobilisations | **404, 405** | Solde N - Solde N-1 |
| Variation des dettes fiscales (IS) | **444** | Solde N - Solde N-1 |
| Variation des dettes diverses HE | **45, 46** (crediteur), **467** (crediteur) | Solde N - Solde N-1 |
| Variation des PCA hors exploitation | **487** (part HE) | Solde N - Solde N-1 |

---

#### 8.2.3. Variation de la tresorerie nette

```
Variation Tresorerie nette = Variation Tresorerie active - Variation Tresorerie passive
```

| Poste | Comptes | Calcul |
|-------|---------|--------|
| Variation des disponibilites | **512** (debiteur), **514, 53, 54** | Solde N - Solde N-1 |
| Variation des concours bancaires courants | **519** | Solde N - Solde N-1 |

**Formule SQL :**
```sql
-- Variation tresorerie active
(Solde_debiteur_N - Solde_debiteur_N1) WHERE compte ~ '^51[24]' OR compte ~ '^5[34]'
-- Variation tresorerie passive
- (Solde_crediteur_N - Solde_crediteur_N1) WHERE compte LIKE '519%'
```

---

#### 8.2.4. Controle de coherence du tableau de financement

```
Variation FRNG (Partie 1) = Variation BFR exploitation + Variation BFR hors exploitation + Variation Tresorerie nette (Partie 2)
```

**Controle SQL :**
```sql
ABS(
    variation_frng
  - variation_bfr_exploitation
  - variation_bfr_hors_exploitation
  - variation_tresorerie_nette
) < 0.01
```

Cette egalite doit **TOUJOURS** etre verifiee. Un ecart signale une erreur de reclassement entre exploitation / hors exploitation / tresorerie, ou un flux oublie dans la partie 1.

**Pieges et exceptions du tableau de financement :**
- Les **EENE** (effets escomptes non echus) doivent etre reintegres : en augmentation des creances clients (ACE) et en augmentation de la tresorerie passive. Sinon le BFR est sous-evalue et la tresorerie sur-evaluee.
- Les **valeurs mobilieres de placement** (50) sont classees en actif circulant hors exploitation dans le tableau de financement, pas en tresorerie (contrairement au tableau des flux de tresorerie ou les VMP tres liquides sont assimilees a la tresorerie).
- La **variation de stock** dans le tableau de financement est la variation de l'actif brut du bilan (soldes des comptes 31-37), pas la variation de stock du compte de resultat (6031/6032/6037/713).
- Les **provisions pour depreciation** des actifs circulants (39, 49) ne sont pas dans le BFR du tableau de financement. Elles sont neutralisees via la CAF (dotations/reprises).
- Le **credit-bail** n'apparait pas dans le tableau de financement PCG (sauf en retraitement pour l'analyse fonctionnelle).
- Les **ecarts de conversion** (476/477) generent des variations d'actif/passif circulant qui doivent etre incluses dans le BFR hors exploitation.

---

## 9. Comptabilite analytique d'exploitation

La comptabilite analytique (ou comptabilite de gestion) est un systeme d'information interne qui analyse les couts et les marges par produit, activite, centre de responsabilite ou tout autre axe de gestion. Elle s'appuie sur les charges de la classe 6 et les produits de la classe 7 de la comptabilite generale, mais les reclasse et les reorganise selon des criteres de gestion.

**Regle fondamentale** : le resultat analytique global doit etre raccordable au resultat de la comptabilite generale. Les differences de traitement (charges suppletives, charges non incorporables) font l'objet d'un compte de differences d'incorporation.

### 9.1. Methode des couts complets (centres d'analyse)

La methode des couts complets integre la totalite des charges (directes et indirectes) dans le cout des produits ou des activites. Elle repose sur le decoupage de l'entite en **centres d'analyse** (anciennement "sections homogenes").

#### 9.1.1. Charges directes et charges indirectes

```
Charges incorporables = Charges de la comptabilite generale
                      - Charges non incorporables
                      + Charges suppletives
```

| Type | Definition | Exemples |
|------|-----------|----------|
| **Charges directes** | Charges affectees sans ambiguite a un seul objet de cout (produit, commande, chantier) | Matieres premieres consommees (601), main-d'oeuvre directe (641 identifiee), sous-traitance specifique (611) |
| **Charges indirectes** | Charges communes a plusieurs objets de cout, necessitant une repartition | Loyers (613), electricite (6061), salaires d'encadrement (641), amortissements (681) |
| **Charges non incorporables** | Charges de la comptabilite generale exclues du calcul analytique | Charges exceptionnelles (67), dotations aux provisions financieres (686), amortissements des frais d'etablissement (6811 sur 201), rappels d'impots (63x), charges des exercices anterieurs |
| **Charges suppletives** | Charges non enregistrees en comptabilite generale mais integrees en analytique | Remuneration des capitaux propres (taux sans risque x CP), remuneration du travail de l'exploitant individuel |

**Formule SQL des charges incorporables :**
```sql
-- Total charges incorporables
SELECT
    SUM(debit - credit) AS charges_incorporables
FROM fec_ecriture
WHERE compte_num ~ '^6'
AND compte_num NOT IN (
    -- Charges non incorporables (a adapter selon politique analytique)
    SELECT compte_num WHERE compte_num LIKE '67%'     -- Charges exceptionnelles
    OR compte_num LIKE '687%'                          -- DAP exceptionnelles
    OR (compte_num LIKE '6811%' AND nature = 'frais_etablissement')
)
-- + Charges suppletives (hors comptabilite generale, a ajouter manuellement)
```

---

#### 9.1.2. Repartition primaire

La repartition primaire consiste a ventiler les charges indirectes entre les differents centres d'analyse a l'aide de **cles de repartition**.

```
Charge du centre i (primaire) = Charges directes du centre i
                               + SUM(Charge indirecte k x Cle de repartition k→i)
```

Les centres d'analyse se decomposent en :
- **Centres principaux** : centres dont l'activite concourt directement a la realisation des produits (approvisionnement, production, distribution, administration)
- **Centres auxiliaires** : centres qui fournissent des prestations aux autres centres (entretien, informatique, direction generale, gestion du personnel)

| Centre type | Exemples | Unite d'oeuvre typique |
|-------------|----------|----------------------|
| Approvisionnement | Service achats, magasin | Kg de matieres achetees, nombre de commandes |
| Production (atelier A) | Ligne de fabrication | Heure machine, heure de MOD |
| Production (atelier B) | Conditionnement | Nombre de lots, nombre d'unites |
| Distribution | Service commercial | Chiffre d'affaires HT, nombre de commandes clients |
| Administration | Direction, comptabilite | Cout de production des produits vendus |
| Auxiliaire : Entretien | Maintenance | Heures d'intervention |
| Auxiliaire : Informatique | SI | Nombre de postes, heures CPU |

**Pieges et exceptions :**
- Les **cles de repartition** doivent refleter la consommation reelle de ressources. Des cles forfaitaires (1/3, 1/3, 1/3) faussent les couts.
- Le total des cles de repartition pour une charge donnee doit etre egal a **100%** (controle de coherence).
- Les charges directes ne transitent PAS par le tableau de repartition. Elles sont affectees directement aux couts.

---

#### 9.1.3. Repartition secondaire

La repartition secondaire consiste a vider les centres auxiliaires en repartissant leurs couts dans les centres principaux (et eventuellement dans d'autres centres auxiliaires).

```
Cout du centre principal j = Total primaire du centre j
                            + SUM(Total centre auxiliaire a x Cle secondaire a→j)
```

**Cas des prestations reciproques** : si le centre Entretien fournit des heures au centre Informatique, et inversement, il faut resoudre un systeme d'equations lineaires :

```
Soit E = cout total Entretien, I = cout total Informatique
E = Total primaire Entretien + a% x I     (Informatique fournit a% a Entretien)
I = Total primaire Informatique + b% x E  (Entretien fournit b% a Informatique)
```

Resolution par substitution ou systeme matriciel.

**Pieges et exceptions :**
- Apres repartition secondaire, les totaux des centres auxiliaires doivent etre **nuls** (controle).
- Le total de tous les centres principaux apres repartition secondaire doit etre egal au total des charges incorporables indirectes (controle de bouclage).

---

#### 9.1.4. Unites d'oeuvre et cout de l'unite d'oeuvre

```
Cout de l'unite d'oeuvre = Total du centre apres repartition secondaire / Nombre d'unites d'oeuvre du centre
```

| Centre | Unite d'oeuvre | Taux de frais |
|--------|--------------|---------------|
| Approvisionnement | Euro d'achat ou kg achete | Cout UO = Total centre / Total achats (ou kg) |
| Production | Heure machine ou heure MOD | Cout UO = Total centre / Heures machine |
| Distribution | 100 euros de CA HT | Taux de frais = Total centre / (CA HT / 100) |
| Administration | Cout de production des produits vendus | Taux de frais = Total centre / Cout de production |

**Note** : pour le centre Administration, on utilise generalement un **taux de frais** (pourcentage) plutot qu'une unite d'oeuvre physique.

---

#### 9.1.5. Cout d'achat

```
Cout d'achat = Prix d'achat HT des matieres
             + Frais accessoires d'achat (transport, droits de douane)
             + Charges indirectes d'approvisionnement imputees
```

| Composante | Comptes | Calcul |
|-----------|---------|--------|
| Prix d'achat HT | **601, 602** | Montant facture hors taxes |
| Frais accessoires | **6081, 6082** | Transport, assurance, droits de douane |
| Charges indirectes approvisionnement | — | Nombre UO consommees x Cout UO approvisionnement |

**Formule SQL :**
```sql
SELECT
    produit_id,
    SUM(debit - credit) WHERE compte ~ '^60[12]' AS prix_achat_ht,
    SUM(debit - credit) WHERE compte LIKE '608%' AS frais_accessoires,
    nb_uo_approvisionnement * cout_uo_approvisionnement AS charges_indirectes_appro,
    -- Total
    prix_achat_ht + frais_accessoires + charges_indirectes_appro AS cout_achat
```

---

#### 9.1.6. Cout de production

```
Cout de production = Cout d'achat des matieres consommees
                   + Charges directes de production (MOD)
                   + Charges indirectes de production imputees
```

| Composante | Detail | Calcul |
|-----------|--------|--------|
| Matieres consommees | Stock initial + Achats - Stock final | Valorisees au cout d'achat (CUMP ou PEPS) |
| MOD | Main-d'oeuvre directe identifiee | Heures x Taux horaire charge |
| Charges indirectes production | Centres de production | Nombre UO consommees x Cout UO production |

```
Matieres consommees = Stock initial (valorise au cout d'achat)
                    + Entrees en stock au cout d'achat
                    - Stock final (valorise au CUMP ou PEPS)
```

**Pieges et exceptions :**
- Les **en-cours de production** (comptes 33, 34, 35) doivent etre valorises et deduits : `Cout de production des produits finis = Charges de la periode + En-cours initiaux - En-cours finals`.
- La **production immobilisee** (72) doit etre valorisee au cout de production, pas au prix de vente.
- Les **dechets et rebuts** : s'ils ont une valeur de revente, cette valeur vient en deduction du cout de production.
- La methode de valorisation des stocks (CUMP ou PEPS/FIFO) doit etre constante d'un exercice a l'autre (PCG Art. 213-2).

---

#### 9.1.7. Cout de revient

```
Cout de revient = Cout de production des produits vendus
                + Cout de distribution (charges directes + indirectes)
                + Cout d'administration impute
```

| Composante | Detail | Calcul |
|-----------|--------|--------|
| Cout de production des produits vendus | Sorties de stock au cout de production | CUMP ou PEPS |
| Charges directes de distribution | Commissions, transport sur ventes | 6242, 622, etc. |
| Charges indirectes de distribution | Centre distribution | Nombre UO x Cout UO distribution |
| Charges indirectes d'administration | Centre administration | Taux de frais x Cout de production |

```
Resultat analytique = Chiffre d'affaires - Cout de revient
```

**Controle de concordance avec la comptabilite generale :**
```
Resultat comptabilite generale
= Resultat analytique global
+ Charges non incorporables
- Charges suppletives
+ ou - Differences d'incorporation (arrondis, ecarts sur stocks)
+ ou - Produits non inclus dans le CA analytique (produits financiers, exceptionnels)
```

Ce controle de concordance doit etre effectue a chaque cloture.

---

### 9.2. Methode ABC (Activity-Based Costing)

La methode ABC (comptabilite par activites) remplace la notion de centre d'analyse par celle d'**activite** et d'**inducteur de cout**. Elle vise a mieux refleter la consommation reelle des ressources.

#### 9.2.1. Principes

```
Les produits consomment des activites.
Les activites consomment des ressources.
```

| Concept | Definition | Exemple |
|---------|-----------|--------|
| **Ressource** | Charge consommee (identique aux charges incorporables) | Salaires, amortissements, loyers |
| **Activite** | Ensemble de taches homogenes concourant a un meme objectif | "Passer des commandes", "Recevoir des livraisons", "Controler la qualite" |
| **Inducteur de cout** | Facteur explicatif du volume d'activite (equivalent de l'UO mais causal) | Nombre de commandes, nombre de references, nombre de lots |
| **Cout de l'inducteur** | Cout total de l'activite / Volume de l'inducteur | Total "Passer des commandes" / Nombre de commandes |

#### 9.2.2. Demarche de calcul

```
1. Identifier les activites
2. Affecter les ressources aux activites (via les charges directes et cles de repartition)
3. Identifier l'inducteur de cout de chaque activite
4. Calculer le cout unitaire de chaque inducteur
5. Imputer les couts aux objets de cout (produits) selon le volume d'inducteurs consommes
```

**Formule de cout ABC d'un produit :**
```
Cout ABC produit P = Charges directes de P
                   + SUM(pour chaque activite a : Volume inducteur a consomme par P x Cout unitaire inducteur a)
```

#### 9.2.3. Comparaison centres d'analyse vs ABC

| Critere | Centres d'analyse | ABC |
|---------|-------------------|-----|
| Unite de decoupage | Centre de responsabilite (structure) | Activite (processus transversal) |
| Cle de repartition | Unite d'oeuvre (souvent volumique) | Inducteur de cout (lien causal) |
| Traitement des charges de complexite | Noyees dans les centres | Isolees par activite (ex: nombre de references) |
| Precision sur produits a faible volume | Faible (subventionne par les grands volumes) | Elevee (cout de complexite bien affecte) |
| Mise en oeuvre | Relativement simple | Plus lourde (identification des activites) |
| Vision de l'entreprise | Hierarchique (centres) | Processus (chaine de valeur) |

**Pieges et exceptions :**
- L'ABC est plus precis mais **plus couteux a maintenir**. Il convient aux entites avec une gamme de produits diversifiee et des charges indirectes elevees.
- Les **activites de soutien** (management, comptabilite) sont souvent reparties au prorata, ce qui reduit l'avantage de l'ABC pour ces postes.
- Un inducteur mal choisi (non causal) donne des resultats aussi faux qu'une mauvaise UO. L'inducteur doit avoir un **lien de causalite demontrable** avec le cout.
- En pratique, beaucoup d'entites utilisent un systeme **hybride** : centres d'analyse pour les charges courantes, ABC pour les activites de support ou de logistique.

---

### 9.3. Couts partiels

Les methodes de couts partiels n'integrent qu'une partie des charges dans le cout des produits. L'objectif est d'analyser la contribution de chaque produit ou activite a la couverture des charges non imputees.

#### 9.3.1. Cout variable — Direct costing simple

```
Marge sur Cout Variable (MCV) = Chiffre d'affaires - Charges variables
```

Seules les charges variables (directes et indirectes) sont imputees aux produits. Les charges fixes sont traitees globalement en charges de periode.

| Element | Formule |
|---------|---------|
| Cout variable du produit | Charges variables directes + Charges variables indirectes |
| MCV unitaire | Prix de vente unitaire - Cout variable unitaire |
| Taux de MCV | MCV / CA |
| Resultat | MCV globale - Total charges fixes |

**Formule SQL :**
```sql
SELECT
    produit_id,
    SUM(CASE WHEN nature_charge = 'variable' THEN montant END) AS cout_variable,
    ca_produit - SUM(CASE WHEN nature_charge = 'variable' THEN montant END) AS mcv,
    (ca_produit - SUM(CASE WHEN nature_charge = 'variable' THEN montant END)) / NULLIF(ca_produit, 0) AS taux_mcv
FROM charges_analytiques
GROUP BY produit_id
```

**Pieges et exceptions :**
- La MCV ne couvre **pas les charges fixes**. Un produit avec une MCV positive contribue a la couverture des charges fixes, meme si le "resultat complet" est negatif.
- La suppression d'un produit a MCV positive **degrade le resultat global** (sauf si les charges fixes specifiques disparaissent aussi).
- La classification variable/fixe est une **approximation**. Les charges mixtes doivent etre ventilees (methode des points extremes, regression lineaire, ou ratio contractuel).

---

#### 9.3.2. Cout specifique — Direct costing evolue

```
Marge sur Cout Specifique (MCS) = MCV - Charges fixes specifiques (directes) du produit
```

Le direct costing evolue va plus loin que le simple en distinguant :
- **Charges fixes specifiques** : charges fixes directement attribuables a un produit ou une activite (amortissement d'une machine dediee, salaire d'un chef de produit)
- **Charges fixes communes** : charges fixes partagees entre plusieurs produits (loyer du siege, direction generale)

| Element | Formule |
|---------|---------|
| MCV | CA - Charges variables |
| Charges fixes specifiques | Charges fixes directement attribuables au produit |
| MCS | MCV - Charges fixes specifiques |
| Resultat | SUM(MCS de tous les produits) - Charges fixes communes |

**Pieges et exceptions :**
- Un produit avec une **MCS negative** doit etre abandonne (sauf consideration strategique), car il ne couvre meme pas ses propres charges fixes.
- Un produit avec une **MCV positive mais MCS negative** couvre les charges variables mais pas ses charges fixes specifiques. Il faut analyser si les charges fixes specifiques peuvent etre reduites.
- Les **charges fixes specifiques** sont parfois difficiles a identifier. Un doute doit conduire au classement en charges fixes communes.

---

### 9.4. Imputation rationnelle des charges fixes

L'imputation rationnelle permet de neutraliser l'effet des variations d'activite sur le cout unitaire. Elle consiste a n'incorporer dans les couts qu'une fraction des charges fixes, proportionnelle au niveau d'activite reel par rapport au niveau d'activite normal.

#### 9.4.1. Coefficient d'imputation rationnelle (CIR)

```
CIR = Activite reelle / Activite normale
```

```
Charges fixes imputees = Charges fixes totales x CIR
```

```
Cout complet rationnel = Charges variables + Charges fixes x CIR
```

| Situation | CIR | Effet |
|-----------|-----|-------|
| Activite reelle = Activite normale | CIR = 1 | Toutes les charges fixes sont imputees |
| Activite reelle < Activite normale | CIR < 1 | **Cout de sous-activite** = Charges fixes x (1 - CIR) |
| Activite reelle > Activite normale | CIR > 1 | **Boni de sur-activite** = Charges fixes x (CIR - 1) |

#### 9.4.2. Cout de sous-activite et boni de sur-activite

```
Ecart d'imputation rationnelle = Charges fixes totales - Charges fixes imputees
                                = Charges fixes x (1 - CIR)
```

- Si CIR < 1 : l'ecart est **positif** → cout de sous-activite (mali). C'est une charge de la periode, non incorporee aux couts des produits.
- Si CIR > 1 : l'ecart est **negatif** → boni de sur-activite. C'est un produit de la periode.

**Formule SQL :**
```sql
SELECT
    centre_id,
    charges_fixes_totales,
    activite_reelle,
    activite_normale,
    activite_reelle::numeric / NULLIF(activite_normale, 0) AS cir,
    charges_fixes_totales * (activite_reelle::numeric / NULLIF(activite_normale, 0)) AS charges_fixes_imputees,
    charges_fixes_totales * (1 - activite_reelle::numeric / NULLIF(activite_normale, 0)) AS ecart_imputation
FROM centres_analyse
```

**Pieges et exceptions :**
- L'**activite normale** est un choix de gestion (capacite pratique, moyenne des 3-5 derniers exercices, ou budget). Elle doit etre stable et justifiable.
- L'imputation rationnelle ne modifie **pas le resultat global** : elle reclasse une partie des charges fixes en cout de sous-activite (ou boni), mais le total reste identique.
- Cette methode est particulierement utile pour les activites **saisonnieres** : elle evite que les couts unitaires de la basse saison soient gonfles par l'etalement des charges fixes sur un faible volume.
- En comptabilite generale (PCG Art. 213-3), la valorisation des stocks peut integrer l'imputation rationnelle : les stocks sont valorises au cout de production avec charges fixes imputees rationnellement, et le cout de sous-activite est charge en resultat.

---

### 9.5. Couts standards et analyse des ecarts

Les couts standards (ou couts preetablis) sont des couts de reference calcules a priori, servant de base de comparaison avec les couts reels constates.

#### 9.5.1. Cout standard d'un produit

```
Cout standard = Quantite standard x Cout unitaire standard
```

| Composante | Quantite standard | Cout unitaire standard |
|-----------|-------------------|----------------------|
| Matiere premiere | Nomenclature technique (kg/unite) | Cout d'achat previsionnel (euro/kg) |
| Main-d'oeuvre directe | Gamme operatoire (h/unite) | Taux horaire charge previsionnel (euro/h) |
| Charges indirectes | Budget du centre / Production prevue = UO standard | Cout UO standard = Budget centre / Nombre UO prevues |

---

#### 9.5.2. Ecart global sur charges directes

```
Ecart global = Cout reel - Cout standard ajuste a la production reelle
             = (Qr x Cr) - (Qs x Cs)
```

Ou :
- Qr = Quantite reelle consommee
- Cr = Cout unitaire reel
- Qs = Quantite standard pour la production reelle (= Quantite standard unitaire x Production reelle)
- Cs = Cout unitaire standard

#### 9.5.3. Decomposition de l'ecart sur charges directes

```
Ecart sur quantite (E/Q) = (Qr - Qs) x Cs
Ecart sur cout (E/C)     = (Cr - Cs) x Qr
```

**Controle :**
```
Ecart global = E/Q + E/C
```

| Ecart | Formule | Interpretation si defavorable (positif) |
|-------|---------|---------------------------------------|
| E/Q (quantite) | (Qr - Qs) x Cs | Surconsommation de matieres ou heures MOD |
| E/C (cout) | (Cr - Cs) x Qr | Augmentation du prix d'achat matieres ou du taux horaire |

**Note importante** : la decomposition ci-dessus est celle a ecart sur cout valorise aux quantites reelles (methode PCG). L'autre methode (ecart sur cout valorise aux quantites standards) donne :

```
E/Q = (Qr - Qs) x Cs      (identique)
E/C = (Cr - Cs) x Qs       (valorise aux quantites standards)
Ecart mixte = (Qr - Qs) x (Cr - Cs)
```

En DCG/DSCG, la methode sans ecart mixte est la plus courante (ecart sur cout valorise aux quantites reelles).

---

#### 9.5.4. Ecart sur charges indirectes (ecart sur centre d'analyse)

L'ecart global sur charges indirectes se decompose en **trois sous-ecarts** :

```
Ecart global sur CI = Cout reel du centre - Cout standard impute a la production reelle
                    = Frais reels - (Production reelle x Cout standard par unite de production)
```

Soit :
- FR = Frais reels du centre
- AR = Activite reelle (en UO)
- AP = Activite prevue (budget)
- PR = Production reelle
- Cs = Cout standard de l'UO = Budget / AP
- QsUO = Nombre d'UO standard pour la production reelle = (AP / Production prevue) x PR

**Trois sous-ecarts :**

```
1. Ecart sur budget (E/B)    = FR - Budget ajuste a l'activite reelle
                              = FR - (Charges variables unitaires prevues x AR + Charges fixes budget)
                              = FR - Budget flexible(AR)
```

```
2. Ecart sur activite (E/A)  = Budget flexible(AR) - (AR x Cs)
                              = (Charges fixes budget / AP - Charges fixes budget / AR) x AR  [simplifie]
                              = Charges fixes budget x (1 - AR/AP)  [si CIR = AR/AP]
```

C'est l'equivalent du **cout de sous-activite** de l'imputation rationnelle.

```
3. Ecart sur rendement (E/R) = (AR - QsUO) x Cs
```

C'est l'equivalent de l'ecart sur quantite pour les charges indirectes.

**Controle :**
```
Ecart global sur CI = E/B + E/A + E/R
```

| Sous-ecart | Formule | Responsabilite |
|-----------|---------|---------------|
| E/B (budget) | FR - Budget flexible(AR) | Responsable du centre (depassement de budget a activite donnee) |
| E/A (activite) | Budget flexible(AR) - (AR x Cs) | Direction (sous-utilisation de la capacite) |
| E/R (rendement) | (AR - QsUO) x Cs | Responsable de production (productivite) |

**Formule SQL :**
```sql
SELECT
    centre_id,
    frais_reels,
    activite_reelle,
    activite_prevue,
    production_reelle,
    budget_cv_unitaire * activite_reelle + budget_cf AS budget_flexible,
    -- Ecart sur budget
    frais_reels - (budget_cv_unitaire * activite_reelle + budget_cf) AS ecart_budget,
    -- Ecart sur activite
    (budget_cv_unitaire * activite_reelle + budget_cf) - (activite_reelle * cout_standard_uo) AS ecart_activite,
    -- Ecart sur rendement
    (activite_reelle - uo_standard_pour_prod_reelle) * cout_standard_uo AS ecart_rendement,
    -- Controle
    frais_reels - (production_reelle * cout_standard_par_unite_produit) AS ecart_global_ci
FROM analyse_ecarts_ci
```

**Pieges et exceptions :**
- L'**ecart sur budget** mesure l'efficience du centre : a-t-il depense plus ou moins que prevu pour l'activite reelle ?
- L'**ecart sur activite** est structurel : il mesure la sous-utilisation (ou sur-utilisation) de la capacite. Il est souvent defavorable en periode de baisse d'activite.
- L'**ecart sur rendement** mesure la productivite : a-t-on consomme plus ou moins d'UO que prevu pour la production reelle ?
- Un ecart **favorable** (negatif) n'est pas toujours positif : un ecart favorable sur quantite de matieres peut traduire un changement de qualite (matieres moins cheres mais de moindre qualite).
- Le **budget flexible** est le budget recalcule au niveau d'activite reelle : on garde les charges fixes du budget initial, mais on ajuste les charges variables au volume reel.

---

## 10. Evaluation et depreciation des actifs

Le PCG (Art. 210-1 et suivants, normes ANC 2014-03 recueil mis a jour) definit les regles d'evaluation des actifs a l'entree, a la cloture, et en cas de depreciation. Ces regles determinent les valeurs inscrites au bilan et les eventuelles dotations aux depreciations.

### 10.1. Valeurs d'evaluation des actifs

#### 10.1.1. Valeur d'entree (cout historique)

```
Valeur d'entree = Cout d'acquisition  (si acquisition a titre onereux)
               OU Valeur venale        (si acquisition a titre gratuit)
               OU Cout de production   (si production par l'entite)
               OU Valeur d'apport      (si apport en nature)
```

| Mode d'acquisition | Valeur d'entree | Comptes | Reference PCG |
|--------------------|-----------------|---------|----|
| Acquisition a titre onereux | **Cout d'acquisition** = Prix d'achat HT + Frais accessoires (droits de douane, frais de transport, frais d'installation et de montage) | **20, 21** (debit) | Art. 213-8 |
| Production par l'entite | **Cout de production** = Cout d'acquisition des matieres + Charges directes de production + Quote-part de charges indirectes de production | **20, 21** (debit) / **72** (credit) | Art. 213-9 |
| Acquisition a titre gratuit | **Valeur venale** = Prix presume qu'accepterait d'en donner un acquereur dans l'etat ou se trouve l'actif | **20, 21** (debit) / **77** (credit) | Art. 213-10 |
| Echange | **Valeur venale** du bien recu (ou du bien cede si elle est plus fiable) | | Art. 213-11 |
| Apport en nature | **Valeur d'apport** figurant dans le traite d'apport | | Art. 213-12 |

**Pieges et exceptions :**
- Les **frais accessoires** (transport, installation, montage, droits de mutation, honoraires de notaire) font partie du cout d'acquisition. Ils sont inscrits au debit du compte d'immobilisation correspondant (pas en charges).
- Les **droits de mutation, honoraires, commissions et frais d'actes** peuvent, sur option, etre comptabilises en charges (PCG Art. 213-8, alinea 2). Le choix doit etre mentionne en annexe et applique de maniere constante.
- Les **couts d'emprunt** peuvent etre incorpores au cout d'acquisition ou de production des actifs eligibles (PCG Art. 213-9-1). C'est une option, pas une obligation.
- La **TVA non deductible** fait partie du cout d'acquisition (majorant la valeur d'entree).
- Les **escomptes de reglement obtenus** sont des produits financiers (765), ils ne viennent PAS en deduction du cout d'acquisition (difference avec les normes IFRS).

---

#### 10.1.2. Valeur actuelle

```
Valeur actuelle = Valeur la plus elevee entre la valeur venale et la valeur d'usage
```

| Notion | Definition | Methode d'evaluation |
|--------|-----------|---------------------|
| **Valeur venale** | Prix presume qu'accepterait de payer un acquereur dans l'etat et le lieu ou se trouve le bien | Marche actif, transactions comparables, estimation d'expert |
| **Valeur d'usage** | Valeur des avantages economiques futurs attendus de l'utilisation de l'actif et de sa sortie | Flux de tresorerie futurs actualises (DCF), ou usage interne si pas de marche |

**Pieges et exceptions :**
- La valeur actuelle sert de reference pour le **test de depreciation** a chaque cloture.
- Pour un actif sans marche actif (ex: logiciel specifique, immobilisation en cours), la valeur d'usage est souvent la seule reference.
- La valeur actuelle ne peut **jamais servir a reevaluer l'actif au-dessus de son cout historique** (sauf reevaluation libre, PCG Art. 214-27, avec passage de l'ecart en capitaux propres au 105).

---

#### 10.1.3. Valeur recouvrable et valeur nette comptable

```
Valeur nette comptable (VNC) = Valeur d'entree - Amortissements cumules - Depreciations cumulees
```

```
Valeur recouvrable = MAX(Valeur venale nette des couts de sortie, Valeur d'usage)
```

**Regle de cloture (PCG Art. 214-15) :**
```
Si Valeur actuelle < VNC  →  Depreciation necessaire
Si Valeur actuelle >= VNC →  Pas de depreciation (mais verifier les indices)
```

---

### 10.2. Test de depreciation (PCG Art. 214-15 a 214-18)

Le test de depreciation est obligatoire a chaque cloture lorsqu'il existe un **indice de perte de valeur** (interne ou externe). Pour les immobilisations incorporelles a duree d'utilisation indeterminee (goodwill, marques), le test est obligatoire **chaque annee**, meme en l'absence d'indice.

#### 10.2.1. Procedure du test

```
1. Identifier les indices de perte de valeur (cf. 10.3)
2. Si indice detecte : estimer la valeur actuelle de l'actif
3. Comparer la valeur actuelle a la VNC
4. Si valeur actuelle < VNC : comptabiliser une depreciation
5. Ajuster le plan d'amortissement pour les exercices futurs
```

#### 10.2.2. Comptabilisation de la depreciation

```
Depreciation = VNC - Valeur actuelle
```

| Operation | Debit | Credit | Libelle |
|----------|-------|--------|---------|
| Constatation de la depreciation | **6816** | **29x** | Dotation aux depreciations des immobilisations incorporelles et corporelles |
| | **6816** | **290, 291** | Depreciation des immobilisations incorporelles (290) ou corporelles (291) |
| | **6817** | **296, 297** | Dotation aux depreciations des immobilisations financieres |

**Detail des comptes de depreciation :**

| Compte d'actif | Compte de depreciation | Libelle |
|---------------|----------------------|---------|
| **201** | **2901** | Depreciation des frais d'etablissement |
| **203** | **2903** | Depreciation des frais de R&D |
| **205** | **2905** | Depreciation des concessions, brevets |
| **206** | **2906** | Depreciation du droit au bail |
| **207** | **2907** | Depreciation du fonds commercial |
| **211** | **2911** | Depreciation des terrains |
| **213** | **2913** | Depreciation des constructions |
| **215** | **2915** | Depreciation des ITMOI |
| **218** | **2918** | Depreciation des autres immo corporelles |
| **261** | **2961** | Depreciation des titres de participation |
| **271** | **2971** | Depreciation des titres immobilises |
| **274** | **2974** | Depreciation des prets |
| **275** | **2975** | Depreciation des depots et cautionnements |

**Formule SQL :**
```sql
-- Depreciations de l'exercice
SELECT
    compte_immobilisation,
    SUM(debit - credit) WHERE compte LIKE '28%' AS amortissements_cumules,
    SUM(credit - debit) WHERE compte LIKE '29%' AS depreciations_cumulees,
    valeur_brute - amortissements_cumules - depreciations_cumulees AS vnc,
    valeur_actuelle,
    CASE
        WHEN valeur_actuelle < vnc THEN vnc - valeur_actuelle
        ELSE 0
    END AS depreciation_a_constater
FROM immobilisations
```

#### 10.2.3. Reprise de depreciation

Si la valeur actuelle redevient superieure a la VNC (depreciation devenue sans objet) :

```
Reprise = MIN(Depreciation cumulee, Valeur actuelle - VNC avant reprise)
```

| Operation | Debit | Credit | Libelle |
|----------|-------|--------|---------|
| Reprise de depreciation | **29x** | **7816** | Reprise sur depreciation des immobilisations incorporelles et corporelles |
| | **296, 297** | **7817** | Reprise sur depreciation des immobilisations financieres |

**Pieges et exceptions :**
- La reprise de depreciation ne peut **jamais** conduire a une VNC superieure a la VNC que l'actif aurait eue sans depreciation (c'est-a-dire avec le plan d'amortissement initial).
- Le **fonds commercial** (207) ne fait l'objet d'une reprise de depreciation que dans des cas **exceptionnels** et justifies (PCG Art. 214-18).
- Apres constatation ou reprise d'une depreciation, le plan d'amortissement doit etre **revise** prospectivement : la nouvelle base amortissable = VNC apres depreciation (ou reprise), amortie sur la duree d'utilisation residuelle.
- Les depreciations des **titres de participation** (2961) sont deductibles fiscalement sous conditions (plus-values latentes non compensables avec moins-values). Attention au regime des plus-values a long terme.

---

### 10.3. Indices de perte de valeur

Le PCG (Art. 214-15) et le reglement ANC 2014-03 listent les indices de perte de valeur a rechercher a chaque cloture.

#### 10.3.1. Indices externes

| # | Indice externe | Exemple concret |
|---|---------------|-----------------|
| 1 | Diminution significative de la valeur de marche | Chute du prix de l'immobilier pour un immeuble, baisse du cours des titres cotes |
| 2 | Changements importants dans l'environnement economique, juridique ou technologique | Nouvelle reglementation rendant un actif obsolete, apparition d'une technologie concurrente |
| 3 | Augmentation des taux d'interet | Impact sur la valeur d'usage (taux d'actualisation plus eleve reduit la valeur actualisee des flux futurs) |
| 4 | Valeur comptable de l'actif net superieure a la capitalisation boursiere | Pour les entites cotees uniquement |

#### 10.3.2. Indices internes

| # | Indice interne | Exemple concret |
|---|---------------|-----------------|
| 1 | Obsolescence ou degradation physique | Materiel accidente, logiciel non maintenu, batiment degrade |
| 2 | Changements importants dans le mode d'utilisation | Arret d'une ligne de production, restructuration, mise au rebut prevue |
| 3 | Performances inferieures aux previsions | L'actif genere des flux de tresorerie ou un resultat inferieur aux previsions initiales |
| 4 | Decisions d'arret ou de restructuration | Plan de cession, fermeture de site, arret d'activite |
| 5 | Ecart d'acquisition (goodwill) non amorti | Si le goodwill a une duree d'utilisation non determinable, test annuel obligatoire |

**Pieges et exceptions :**
- La liste des indices n'est **pas limitative**. Tout evenement susceptible d'affecter la valeur d'un actif doit etre examine.
- Un seul indice suffit a declencher le test de depreciation.
- L'absence d'indice pour un actif amortissable dispense du test de depreciation (mais pas de la revue du plan d'amortissement, PCG Art. 214-13).
- Pour les **immobilisations incorporelles non amorties** (fonds commercial 207, marques 205 si duree indeterminee), le test est annuel **meme sans indice**.

---

### 10.4. Ecarts de conversion (comptes 476/477)

Les ecarts de conversion concernent les creances et dettes libellees en monnaie etrangere. A la cloture, ces elements sont convertis au cours de change de cloture, generant des ecarts de conversion.

#### 10.4.1. Principe de conversion a la cloture

```
Valeur au cours de cloture = Montant en devise x Cours de cloture
Valeur comptable initiale   = Montant en devise x Cours historique (date de l'operation)
Ecart de conversion         = Valeur au cours de cloture - Valeur comptable initiale
```

#### 10.4.2. Ecart de conversion actif (476) — Perte latente

Un **ecart de conversion actif** represente une **perte latente** : la situation s'est degradee entre la date de l'operation et la cloture.

| Situation | Ecart | Ecriture |
|----------|-------|----------|
| Creance en devise : le cours a baisse (la devise a perdu de la valeur) | Perte latente | Debit **476** / Credit **411** (ou 267, etc.) |
| Dette en devise : le cours a monte (il faudra payer plus cher en euros) | Perte latente | Debit **476** / Credit **401** (ou 16x, etc.) |

**Provision pour risque de change :**

Par application du principe de prudence, la perte latente donne lieu a une **provision pour risque de change** :

```
Provision pour risque de change = Montant de l'ecart de conversion actif (perte latente)
```

| Operation | Debit | Credit |
|----------|-------|--------|
| Constatation ecart conversion actif | **476** | Compte de creance ou dette concerne |
| Dotation provision risque de change | **6865** | **1515** (provision pour pertes de change) |

**Formule SQL :**
```sql
-- Ecarts de conversion actif a la cloture
SELECT
    compte_num,
    devise,
    montant_devise,
    montant_devise * cours_historique AS valeur_historique,
    montant_devise * cours_cloture AS valeur_cloture,
    CASE
        WHEN type_compte = 'creance' AND cours_cloture < cours_historique
            THEN montant_devise * (cours_historique - cours_cloture)
        WHEN type_compte = 'dette' AND cours_cloture > cours_historique
            THEN montant_devise * (cours_cloture - cours_historique)
        ELSE 0
    END AS ecart_conversion_actif_476
FROM comptes_en_devise
WHERE ecart_conversion_actif_476 > 0
```

---

#### 10.4.3. Ecart de conversion passif (477) — Gain latent

Un **ecart de conversion passif** represente un **gain latent** : la situation s'est amelioree.

| Situation | Ecart | Ecriture |
|----------|-------|----------|
| Creance en devise : le cours a monte (on recevra plus d'euros) | Gain latent | Debit **411** (ou 267, etc.) / Credit **477** |
| Dette en devise : le cours a baisse (il faudra payer moins cher) | Gain latent | Debit **401** (ou 16x, etc.) / Credit **477** |

**Pas de provision** : par application du principe de prudence, les gains latents ne sont **pas comptabilises en produit**. Ils sont simplement constates au bilan (477) sans impact sur le resultat.

---

#### 10.4.4. Contre-passation a l'ouverture de l'exercice suivant

A l'ouverture de l'exercice suivant (N+1), les ecritures d'ecarts de conversion sont **contre-passees** (extournees) pour ramener les creances et dettes a leur valeur historique :

| Operation | Debit | Credit |
|----------|-------|--------|
| Contre-passation ecart conversion actif | Compte de creance ou dette | **476** |
| Contre-passation ecart conversion passif | **477** | Compte de creance ou dette |
| Reprise provision risque de change | **1515** | **7865** |

Ainsi, a l'ouverture de N+1, les comptes 476 et 477 sont soldes, et les creances/dettes retrouvent leur valeur historique. Lors du reglement effectif, le gain ou la perte de change reel sera constate en **666** (perte de change) ou **766** (gain de change).

**Formule SQL :**
```sql
-- Ecritures de contre-passation a generer en ouverture N+1
SELECT
    'Contre-passation ECA' AS libelle,
    compte_creance_dette AS compte_debit,
    '476' AS compte_credit,
    montant_eca AS montant
FROM ecarts_conversion
WHERE type = 'actif' AND exercice = N

UNION ALL

SELECT
    'Contre-passation ECP' AS libelle,
    '477' AS compte_debit,
    compte_creance_dette AS compte_credit,
    montant_ecp AS montant
FROM ecarts_conversion
WHERE type = 'passif' AND exercice = N

UNION ALL

SELECT
    'Reprise provision change' AS libelle,
    '1515' AS compte_debit,
    '7865' AS compte_credit,
    montant_provision AS montant
FROM provisions_change
WHERE exercice = N
```

---

#### 10.4.5. Cas particulier : couverture de change

Si la creance ou la dette en devise fait l'objet d'une **couverture de change** (contrat a terme, option de change), le traitement differe :

| Situation | Traitement |
|----------|-----------|
| Couverture parfaite (meme montant, meme echeance, meme devise) | L'ecart de conversion est neutralise par l'instrument de couverture. Pas de provision pour risque de change sur la partie couverte. |
| Couverture partielle | Provision pour risque de change uniquement sur la partie **non couverte**. |
| Position globale de change | Compensation possible des pertes et gains latents sur une meme devise (position nette). Provision sur le solde net defavorable. |

**Pieges et exceptions :**
- La **compensation** des ecarts de conversion actif et passif n'est possible que pour une **meme devise** et des operations de meme nature (PCG Art. 420-7).
- Les **ICNE** (interets courus non echus) en devise sont aussi soumis a conversion au cours de cloture et generent des ecarts de conversion.
- En cas de **cession de creance** (affacturage, escompte), l'ecart de conversion doit etre transfere ou liquide au moment de la cession.
- Les comptes **476 et 477** apparaissent respectivement a l'actif et au passif du bilan. Ils ne doivent **jamais etre compenses** entre eux.
- Le compte **1515** (provision pour pertes de change) est a distinguer du **1516** (provision pour pertes sur contrats a terme). Les deux sont au passif du bilan en provisions pour risques.

---

## Annexe A — Correspondance comptes PCG et etats financiers

Table de reference rapide pour l'implementation SQL :

| Etat | Poste | Comptes inclus | Signe dans l'etat |
|------|-------|---------------|-------------------|
| SIG | Marge commerciale (+) | 707 | credit - debit |
| SIG | Marge commerciale (-) | 607, 6037 | debit - credit |
| SIG | Marge commerciale (+) | 6097 | credit - debit |
| SIG | Production (+) | 701-706, 708 | credit - debit |
| SIG | Production (-) | 7091-7096, 7098 | credit - debit (negatif) |
| SIG | Production (+) | 713 | credit - debit |
| SIG | Production (+) | 72 | credit - debit |
| SIG | VA (-) consommations | 601,602,604,605,606,608 | debit - credit |
| SIG | VA (-) consommations | 6031, 6032 | debit - credit |
| SIG | VA (-) consommations | 61, 62 | debit - credit |
| SIG | VA (+) RRR obtenus | 6091-6096, 6098 | credit - debit |
| SIG | EBE (+) | 74 | credit - debit |
| SIG | EBE (-) | 63 | debit - credit |
| SIG | EBE (-) | 64 | debit - credit |
| SIG | Rex (+) | 781, 791, 75 | credit - debit |
| SIG | Rex (-) | 681, 65 | debit - credit |
| SIG | RCAI (+) | 76, 786, 796 | credit - debit |
| SIG | RCAI (-) | 66, 686 | debit - credit |
| SIG | Rex except (+) | 77, 787, 797 | credit - debit |
| SIG | Rex except (-) | 67, 687 | debit - credit |
| SIG | Resultat (-) | 691, 695, 696, 699 | debit - credit |
| CR | CA | 70 - 709 | credit - debit |
| Bilan | Actif immo brut | 20-27 | debit - credit |
| Bilan | Amort/deprec actif immo | 28, 29 | credit - debit |
| Bilan | Stocks brut | 31-37 | debit - credit |
| Bilan | Deprec stocks | 39 | credit - debit |
| Bilan | Creances clients brut | 411-418 | debit - credit |
| Bilan | Deprec creances | 49 | credit - debit |
| Bilan | Dispo | 512, 514, 53, 54 | debit - credit |
| Bilan | Capitaux propres | 10-14 (sauf 109) | credit - debit |
| Bilan | Provisions | 15 | credit - debit |
| Bilan | Dettes financieres | 16, 17 | credit - debit |
| Bilan | Dettes fournisseurs | 401, 403, 408 | credit - debit |
| Bilan | CBC | 519 | credit - debit |
| BF | Emplois stables | 20-27 (BRUT) | debit - credit |
| BF | Ressources stables | CP + 28+29+39+49+59 + 15 + 16+17 | credit - debit |
| BF | ACE | Stocks brut + Creances exploit brut | debit - credit |
| BF | PCE | Dettes exploit | credit - debit |
| BF | Tresorerie active | 512+514+53+54 | debit - credit |
| BF | Tresorerie passive | 519 | credit - debit |
| TdF | CAF (ressource durable) | Resultat + DAP - RAP - PCEA + VCEAC - 777 | cf. section 1.9 |
| TdF | PCEA (ressource) | 775 | credit - debit |
| TdF | Acquisitions immo (emploi) | Flux debit 20-27 | debit (flux) |
| TdF | Emprunts nouveaux (ressource) | Flux credit 16 (hors 169, 1688) | credit (flux) |
| TdF | Remboursements emprunts (emploi) | Flux debit 16 (hors 169, 1688) | debit (flux) |
| TdF | Distributions (emploi) | 457 | debit (flux) |
| TdF | Variation BFR exploit | Variation N vs N-1 des postes ACE et PCE | solde N - solde N-1 |
| TdF | Variation tresorerie | Variation 512+514+53+54 - Variation 519 | solde N - solde N-1 |
| Deprec | Depreciation immobilisations | 6816 / 29x | debit (dotation) |
| Deprec | Reprise depreciation | 29x / 7816 | credit (reprise) |
| ECA | Ecart conversion actif (perte latente) | 476 | debit - credit |
| ECP | Ecart conversion passif (gain latent) | 477 | credit - debit |
| ECA | Provision risque de change | 6865 / 1515 | debit (dotation) |

---

## Annexe B — Controles de coherence

Liste des controles a implementer dans `v_controles_coherence` :

| # | Controle | Formule | Seuil |
|---|---------|---------|-------|
| 1 | Equilibre debit/credit | SUM(debit) = SUM(credit) par ecriture | Ecart = 0 |
| 2 | Resultat CR = Resultat bilan | SIG Resultat net = Solde compte 12 | Ecart < 0.01 |
| 3 | Total Actif = Total Passif | Bilan actif net = Bilan passif | Ecart < 0.01 |
| 4 | FRNG = BFR + TN | FRNG - BFR exploit - BFR HE - TN = 0 | Ecart < 0.01 |
| 5 | CAF additive = CAF soustractive | Les deux methodes de CAF donnent le meme resultat | Ecart < 0.01 |
| 6 | Reciprocite intra-groupe | Solde 451/455 entite A vs entite B | Ecart = 0 |
| 7 | Cloture N-1 = Ouverture N | Soldes bilan fin N-1 = A-nouveaux N | Ecart = 0 |
| 8 | Variation tresorerie | TN fin - TN debut = Flux de tresorerie | Ecart < 0.01 |
| 9 | Tableau de financement P1 = P2 | Variation FRNG = Variation BFR exploit + Variation BFR HE + Variation TN | Ecart < 0.01 |
| 10 | Concordance analytique/generale | Resultat analytique + Charges non incorp. - Charges suppletives +/- Differences = Resultat comptable | Ecart < 0.01 |
| 11 | Repartition secondaire : centres auxiliaires soldes | Total de chaque centre auxiliaire apres repartition secondaire = 0 | Ecart = 0 |
| 12 | Ecart global CI = E/B + E/A + E/R | Decomposition des ecarts sur charges indirectes | Ecart < 0.01 |
| 13 | VNC apres reprise <= VNC sans depreciation | Reprise de depreciation ne depasse pas le plan d'amortissement initial | VNC reprise <= VNC initiale |
| 14 | Ecarts de conversion 476/477 soldes a l'ouverture | Contre-passation effective des ecarts de conversion | Solde = 0 |

---

*Referentiel de comptabilite analytique et financiere — PCG / normes ANC*
*Derniere mise a jour : 2 avril 2026*
