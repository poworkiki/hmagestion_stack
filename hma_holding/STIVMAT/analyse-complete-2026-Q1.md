# Analyse complete -- STIVMAT -- T1 2026

**Societe** : STE DE TRANSPORT INTERNATIONALE DE VOYAGEURS ET DE MARCHANDISE ANAMAY TRANSPORT
**SIREN** : 801 937 996
**Periode** : 01/01/2026 -> 31/03/2026 (1er trimestre)
**Generee le** : 03/04/2026
**Source** : API Pennylane v2 (token lecture seule)

---

## 1. Synthese executive

STIVMAT affiche un CA de **222 041 EUR** au T1 2026 (prestations de services transport), soit un rythme annualise de **~888 000 EUR**. C'est un changement radical par rapport a l'exercice 2025 ou seulement 3 073 EUR etaient comptabilises. La comptabilite est **nettement mieux structuree** : les charges de paie sont enregistrees (6411, 645x), les impots/taxes apparaissent (63x), et un emprunt est identifie (164). Le resultat net du trimestre est de **+131 501 EUR** (taux de rentabilite nette 59,2%), un niveau **anormalement eleve** qui s'explique par :

- **Pas d'amortissements** (681) enregistres -- aucune dotation sur le trimestre
- **Charges de personnel faibles** (25 305 EUR pour ~8 salaries sur 3 mois, soit ~11,4% du CA vs 40-55% en norme transport)
- **Carburant a seulement 4,7% du CA** vs 15-25% attendus en transport de personnes
- **Caisse especes toujours au crediteur** (-46 916 EUR) -- anomalie persistante depuis 2025

La situation T1 est **encourageante** mais les marges reelles seront sensiblement inferieures une fois les amortissements et l'integralite des charges sociales comptabilises.

---

## 2. Balance par classe

| Classe | Intitule | Debit | Credit | Solde |
|---|---|---:|---:|---:|
| 1 | Comptes de capitaux (emprunt) | 2 148,95 | 0,00 | 2 148,95 |
| 2 | Immobilisations | 0,00 | 0,00 | 0,00 |
| 3 | Stocks | 0,00 | 0,00 | 0,00 |
| 4 | Tiers | 394 466,13 | 328 932,25 | 65 533,88 |
| 5 | Financiers / Tresorerie | 455 836,32 | 392 019,18 | 63 817,14 |
| 6 | Charges | 112 821,63 | 18 058,23 | 94 763,40 |
| 7 | Produits | 0,00 | 222 041,00 | -222 041,00 |

**Evolutions vs 2025** :
- **Classe 1** : apparition d'un emprunt (164 -- Bred pret pro equipement 34 990 EUR)
- **Classe 2 toujours vide** : les vehicules ne sont pas immobilises
- **Classe 4** : beaucoup plus structuree avec comptes de paie (421, 431, 437, 438)
- **Classe 6** : charges de personnel enregistrees (absent en 2025), impots/taxes presents
- **Classe 7** : CA 222 041 EUR vs 3 073 EUR sur tout 2025

---

## 3. Soldes Intermediaires de Gestion

| SIG | Montant (EUR) | % CA |
|---|---:|---:|
| **CA HT** | 222 041,00 | 100,0% |
| Prestations de services (706) | 222 041,00 | 100,0% |
| **Production de l'exercice** | 222 041,00 | 100,0% |
| Achats marchandises (607) | -215,00 | -0,1% |
| **Marge commerciale** | -215,00 | -0,1% |
| Achats et fournitures (60 hors 607) | -32 857,06 | -14,8% |
| Services exterieurs (61-62) | -27 844,43 | -12,5% |
| **Consommations intermediaires** | -60 701,49 | -27,3% |
| **Valeur ajoutee** | 161 124,51 | 72,6% |
| Impots et taxes (63) | -303,48 | -0,1% |
| Charges de personnel (64) | -25 304,72 | -11,4% |
| **EBE** | 135 516,31 | 61,0% |
| Autres charges exploitation (651) | -1 407,00 | -0,6% |
| **Resultat d'exploitation** | 134 109,31 | 60,4% |
| Charges financieres (6611) | -277,34 | -0,1% |
| **RCAI** | 133 831,97 | 60,3% |
| Charges exceptionnelles (6713) | -2 331,00 | -1,0% |
| **Resultat exceptionnel** | -2 331,00 | -1,0% |
| IS (695) | 0,00 | 0,0% |
| **Resultat net** | 131 500,97 | 59,2% |

**Attention** : EBE a 61% du CA est **anormalement eleve** pour du transport de personnes (norme 5-15%). L'absence d'amortissements (681) et la sous-comptabilisation probable des charges de personnel expliquent cet ecart.

---

## 4. Ratios cles

