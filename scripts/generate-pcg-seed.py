#!/usr/bin/env python3
"""
Génère le fichier SQL seed pour pcg_analytique à partir des comptes Pennylane.
Source: /tmp/pennylane_accounts.jsonl (1 412 comptes)
Output: sql/02-data/001-pcg-analytique-seed.sql
"""
import json
import os

import platform
if platform.system() == "Windows":
    INPUT_FILE = os.path.join(os.environ.get("TEMP", "C:/Users/gabin/AppData/Local/Temp"), "pennylane_accounts.jsonl")
else:
    INPUT_FILE = "/tmp/pennylane_accounts.jsonl"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "sql", "02-data", "001-pcg-analytique-seed.sql")

# Read all accounts
def fix_encoding(s):
    """Fix double-encoded UTF-8 strings from Pennylane API."""
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        fixed = s
    # Assertion anti double-UTF8 résiduel
    if "\u00c3" in fixed:
        import unicodedata
        fixed = unicodedata.normalize("NFC", fixed)
    return fixed

accounts = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            acc = json.loads(line)
            acc["label"] = fix_encoding(acc["label"])
            accounts.append(acc)

print(f"Loaded {len(accounts)} accounts from Pennylane")


def get_mapping(num):
    n = num.strip()
    classe = int(n[0]) if n and n[0].isdigit() else 0

    sig_solde = None
    sig_signe = None
    cr_rubrique = None
    cr_signe = None
    bilan_poste = None
    bilan_section = None
    bf_categorie = None
    nature_defaut = "fixe"

    # ===== CLASSE 1 — CAPITAUX =====
    if classe == 1:
        bilan_section = "passif_capitaux"
        bf_categorie = "ressources_stables"
        # CRITIQUE: 109 = Capital souscrit non appelé = ACTIF (créance sur actionnaires)
        if n.startswith("109"):
            bilan_poste = "Capital souscrit non appele"
            bilan_section = "actif_immobilise"
            bf_categorie = "emplois_stables"
        elif n.startswith("10"):
            bilan_poste = "Capital"
        elif n.startswith("11"):
            bilan_poste = "Report a nouveau"
        elif n.startswith("12"):
            bilan_poste = "Resultat de l exercice"
        elif n.startswith("13"):
            bilan_poste = "Subventions d investissement"
        elif n.startswith("14"):
            bilan_poste = "Provisions reglementees"
        elif n.startswith("15"):
            bilan_poste = "Provisions pour risques et charges"
        elif n.startswith("169"):
            # CRITIQUE: 169 = Primes de remboursement des emprunts = ACTIF
            bilan_poste = "Primes de remboursement des emprunts"
            bilan_section = "actif_immobilise"
            bf_categorie = "emplois_stables"
        elif n.startswith("16"):
            bilan_poste = "Emprunts et dettes assimilees"
            bilan_section = "passif_dettes"
        elif n.startswith("17"):
            bilan_poste = "Dettes rattachees a des participations"
            bilan_section = "passif_dettes"
        elif n.startswith("18"):
            bilan_poste = "Comptes de liaison"

    # ===== CLASSE 2 — IMMOBILISATIONS =====
    elif classe == 2:
        bilan_section = "actif_immobilise"
        bf_categorie = "emplois_stables"
        if n.startswith("20"):
            bilan_poste = "Immobilisations incorporelles"
        elif n.startswith("21"):
            bilan_poste = "Immobilisations corporelles"
        elif n.startswith("22"):
            bilan_poste = "Immobilisations mises en concession"
        elif n.startswith("23"):
            bilan_poste = "Immobilisations en cours"
        # CRITIQUE: 24x = Participations (manquait dans le mapping)
        elif n.startswith("24"):
            bilan_poste = "Participations et creances rattachees"
        elif n.startswith("25") or n.startswith("26") or n.startswith("27"):
            bilan_poste = "Immobilisations financieres"
        elif n.startswith("28"):
            bilan_poste = "Amortissements des immobilisations"
            bf_categorie = "ressources_stables"
        elif n.startswith("29"):
            bilan_poste = "Depreciations des immobilisations"
            bf_categorie = "ressources_stables"

    # ===== CLASSE 3 — STOCKS =====
    elif classe == 3:
        bilan_section = "actif_circulant"
        bilan_poste = "Stocks et en-cours"
        bf_categorie = "bfr_exploit"
        nature_defaut = "variable"
        if n.startswith("39"):
            bilan_poste = "Depreciations des stocks"
            bf_categorie = "ressources_stables"

    # ===== CLASSE 4 — TIERS =====
    elif classe == 4:
        bilan_section = "actif_circulant"
        bf_categorie = "bfr_exploit"
        if n.startswith("40"):
            bilan_poste = "Fournisseurs et comptes rattaches"
            bilan_section = "passif_dettes"
        elif n.startswith("41"):
            bilan_poste = "Clients et comptes rattaches"
        elif n.startswith("42") or n.startswith("43"):
            bilan_poste = "Personnel et organismes sociaux"
            bilan_section = "passif_dettes"
        elif n.startswith("44"):
            bilan_poste = "Etat et collectivites publiques"
            if n.startswith("445") and not n.startswith("4456"):
                bilan_section = "passif_dettes"
            else:
                bilan_section = "actif_circulant"
        elif n.startswith("45"):
            bilan_poste = "Groupe et associes"
            bf_categorie = "bfr_hors_exploit"
        elif n.startswith("46"):
            bilan_poste = "Debiteurs et crediteurs divers"
            bf_categorie = "bfr_hors_exploit"
        elif n.startswith("47"):
            bilan_poste = "Comptes transitoires ou d attente"
            bf_categorie = "bfr_hors_exploit"
        # CRITIQUE: 486 CCA = actif, 487 PCA = passif (distinction obligatoire)
        elif n.startswith("486"):
            bilan_poste = "Charges constatees d avance"
            bilan_section = "actif_circulant"
            bf_categorie = "bfr_exploit"
        elif n.startswith("487"):
            bilan_poste = "Produits constates d avance"
            bilan_section = "passif_dettes"
            bf_categorie = "bfr_exploit"
        elif n.startswith("481"):
            # MOYEN: 481 Frais émission emprunts = hors exploitation
            bilan_poste = "Frais d emission d emprunts a etaler"
            bf_categorie = "bfr_hors_exploit"
        elif n.startswith("48"):
            bilan_poste = "Comptes de regularisation"
        elif n.startswith("49"):
            bilan_poste = "Depreciations des comptes de tiers"
            bf_categorie = "ressources_stables"

    # ===== CLASSE 5 — FINANCIER =====
    elif classe == 5:
        bilan_section = "actif_circulant"
        bf_categorie = "tresorerie_active"
        if n.startswith("50"):
            bilan_poste = "Valeurs mobilieres de placement"
        elif n.startswith("51"):
            bilan_poste = "Banques et etablissements financiers"
            if n.startswith("519"):
                bilan_section = "passif_dettes"
                bf_categorie = "tresorerie_passive"
        elif n.startswith("53"):
            bilan_poste = "Caisse"
        elif n.startswith("54"):
            bilan_poste = "Regies d avances et accreditifs"
        elif n.startswith("58"):
            bilan_poste = "Virements internes"
        elif n.startswith("59"):
            bilan_poste = "Depreciations des VMP"
            bf_categorie = "ressources_stables"
        else:
            bilan_poste = "Tresorerie"

    # ===== CLASSE 6 — CHARGES =====
    elif classe == 6:
        cr_signe = -1

        if n.startswith("607") or n == "6037":
            sig_solde = "Marge commerciale"
            sig_signe = -1
            cr_rubrique = "Achats de marchandises"
            nature_defaut = "variable"
        elif n.startswith("6031") or n.startswith("6032"):
            sig_solde = "Valeur ajoutee"
            sig_signe = -1
            cr_rubrique = "Variation de stocks matieres"
            nature_defaut = "variable"
        # MOYEN: 6033/6034/6035 = variation stocks produits finis → Production, pas VA
        elif n.startswith("6033") or n.startswith("6034") or n.startswith("6035"):
            sig_solde = "Production de l exercice"
            sig_signe = -1
            cr_rubrique = "Variation de stocks produits"
            nature_defaut = "variable"
        elif n.startswith("60"):
            sig_solde = "Valeur ajoutee"
            sig_signe = -1
            cr_rubrique = "Achats consommes"
            nature_defaut = "variable"
        elif n.startswith("61") or n.startswith("62"):
            sig_solde = "Valeur ajoutee"
            sig_signe = -1
            cr_rubrique = "Services exterieurs"
            if n.startswith("613") or n.startswith("614") or n.startswith("616"):
                nature_defaut = "fixe"
            else:
                nature_defaut = "variable"
        elif n.startswith("63"):
            sig_solde = "EBE"
            sig_signe = -1
            cr_rubrique = "Impots, taxes et versements assimiles"
            nature_defaut = "fixe"
        elif n.startswith("64"):
            sig_solde = "EBE"
            sig_signe = -1
            cr_rubrique = "Charges de personnel"
            nature_defaut = "fixe"
        elif n.startswith("65"):
            sig_solde = "Resultat d exploitation"
            sig_signe = -1
            cr_rubrique = "Autres charges de gestion courante"
            nature_defaut = "fixe"
        elif n.startswith("66"):
            sig_solde = "RCAI"
            sig_signe = -1
            cr_rubrique = "Charges financieres"
            nature_defaut = "fixe"
        elif n.startswith("67"):
            sig_solde = "Resultat exceptionnel"
            sig_signe = -1
            cr_rubrique = "Charges exceptionnelles"
            nature_defaut = "fixe"
        elif n.startswith("681"):
            sig_solde = "Resultat d exploitation"
            sig_signe = -1
            cr_rubrique = "DAP exploitation"
            nature_defaut = "fixe"
        elif n.startswith("686"):
            sig_solde = "RCAI"
            sig_signe = -1
            cr_rubrique = "DAP financier"
            nature_defaut = "fixe"
        elif n.startswith("687"):
            sig_solde = "Resultat exceptionnel"
            sig_signe = -1
            cr_rubrique = "DAP exceptionnel"
            nature_defaut = "fixe"
        elif n.startswith("68"):
            sig_solde = "Resultat d exploitation"
            sig_signe = -1
            cr_rubrique = "DAP"
            nature_defaut = "fixe"
        elif n.startswith("691"):
            sig_solde = "Resultat de l exercice"
            sig_signe = -1
            cr_rubrique = "Participation des salaries"
            nature_defaut = "fixe"
        elif n.startswith("69"):
            sig_solde = "Resultat de l exercice"
            sig_signe = -1
            cr_rubrique = "Impots sur les benefices"
            nature_defaut = "fixe"

    # ===== CLASSE 7 — PRODUITS =====
    elif classe == 7:
        cr_signe = 1

        if n.startswith("707"):
            sig_solde = "Marge commerciale"
            sig_signe = 1
            cr_rubrique = "Ventes de marchandises"
            nature_defaut = "variable"
        elif n.startswith("70"):
            sig_solde = "Production de l exercice"
            sig_signe = 1
            cr_rubrique = "Production vendue"
            nature_defaut = "variable"
        elif n.startswith("713"):
            sig_solde = "Production de l exercice"
            sig_signe = 1
            cr_rubrique = "Production stockee"
            nature_defaut = "variable"
        elif n.startswith("71"):
            sig_solde = "Production de l exercice"
            sig_signe = 1
            cr_rubrique = "Production stockee"
            nature_defaut = "variable"
        elif n.startswith("72"):
            sig_solde = "Production de l exercice"
            sig_signe = 1
            cr_rubrique = "Production immobilisee"
            nature_defaut = "variable"
        elif n.startswith("74"):
            sig_solde = "EBE"
            sig_signe = 1
            cr_rubrique = "Subventions d exploitation"
            nature_defaut = "fixe"
        elif n.startswith("75"):
            sig_solde = "Resultat d exploitation"
            sig_signe = 1
            cr_rubrique = "Autres produits de gestion courante"
            nature_defaut = "fixe"
        elif n.startswith("76"):
            sig_solde = "RCAI"
            sig_signe = 1
            cr_rubrique = "Produits financiers"
            nature_defaut = "fixe"
        elif n.startswith("77"):
            sig_solde = "Resultat exceptionnel"
            sig_signe = 1
            cr_rubrique = "Produits exceptionnels"
            nature_defaut = "fixe"
        elif n.startswith("781"):
            sig_solde = "Resultat d exploitation"
            sig_signe = 1
            cr_rubrique = "Reprises exploitation"
            nature_defaut = "fixe"
        elif n.startswith("786"):
            sig_solde = "RCAI"
            sig_signe = 1
            cr_rubrique = "Reprises financier"
            nature_defaut = "fixe"
        elif n.startswith("787"):
            sig_solde = "Resultat exceptionnel"
            sig_signe = 1
            cr_rubrique = "Reprises exceptionnel"
            nature_defaut = "fixe"
        elif n.startswith("78"):
            sig_solde = "Resultat d exploitation"
            sig_signe = 1
            cr_rubrique = "Reprises"
            nature_defaut = "fixe"
        elif n.startswith("791"):
            sig_solde = "Resultat d exploitation"
            sig_signe = 1
            cr_rubrique = "Transferts de charges exploitation"
            nature_defaut = "fixe"
        elif n.startswith("796"):
            sig_solde = "RCAI"
            sig_signe = 1
            cr_rubrique = "Transferts de charges financieres"
            nature_defaut = "fixe"
        elif n.startswith("797"):
            sig_solde = "Resultat exceptionnel"
            sig_signe = 1
            cr_rubrique = "Transferts de charges exceptionnelles"
            nature_defaut = "fixe"
        elif n.startswith("79"):
            sig_solde = "Resultat d exploitation"
            sig_signe = 1
            cr_rubrique = "Transferts de charges"
            nature_defaut = "fixe"
        else:
            cr_rubrique = "Autres produits"

    return (sig_solde, sig_signe, cr_rubrique, cr_signe, bilan_poste, bilan_section, bf_categorie, nature_defaut)


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# Generate SQL
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    out.write("-- ============================================\n")
    out.write("-- Seed: pcg_analytique — 1 412 comptes PCG\n")
    out.write("-- Source: Pennylane API sandbox /ledger_accounts\n")
    out.write("-- Mapping analytique: SIG, CR, Bilan, BF, V/F\n")
    out.write("-- ============================================\n\n")
    out.write("-- Nettoyage prealable (idempotent)\n")
    out.write("DELETE FROM pcg_analytique;\n\n")
    out.write("INSERT INTO pcg_analytique (numero, libelle, classe, sig_solde, sig_signe, cr_rubrique, cr_signe, bilan_poste, bilan_section, bf_categorie, nature_defaut) VALUES\n")

    lines = []
    for acc in accounts:
        num = acc["number"]
        label = acc["label"]
        classe = int(num[0]) if num and num[0].isdigit() else 0
        mapping = get_mapping(num)

        line = f"({sql_val(num)}, {sql_val(label)}, {classe}, {sql_val(mapping[0])}, {sql_val(mapping[1])}, {sql_val(mapping[2])}, {sql_val(mapping[3])}, {sql_val(mapping[4])}, {sql_val(mapping[5])}, {sql_val(mapping[6])}, {sql_val(mapping[7])})"
        lines.append(line)

    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            out.write(f"{line},\n")
        else:
            out.write(f"{line};\n")

    out.write(f"\n-- Total: {len(lines)} comptes PCG inseres\n")

print(f"Generated {OUTPUT_FILE} with {len(accounts)} accounts")
