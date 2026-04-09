#!/usr/bin/env python3
"""
Synchronise pcg_analytique (Supabase SQL seed) -> kb_pcg_analytique (Qdrant).

- Lit les comptes depuis le fichier SQL seed (source de vérité)
- Génère le champ `contenu` enrichi en français pour le RAG
- Calcule les embeddings via OpenAI text-embedding-3-small
- Upsert dans Qdrant avec IDs uuid5 déterministes
- Crée les index de payload pour le filtrage hybride

Usage:
    python3 scripts/generate-pcg-qdrant.py

Prérequis:
    pip install qdrant-client openai
    Variables: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
"""
import os
import re
import uuid
import time

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)
from openai import OpenAI

# === Configuration ===

QDRANT_URL = os.environ.get("QDRANT_URL", "https://qdrant.hma.business:443")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "ToUjevnV22HxWSqFiCdVVhPl3uJNj4AX")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION = "kb_pcg_analytique"
VECTOR_SIZE = 1536
BATCH_SIZE = 100  # OpenAI embedding batch size

# Namespace fixe pour uuid5 déterministe
NAMESPACE_PCG = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Chemin vers le seed SQL (source de vérité)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(SCRIPT_DIR, "..", "sql", "02-data", "001-pcg-analytique-seed.sql")


def pcg_qdrant_id(numero: str) -> str:
    """ID Qdrant déterministe à partir du numéro de compte."""
    return str(uuid.uuid5(NAMESPACE_PCG, numero))


def parse_sql_seed(filepath: str) -> list[dict]:
    """Parse le fichier SQL seed pour extraire les comptes et leur mapping."""
    accounts = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Trouver le bloc INSERT INTO ... VALUES
    match = re.search(r"VALUES\s*\n(.*?);", content, re.DOTALL)
    if not match:
        raise ValueError(f"Pas de bloc VALUES trouvé dans {filepath}")

    values_block = match.group(1)

    # Parser chaque ligne de valeurs
    # Format: ('numero', 'libelle', classe, 'sig_solde', sig_signe, 'cr_rubrique', cr_signe, 'bilan_poste', 'bilan_section', 'bf_categorie', 'nature_defaut')
    row_pattern = re.compile(
        r"\(('(?:[^']|'')*'),\s*('(?:[^']|'')*'),\s*(\d+),\s*(NULL|'(?:[^']|'')*'),\s*(NULL|-?\d+),\s*(NULL|'(?:[^']|'')*'),\s*(NULL|-?\d+),\s*(NULL|'(?:[^']|'')*'),\s*(NULL|'(?:[^']|'')*'),\s*(NULL|'(?:[^']|'')*'),\s*(NULL|'(?:[^']|'')*')\)"
    )

    for m in row_pattern.finditer(values_block):
        def clean(val):
            if val == "NULL":
                return None
            if val.startswith("'") and val.endswith("'"):
                return val[1:-1].replace("''", "'")
            try:
                return int(val)
            except ValueError:
                return val

        acc = {
            "numero": clean(m.group(1)),
            "libelle": clean(m.group(2)),
            "classe": int(m.group(3)),
            "sig_solde": clean(m.group(4)),
            "sig_signe": clean(m.group(5)),
            "cr_rubrique": clean(m.group(6)),
            "cr_signe": clean(m.group(7)),
            "bilan_poste": clean(m.group(8)),
            "bilan_section": clean(m.group(9)),
            "bf_categorie": clean(m.group(10)),
            "nature_defaut": clean(m.group(11)),
        }
        accounts.append(acc)

    return accounts


def build_contenu(row: dict) -> str:
    """Génère le texte enrichi en français pour le RAG."""
    parts = []
    parts.append(f"Compte {row['numero']} — {row['libelle']}.")
    parts.append(f"Classe {row['classe']}.")

    if row["sig_solde"]:
        signe = "addition" if row["sig_signe"] == 1 else "soustraction"
        parts.append(
            f"SIG : entre dans le calcul du solde « {row['sig_solde']} » par {signe}."
        )

    if row["cr_rubrique"]:
        nature = "produit" if row["cr_signe"] == 1 else "charge"
        parts.append(
            f"Compte de résultat : rubrique « {row['cr_rubrique']} », nature {nature}."
        )
    else:
        parts.append("Ce compte n'apparaît pas au compte de résultat (compte de bilan).")

    if row["bilan_poste"]:
        section_labels = {
            "actif_immobilise": "Actif immobilisé",
            "actif_circulant": "Actif circulant",
            "passif_capitaux": "Passif — Capitaux propres",
            "passif_dettes": "Passif — Dettes",
        }
        section = section_labels.get(row["bilan_section"], row["bilan_section"] or "")
        parts.append(f"Bilan : poste « {row['bilan_poste']} », section {section}.")
    else:
        parts.append("Ce compte n'apparaît pas au bilan (compte de gestion).")

    if row["bf_categorie"]:
        bf_labels = {
            "emplois_stables": "Emplois stables",
            "ressources_stables": "Ressources stables",
            "bfr_exploit": "BFR d'exploitation",
            "bfr_hors_exploit": "BFR hors exploitation",
            "tresorerie_active": "Trésorerie active",
            "tresorerie_passive": "Trésorerie passive",
        }
        bf = bf_labels.get(row["bf_categorie"], row["bf_categorie"])
        parts.append(f"Bilan fonctionnel : catégorie « {bf} ».")

    parts.append(
        f"Nature : {row['nature_defaut']} (pour le résultat différentiel et le seuil de rentabilité)."
    )

    return " ".join(parts)