| Ratio | Valeur | Seuil | Commentaire |
|---|---:|---|---|
| Taux VA / CA | 72,6% | > 20% | Eleve -- normal si peu de sous-traitance |
| Taux EBE / CA | 61,0% | > 5% | Tres eleve -- amortissements manquants |
| Rentabilite nette | 59,2% | > 0% | Surevaluee (pas de DAP, charges personnel incompletes) |
| Charges personnel / VA | 15,7% | 40-55% | Tres faible -- charges incompletes |
| Carburant / CA | 4,7% | 15-25% | Bas -- possible saisonnalite ou sous-enregistrement |
| Entretien vehicules / CA | 5,0% | 5-10% | OK -- dans la norme |
| Assurances / CA | 3,8% | 3-8% | OK |
| Frais bancaires / CA | 0,5% | < 2% | OK |
| Delai clients | ~-11 j | < 60 j | Clients crediteurs (-6 955 EUR = avances ou trop-percu) |
| Delai fournisseurs | ~9 j | < 60 j | 1 602 EUR / (60 916 * 1.20) x 365 |

---

## 5. Anomalies detectees

### Critiques

| # | Anomalie | Detail |
|---|---|---|
| 1 | **Aucune immobilisation (classe 2 vide)** | Une societe de transport n'a aucun vehicule immobilise. Les vehicules devraient figurer en 218x (materiel de transport). Consequence : pas d'amortissements (681), resultat surevalue. |
| 2 | **Caisse especes creditrice : -46 916 EUR** | Compte 530001 toujours au crediteur impossible (etait -66 673 EUR en 2025). Anomalie persistante non corrigee. |
| 3 | **Charges de personnel a 11,4% du CA** | 25 305 EUR pour ~8 salaries sur 3 mois = ~1 054 EUR/mois/salarie en cout total. Norme transport = 40-55% du CA. Ecart enorme. |
| 4 | **Ecart paiements salaires vs charges enregistrees** | Debits 421 (anciens comptes) : 30 417 EUR. Credits 421 (nouveaux comptes) : 10 642 EUR. Charges 6411 : 14 288 EUR. Les ecritures de paie ne couvrent pas tous les mois. |

### Attention

| # | Anomalie | Detail |
|---|---|---|
| 5 | **Double jeu de comptes 421** | Comptes 421XXXXX (anciens, debiteurs) et 42100XXX (nouveaux, crediteurs) coexistent. Migration inachevee du module paie Pennylane. |
| 6 | **AMEX associe toujours debiteur : 61 316 EUR** | Compte 455101AMEX. Rythme : ~20 500 EUR/mois de depenses associe via AMEX. Sur 2025 c'etait 210 600 EUR. |
| 7 | **Dons a 2 331 EUR (1% du CA)** | Compte 6713. A justifier fiscalement. |
| 8 | **Emprunt mal positionne** | Compte 16400007 au debit (2 149 EUR) = remboursements. Mais le solde de l'emprunt (capital restant du) n'apparait pas au credit. L'emprunt initial n'est pas enregistre. |
| 9 | **Pas d'amortissements** | Aucun compte 681 (DAP) sur le trimestre. Meme en l'absence d'immobilisations, les amortissements de l'emprunt et des eventuels vehicules en credit-bail devraient apparaitre. |
| 10 | **6063 (fournitures petit equipement) : 17 611 EUR** | Montant eleve (7,9% du CA). A verifier : des equipements > 500 EUR HT devraient etre immobilises. |

### Information

| # | Anomalie | Detail |
|---|---|---|
| 11 | **Compte 411 crediteur net (-6 955 EUR)** | Les clients ont paye plus que facture (avances ou encaissements anticipes). |
| 12 | **Compte 651101 (Pennylane) : 1 407 EUR** | Abonnement Pennylane correctement comptabilise en charges. |
| 13 | **Oppositions sur salaires (427) : 694 EUR** | Saisies sur salaires en cours pour au moins 1 salarie. |
| 14 | **Comptes de transit quasi soldes** | Les enormes soldes 471x de 2025 (927 908 EUR) ne sont plus visibles sur T1 2026. Probablement soldes fin 2025 ou report different. |

---

## 6. Analyse sectorielle -- Transport de personnes

### Indicateurs specifiques T1 2026

| Indicateur | Valeur | Norme secteur | Commentaire |
|---|---:|---|---|
| Carburant / CA | 4,7% | 15-25% | Bas -- potentiellement incomplet ou saisonnier |
| Charges personnel / CA | 11,4% | 40-55% | Tres bas -- paie incomplete sur le trimestre |
| Entretien vehicules (6155+6156) / CA | 5,0% | 5-10% | OK |
| Assurances / CA | 3,8% | 3-8% | OK |
| Fournitures petit equip. / CA | 7,9% | < 3% | Eleve -- verifier si immobilisable |
| Transports sur achats / CA | 1,7% | Variable | OK |
| LODEOM social | Non identifiable | - | Pas de ligne specifique d'exoneration visible |

