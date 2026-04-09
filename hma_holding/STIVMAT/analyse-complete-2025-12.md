# Analyse complete -- STIVMAT

**Societe** : STE DE TRANSPORT INTERNATIONALE DE VOYAGEURS ET DE MARCHANDISE ANAMAY TRANSPORT
**SIREN** : 801 937 996
**Periode** : 01/01/2025 -> 31/12/2025
**Generee le** : 03/04/2026
**Source** : API Pennylane v2 (token lecture seule)

---

## 1. Synthese executive

STIVMAT est une societe de **transport de personnes** en Guyane. L'exercice 2025 presente un CA de seulement **3 073 EUR** (prestations de services), extremement faible pour une structure employant **7 salaries**. Le resultat net est de **-24 873 EUR**. La situation comptable presente de **graves anomalies structurelles** :

- **Salaires payes (70 201 EUR) mais aucune charge salariale enregistree** (641 quasi vide) -- les ecritures de paie ne sont pas comptabilisees en charges
- **Comptes de transit massifs** : 291 459 EUR en decaissements en attente et 637 323 EUR en encaissements en attente sur le Credit Agricole -- la majorite des operations n'est pas affectee
- **Caisse especes au crediteur impossible** (-66 673 EUR) -- meme anomalie que ETPA
- **Compte associe AMEX debiteur de 210 600 EUR** -- montant considerable a justifier
- **Aucun capital, aucune immobilisation, aucun stock** enregistres (classes 1, 2, 3 vides)

Le CA reel de STIVMAT est probablement **beaucoup plus eleve** que 3 073 EUR -- les encaissements en attente (637 323 EUR) suggerent un CA potentiel significatif non encore comptabilise en produits.

---

## 2. Balance par classe

| Classe | Intitule | Debit | Credit | Solde |
|---|---|---:|---:|---:|
| 1 | Comptes de capitaux | 0,00 | 0,00 | 0,00 |
| 2 | Immobilisations | 0,00 | 0,00 | 0,00 |
| 3 | Stocks | 0,00 | 0,00 | 0,00 |
| 4 | Tiers | 584 827,40 | 666 378,25 | -81 550,85 |
| 5 | Financiers / Tresorerie | 934 883,54 | 878 205,73 | 56 677,81 |
| 6 | Charges | 28 710,67 | 765,13 | 27 945,54 |
| 7 | Produits | 0,00 | 3 072,50 | -3 072,50 |

**Observations** :
- **Classes 1, 2, 3 vides** : aucun capital social, aucune immobilisation (vehicules ?), aucun stock -- situation anormale pour une societe de transport
- **Classe 4 dominee par les comptes de transit** (471x) et le compte associe AMEX (455)
- **Classe 5** : solde apparemment positif mais fausse par la caisse creditrice et les virements internes

---

## 3. Soldes Intermediaires de Gestion

| SIG | Montant (EUR) | % CA |
|---|---:|---:|
| **CA HT** | 3 072,50 | 100,0% |
| Ventes marchandises (707) | 0,00 | 0,0% |
| Prestations de services (706) | 3 072,50 | 100,0% |
| **Production de l'exercice** | 3 072,50 | 100,0% |
| **Marge commerciale** | 0,00 | N/A |
| Achats et fournitures (605-606) | -11 608,64 | -377,9% |
| Services exterieurs (61-62) | -12 091,30 | -393,5% |
| **Consommations intermediaires** | -23 699,94 | -771,3% |
| **Valeur ajoutee** | -20 627,44 | -671,3% |
| Subventions exploitation (74) | 0,00 | 0,0% |
| Impots et taxes (63) | 0,00 | 0,0% |
| Charges de personnel (64) | -2 232,41 | -72,7% |
| **EBE** | -22 859,85 | -743,9% |
| Autres produits/charges exploitation | 0,00 | 0,0% |
| **Resultat d'exploitation** | -22 859,85 | -743,9% |
| Charges financieres (6611) | -13,19 | -0,4% |
| **RCAI** | -22 873,04 | -744,4% |
| Charges exceptionnelles (67) | -2 000,00 | -65,1% |
| **Resultat exceptionnel** | -2 000,00 | -65,1% |
| IS (695) | 0,00 | 0,0% |
| **Resultat net** | -24 873,04 | -809,5% |