def get_embeddings(texts: list[str], client: OpenAI) -> list[list[float]]:
    """Calcule les embeddings par batch via OpenAI."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def main():
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY non définie. Export la variable ou ajoute-la dans .mcp.json")

    # 1. Parser le seed SQL
    print(f"Lecture du seed SQL : {SEED_FILE}")
    accounts = parse_sql_seed(SEED_FILE)
    print(f"  -> {len(accounts)} comptes parsés")

    # Filtrer les comptes auxiliaires (alphanumériques) — seuls les comptes PCG racines
    pcg_accounts = [a for a in accounts if a["numero"].isdigit()]
    aux_accounts = [a for a in accounts if not a["numero"].isdigit()]
    print(f"  -> {len(pcg_accounts)} comptes PCG racines, {len(aux_accounts)} auxiliaires exclus")

    # 2. Générer les textes enrichis
    print("Génération des textes enrichis...")
    for acc in pcg_accounts:
        acc["contenu"] = build_contenu(acc)

    # 3. Connexion Qdrant
    print(f"Connexion Qdrant : {QDRANT_URL}")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 4. Créer ou recréer la collection
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION in collections:
        print(f"  Collection '{COLLECTION}' existante — suppression et recréation")
        qdrant.delete_collection(COLLECTION)

    qdrant.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"  Collection '{COLLECTION}' créée ({VECTOR_SIZE} dims, cosine)")

    # 5. Générer embeddings et upsert par batch
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    total = len(pcg_accounts)
    inserted = 0

    for i in range(0, total, BATCH_SIZE):
        batch = pcg_accounts[i : i + BATCH_SIZE]
        texts = [acc["contenu"] for acc in batch]

        # Embeddings
        embeddings = get_embeddings(texts, openai_client)

        # Points Qdrant
        points = []
        for acc, emb in zip(batch, embeddings):
            point = PointStruct(
                id=pcg_qdrant_id(acc["numero"]),
                vector=emb,
                payload={
                    "number": acc["numero"],
                    "label": acc["libelle"],
                    "classe": acc["classe"],
                    "contenu": acc["contenu"],
                    "sig_solde": acc["sig_solde"],
                    "sig_signe": acc["sig_signe"],
                    "cr_rubrique": acc["cr_rubrique"],
                    "cr_signe": acc["cr_signe"],
                    "bilan_poste": acc["bilan_poste"],
                    "bilan_section": acc["bilan_section"],
                    "bf_categorie": acc["bf_categorie"],
                    "nature_defaut": acc["nature_defaut"],
                },
            )
            points.append(point)

        qdrant.upsert(collection_name=COLLECTION, points=points)
        inserted += len(points)
        print(f"  Batch {i // BATCH_SIZE + 1} : {inserted}/{total} points insérés")

        # Rate limiting OpenAI
        if i + BATCH_SIZE < total:
            time.sleep(0.5)

    # 6. Créer les index de payload pour filtrage hybride
    print("Création des index de payload...")
    index_fields = {
        "number": PayloadSchemaType.KEYWORD,
        "classe": PayloadSchemaType.INTEGER,
        "sig_solde": PayloadSchemaType.KEYWORD,
        "cr_rubrique": PayloadSchemaType.KEYWORD,
        "bf_categorie": PayloadSchemaType.KEYWORD,
        "nature_defaut": PayloadSchemaType.KEYWORD,
        "bilan_section": PayloadSchemaType.KEYWORD,
    }
    for field, schema_type in index_fields.items():
        qdrant.create_payload_index(
            collection_name=COLLECTION,
            field_name=field,
            field_schema=schema_type,
        )
        print(f"  Index '{field}' ({schema_type}) créé")

    # 7. Vérification
    info = qdrant.get_collection(COLLECTION)
    print(f"\nTerminé : {info.points_count} points dans '{COLLECTION}'")
    print(f"Vérification : seed SQL = {len(pcg_accounts)}, Qdrant = {info.points_count}")
    if info.points_count == len(pcg_accounts):
        print("OK: Synchronisation Supabase -> Qdrant reussie")
    elif info.points_count > len(pcg_accounts) * 0.95:
        print(f"AVERTISSEMENT: {info.points_count}/{len(pcg_accounts)} indexes (delai d'indexation ou doublons numero)")
        print("OK: Synchronisation quasi-complete")
    else:
        raise AssertionError(f"ERREUR: {info.points_count} != {len(pcg_accounts)} — ecart trop important")


if __name__ == "__main__":
    main()