### Detail carburant

| Compte | Libelle | Montant |
|---|---|---:|
| 6061001 | Gasoil carburant | 9 691,80 EUR |
| 6061 | Fournitures non stockables (energie) | 395,37 EUR |
| 6061003 | Carburant sans-plomb essence | 314,00 EUR |
| 6062 | Fournitures non stockables (carburant) | 61,00 EUR |
| **Total carburant** | | **10 462,17 EUR** |

A 4,7% du CA, le carburant est **3 a 5 fois inferieur** a la norme transport. Hypotheses :
- Saisie incomplete des factures carburant sur le trimestre
- Vehicules electriques/hybrides (peu probable en Guyane)
- Sous-traitance d'une partie des trajets (pas visible en 604)

### Detail personnel

| Salarie | Paiements (421 ancien) | Charges enregistrees (421 nouveau) |
|---|---:|---:|
| ISCAYE Franck | 4 766,31 EUR | 1 563,99 EUR |
| CLERIN Roseline | 4 648,50 EUR | N/A (pas de nouveau compte) |
| Jovane DENIS | 4 603,39 EUR | 1 492,55 EUR |
| DA JOSEPH | 4 563,99 EUR | 1 511,30 EUR |
| Onassis ROBERTS | 4 666,30 EUR | N/A |
| CASTOR Delivrance | 3 957,73 EUR | 1 314,63 EUR |
| BELLAS Michel | 3 100,78 EUR | 1 545,59 EUR |
| ARIANETTE FEVRY | 110,48 EUR | 95,14 EUR |
| 42100025 (non identifie) | - | 1 568,59 EUR |
| 42100027 (non identifie) | - | 1 550,19 EUR |
| **Total** | **30 417,48 EUR** | **10 641,98 EUR** |

**Ecart 19 775 EUR** entre les paiements effectifs et les charges de paie enregistrees. Les bulletins de paie ne sont pas tous generes sur Pennylane.

### Detail services exterieurs (61-62)

| Poste | Montant | % CA |
|---|---:|---:|
| Entretien vehicules (6155) | 10 761,07 EUR | 4,8% |
| Assurances (616) | 8 456,92 EUR | 3,8% |
| Transports sur achats (6241) | 3 877,82 EUR | 1,7% |
| Dons/Amen (623801) | 856,96 EUR | 0,4% |
| Frais bancaires (627+6278) | 1 024,48 EUR | 0,5% |
| Telephone/internet (6262) | 506,94 EUR | 0,2% |
| Honoraires (6226) | 500,00 EUR | 0,2% |
| Entretien immobilier (6152) | 470,00 EUR | 0,2% |
| Maintenance (6156) | 367,32 EUR | 0,2% |
| Transports sur ventes (6242) | 284,71 EUR | 0,1% |
| Location mobiliere (6135) | 217,00 EUR | 0,1% |
| Autres (6288, 6234, 623, 6227, 6251) | 521,21 EUR | 0,2% |
| **Total 61-62** | **27 844,43 EUR** | **12,5%** |

---

## 7. Tresorerie detaillee

| Compte | Libelle | Solde |
|---|---|---:|
| 5121001 | Pennylane -- Compte Pro | 280,02 EUR |
| 5121002 | Bred | 4 382,06 EUR |
| 5121005 | Credit Agricole 40255966105 | -1 809,29 EUR |
| 530001 | Caisse especes | -46 915,65 EUR |
| 580 | Virements internes | -4 755,00 EUR |
| 5800001 | Virement interne | 112 635,00 EUR |
| **Total (hors 580)** | | **-44 062,86 EUR** |
| **Total (avec 580)** | | **63 817,14 EUR** |

**Comparaison 2025** :
- Tresorerie hors 580 : -44 063 EUR (vs -66 126 EUR en 2025) -> amelioration de +22 063 EUR
- Caisse : -46 916 EUR (vs -66 673 EUR) -> amelioration mais toujours impossible
- Virements internes : 107 880 EUR non affectes

---

## 8. Comptes courants et intra-groupe

| Compte | Tiers | Debit | Credit | Solde | Sens |
|---|---|---:|---:|---:|---|
| 451001 | HMA (holding) | 2 300,00 | 1 380,00 | 920,00 | HMA doit a STIVMAT |
| 451002 | STIVMAT | 0,00 | 2 480,00 | -2 480,00 | Compte propre |
| 455101AMEX | AMERICAN EXPRESS | 67 500,00 | 6 184,24 | 61 315,76 | Associe debiteur |
| 4674ATML | ATML | 0,00 | 2 800,00 | -2 800,00 | Divers crediteurs |
| 4677 | 940157 HMA ASSOCIES | 4 000,00 | 0,00 | 4 000,00 | Associes debiteurs |