**Attention** : ces SIG sont calcules sur le CA comptabilise (3 073 EUR) qui ne reflete PAS le CA reel de STIVMAT. Les encaissements en attente (637 323 EUR) n'ont pas ete ventiles en produits.

---

## 4. Ratios cles

| Ratio | Valeur | Seuil | Commentaire |
|---|---:|---|---|
| Taux VA / CA | -671,3% | > 20% | Non significatif -- CA sous-evalue |
| Taux EBE / CA | -743,9% | > 5% | Non significatif -- CA sous-evalue |
| Rentabilite nette | -809,5% | > 0% | Non significatif -- CA sous-evalue |
| Charges personnel / VA | N/A | < 80% | VA negative -- ratio non calculable |
| Carburant / CA | 256,3% | 15-25% | Non significatif -- 7 875 EUR de carburant vs 3 073 EUR de CA |
| Taux d'endettement | N/A | < 100% | Pas de capitaux propres ni dettes financieres |
| Liquidite generale | N/A | > 1 | Classes 1-3 vides |
| Delai clients | ~365 j | < 60 j | 3 073 EUR de creances = 100% du CA |
| Delai fournisseurs | ~54 j | < 60 j | 15 419 EUR / (23 700 * 1.20) x 365 |

**Note** : les ratios sont NON SIGNIFICATIFS tant que les comptes de transit (471x) n'auront pas ete soldes et les produits correctement comptabilises.

---

## 5. Anomalies detectees

### Critiques

| # | Anomalie | Detail |
|---|---|---|
| 1 | **Salaires payes sans charges correspondantes** | 7 salaries avec 70 201 EUR cumules au debit des comptes 421, mais aucun compte 6411 (remunerations du personnel). Seul 6414 (indemnites) a 1 843 EUR. Les ecritures de paie ne generent pas les charges salariales. |
| 2 | **Comptes de transit non soldes -- 927 908 EUR** | 4716005 (decaissements en attente CA) : 290 585 EUR debit. 4717005 (encaissements en attente CA) : 637 323 EUR credit. Ces montants doivent etre ventiles sur les comptes definitifs. |
| 3 | **Caisse especes au crediteur impossible** | Compte 530001 : solde -66 673 EUR. Une caisse physique ne peut pas avoir un solde negatif. Indique des retraits non justifies ou des encaissements manquants. |
| 4 | **Classes 1, 2, 3 vides** | Aucun capital social (101), aucune immobilisation (vehicules en 218x ?), aucun stock. Pour une societe de transport, les vehicules devraient etre immobilises. |
| 5 | **Compte associe AMEX debiteur de 210 600 EUR** | Compte 455101AMEX : montant tres eleve. L'associe a utilise la carte AMEX pour 210 600 EUR de depenses -- a justifier et documenter. |
| 6 | **CA manifestement sous-evalue** | 3 073 EUR de CA pour 7 salaries et 24 journaux comptables -- ne reflete pas l'activite reelle. Les encaissements en transit (637 323 EUR) contiennent probablement le CA reel. |

### Attention

| # | Anomalie | Detail |
|---|---|---|
| 7 | **Carburant > CA** | 6061 : 7 875 EUR + 60611 : 237 EUR = 8 112 EUR de fournitures energetiques vs 3 073 EUR de CA. Normal en absolu pour du transport, mais confirme que le CA est sous-evalue. |
| 8 | **Dons et liberalites** | Compte 6713 : 300 EUR + 678 (charges exceptionnelles) : 1 700 EUR = 2 000 EUR de charges exceptionnelles a justifier. |
| 9 | **Comptes courants associes** | HMA (451001) : -2 140 EUR (STIVMAT doit a HMA). STIVMAT (451002) : -2 000 EUR. Mouvements intra-groupe a documenter. |
| 10 | **Bred - decaissements en attente** | Compte 4716002 : 874 EUR -- faible montant mais a regulariser. |

### Information