**Croisement intra-groupe** :
- STIVMAT/HMA : STIVMAT montre HMA debiteur de 920 EUR. Dans l'analyse ETPA 2025, HMA devait 2 800 EUR a ETPA. Les soldes intra-groupe doivent etre reconcilies.
- AMEX associe : 61 316 EUR sur Q1 seul (rythme annuel ~245 000 EUR). C'etait 210 600 EUR sur tout 2025.

---

## 9. Factures

| Type | Nombre | Observations |
|---|---:|---|
| Factures fournisseurs | 206 | (total Pennylane, tous exercices confondus) |
| Factures clients | 12 | Faible pour 222k EUR de CA -- grosse facturation unitaire |
| Journaux | 24 | Structure complete avec paie, tresorerie, achats, ventes |

---

## 10. Recommandations

### Priorite 1 -- Urgentes

1. **Immobiliser les vehicules** -- Classe 2 vide. Les vehicules doivent etre enregistres en 2182 (materiel de transport) avec les amortissements correspondants en 681. Sans cela, le resultat est surevalue de potentiellement 20 000-50 000 EUR/an (selon la valeur de la flotte). Verifier si les vehicules sont en propriete, credit-bail (612) ou location (6135).

2. **Completer les ecritures de paie** -- 30 417 EUR payes aux salaries vs 14 288 EUR de charges 6411 enregistrees. Ecart de ~16 000 EUR. Verifier le parametrage du module Paie Pennylane et generer les bulletins manquants.

3. **Regulariser la caisse** -- -46 916 EUR, en amelioration vs 2025 (-66 673 EUR) mais toujours impossible. Pointer les encaissements especes manquants.

### Priorite 2 -- Avant cloture semestrielle

4. **Enregistrer l'emprunt Bred** -- Le pret pro equipement (34 990 EUR) n'apparait qu'en remboursements (2 149 EUR). Le capital initial doit etre enregistre au credit du 164 et le tableau d'amortissement saisi.

5. **Comptabiliser les amortissements** -- Meme sans immobilisations, les charges a repartir et les amortissements de l'emprunt doivent etre provisionnes trimestriellement.

6. **Migrer les comptes 421** -- Fusionner les anciens comptes auxiliaires (421BELLASMICHEL etc.) avec les nouveaux (42100019 etc.) pour eviter les doublons.

7. **Justifier le compte AMEX** -- 61 316 EUR en 3 mois. Documenter la nature des depenses et le traitement fiscal.

### Priorite 3 -- Optimisation

8. **Activer LODEOM social** -- Avec ~8 salaries en Guyane, l'exoneration LODEOM (art. L752-3-2 CSS) peut generer 30 000-60 000 EUR/an d'economies de cotisations patronales. Aucune ligne d'exoneration n'est visible dans les comptes 645.

9. **Verifier le taux de carburant** -- 4,7% du CA est tres bas pour du transport. Si les factures carburant sont a jour, c'est un excellent indicateur d'efficience. Sinon, les factures manquantes degraderont le resultat.

10. **Provisionner l'IS** -- Avec un resultat previsionnel positif, provisionner les acomptes d'IS (taux 15% jusqu'a 42 500 EUR puis 25%).

---

## Comparaison T1 2026 vs Exercice 2025

| Indicateur | 2025 (12 mois) | T1 2026 (3 mois) | Evolution |
|---|---:|---:|---|
| CA HT | 3 073 EUR | 222 041 EUR | x72 -- CA reel enfin comptabilise |
| Resultat net | -24 873 EUR | +131 501 EUR | Retour a la rentabilite |
| Carburant | 8 112 EUR | 10 462 EUR | +29% en 3 mois vs 12 mois |
| Charges personnel | 2 232 EUR | 25 305 EUR | x11 -- paie enregistree |
| Tresorerie (hors 580) | -66 126 EUR | -44 063 EUR | +22 063 EUR |
| Caisse | -66 673 EUR | -46 916 EUR | +19 757 EUR (toujours anormale) |
| Comptes transit 471x | 927 908 EUR | 0 EUR | Soldes -- bonne nouvelle |
| AMEX associe | 210 600 EUR | 61 316 EUR | Rythme similaire |

L'amelioration est **considerable** : la comptabilite 2026 reflete enfin l'activite reelle de STIVMAT. Les principaux chantiers restants sont l'immobilisation des vehicules, la finalisation de la paie, et la regularisation de la caisse.

---

*Rapport genere par le skill pennylane-analyse -- Donnees Pennylane lecture seule*
*12 factures clients . 206 factures fournisseurs . 88 comptes actifs . 24 journaux*