| # | Anomalie | Detail |
|---|---|---|
| 11 | **Retour sur achat (6063 credit)** | 765 EUR au credit du compte 6063 -- avoir fournisseur ou retour de marchandise. |
| 12 | **Pas d'impots ni taxes** | Aucun compte 63x -- ni CFE, ni CVAE, ni taxes sur les vehicules. |

---

## 6. Analyse sectorielle -- Transport de personnes

### Indicateurs specifiques STIVMAT

| Indicateur | Valeur | Norme secteur | Commentaire |
|---|---:|---|---|
| Carburant / CA | 256,3% | 15-25% | Non significatif (CA sous-evalue) |
| Charges personnel / CA | 72,7% | 40-55% | Non significatif (CA sous-evalue) |
| Entretien vehicules (6155) / CA | 159,3% | 5-10% | Non significatif (CA sous-evalue) |
| Maintenance (6156) / CA | 97,6% | Inclus entretien | Non significatif |
| Assurances / CA | 37,6% | 3-8% | Non significatif |
| LODEOM social | Absent | - | Aucune exoneration LODEOM visible (pas de 645 reduits) |

**Note** : tous les ratios sectoriels sont inexploitables en l'etat. Il faudrait recalculer avec le CA reel une fois les comptes de transit ventiles.

### Estimation du CA reel potentiel

Les encaissements en attente sur le Credit Agricole (637 323 EUR) representent probablement l'essentiel des recettes non encore comptabilisees. Si meme une fraction est du CA :
- Hypothese basse (50% = CA) : ~318 662 EUR -> ratios normaux pour du transport
- Hypothese haute (80% = CA) : ~509 859 EUR -> societe correctement dimensionnee pour 7 salaries

### Detail du personnel (comptes 421)

| Salarie | Debit cumule 2025 |
|---|---:|
| CLERIN Roseline | 14 458,35 EUR |
| DA JOSEPH | 13 002,87 EUR |
| ISCAYE Franck | 10 645,61 EUR |
| BELLAS Michel | 10 122,13 EUR |
| Jovane DENIS | 8 376,45 EUR |
| CASTOR Delivrance | 8 137,26 EUR |
| Onassis ROBERTS | 5 457,95 EUR |
| **Total** | **70 200,62 EUR** |

Les debits sur 421 correspondent aux salaires payes (virements). Mais sans credits correspondants (ecritures de paie), ces comptes restent debiteurs de maniere anormale.

### Detail des charges par nature

| Poste | Comptes | Montant | % CA |
|---|---|---:|---:|
| Carburant | 6061, 60611 | 8 111,53 EUR | 264,0% |
| Entretien vehicules | 6155, 6156 | 7 894,60 EUR | 256,9% |
| Fournitures petit equip. | 6063, 60631 | 2 344,17 EUR | 76,3% |
| Frais personnel | 6414, 6475, 648 | 2 232,41 EUR | 72,7% |
| Charges exceptionnelles | 6713, 678 | 2 000,00 EUR | 65,1% |
| Frais bancaires | 627, 6278 | 1 868,90 EUR | 60,8% |
| Assurances | 616 | 1 155,90 EUR | 37,6% |
| Materiel/equipements | 605 | 1 152,94 EUR | 37,5% |
| Location mobiliere | 6135 | 1 090,00 EUR | 35,5% |
| Electricite | 60611 | (inclus carburant) | - |
| Transports sur achats | 6241 | 81,90 EUR | 2,7% |
| Charges financieres | 6611 | 13,19 EUR | 0,4% |

---

## 7. Tresorerie detaillee

| Compte | Libelle | Solde |
|---|---|---:|
| 5121001 | Pennylane -- Compte Pro | 24,58 EUR |
| 5121002 | Bred | 674,48 EUR |
| 5121005 | Credit Agricole 40255966105 | -152,52 EUR |
| 530001 | Caisse especes | -66 672,60 EUR |
| 5800001 | Virement interne | 122 803,87 EUR |
| 58090004 | Virements internes Swan | 0,00 EUR |
| **Total (hors 580)** | | **-66 126,06 EUR** |
| **Total (avec 580)** | | **56 677,81 EUR** |

**Attention** : le solde "positif" avec virements internes est trompeur. La tresorerie reelle (hors 580) est **-66 126 EUR**, dominee par l'anomalie de la caisse.

---

## 8. Comptes courants et intra-groupe

| Compte | Tiers | Debit | Credit | Solde | Sens |
|---|---|---:|---:|---:|---|
| 451001 | HMA (holding) | 0,00 | 2 140,00 | -2 140,00 | STIVMAT doit a HMA |
| 451002 | STIVMAT | 0,00 | 2 000,00 | -2 000,00 | Compte propre (credit) |
| 455101AMEX | AMERICAN EXPRESS | 210 600,00 | 0,00 | 210 600,00 | Associe debiteur |

**Solde net comptes courants** : 206 460,00 EUR debiteur (l'associe doit 210 600 EUR via AMEX)

**Croisement intra-groupe** : dans l'analyse ETPA, le compte 451002 (STIVMAT) montre que STIVMAT a avance 1 785 EUR a ETPA. Ce montant n'apparait pas symetriquement ici -- a verifier.

---

## 9. Factures

| Type | Nombre | Observations |
|---|---:|---|
| Factures fournisseurs | 206 | Volume important pour le CA affiche |
| Factures clients | 12 | Tres faible -- confirme un CA sous-evalue ou une facturation incomplete |
| Journaux | 24 | 7 journaux de tresorerie, 1 paie, journaux custom |

---

## 10. Recommandations

### Priorite 1 -- URGENTES (avant toute analyse fiable)

1. **Solder les comptes de transit (471x)** -- 927 908 EUR en attente d'affectation (290 585 EUR decaissements + 637 323 EUR encaissements). C'est la priorite absolue : aucun ratio ni SIG n'est fiable tant que ces montants ne sont pas ventiles sur les comptes definitifs.

2. **Comptabiliser les charges de paie** -- 70 201 EUR de salaires payes (421 debit) sans contrepartie en charges (641). Les ecritures de paie doivent etre generees : 641x (salaires bruts), 645x (charges sociales), 431/437 (organismes sociaux). Verifier si le module Paie de Pennylane est correctement parametre.

3. **Regulariser la caisse** -- Solde crediteur de -66 673 EUR physiquement impossible. Identifier les operations manquantes (encaissements especes non saisis, depenses fictives, erreurs de journal).

### Priorite 2 -- Structuration comptable

4. **Enregistrer le capital social** -- Compte 101 vide. Regulariser l'apport en capital et les a-nouveaux des exercices precedents (exercices 2022-2024 ouverts dans Pennylane).

5. **Immobiliser les vehicules** -- Une societe de transport doit avoir ses vehicules en immobilisations (218x, 2182). Verifier si les vehicules sont en propriete (immobilisation) ou en credit-bail (engagement hors bilan).

6. **Justifier le compte AMEX associe** -- 210 600 EUR au debit du 455101AMEX. Documenter la nature des depenses et verifier le traitement fiscal (avantage en nature ? compte courant associe ?).

7. **Comptabiliser les impots et taxes** -- Aucun compte 63x : ni CFE, ni taxe sur les vehicules (TVTS/taxe annuelle). Ces taxes sont obligatoires pour une societe de transport.

### Priorite 3 -- Optimisation

8. **Activer les exonerations LODEOM** -- En Guyane, STIVMAT peut beneficier de l'exoneration LODEOM social (art. L752-3-2 CSS) : exoneration totale des cotisations patronales jusqu'a 1,3 SMIC (environ 2 200 EUR/mois brut). Avec 7 salaries, l'economie potentielle est significative.

9. **Traiter les exercices anterieurs** -- Les exercices 2022, 2023 et 2024 sont ouverts (status: open). Les a-nouveaux et les reports doivent etre traites pour avoir une situation patrimoniale correcte.

10. **Rapprocher les comptes bancaires** -- Effectuer un rapprochement bancaire complet sur le Credit Agricole (752 965 EUR de mouvements debit, 753 117 EUR de mouvements credit) pour valider l'exactitude des ecritures.

---

*Rapport genere par le skill pennylane-analyse -- Donnees Pennylane lecture seule*
*12 factures clients . 206 factures fournisseurs . 40 comptes actifs . 24 journaux*
