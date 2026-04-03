# Contrat API Pennylane — Sync Chantier A

**Version API**: v2
**Base URL**: `https://app.pennylane.com/api/external/v2`
**Auth**: Bearer token (lecture seule, stocké dans Vaultwarden)

## Endpoint principal : /ledger_entries

**Méthode**: GET
**Pagination**: `page` (1-based), 100 résultats par page max
**Filtre incrémental**: `updated_at[gte]=YYYY-MM-DDTHH:MM:SS`

### Paramètres

| Param | Type | Description |
|---|---|---|
| page | integer | Numéro de page (défaut: 1) |
| per_page | integer | Résultats par page (max: 100) |
| updated_at[gte] | datetime | Filtre incrémental depuis dernière sync |
| journal_code | string | Filtrer par code journal |

### Réponse

```json
{
  "ledger_entries": [
    {
      "id": 12345,
      "document_number": "AC-2025-001",
      "date": "2025-03-15",
      "label": "Achat marchandises",
      "debit": 1500.00,
      "credit": 0.00,
      "lettering_code": "AA001",
      "lettering_date": "2025-04-01",
      "validated_at": "2025-03-20",
      "journal": {
        "code": "AC",
        "label": "Journal des achats"
      },
      "planitem": {
        "number": "607",
        "label": "Achats de marchandises",
        "auxiliary_code": null,
        "auxiliary_label": null
      }
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 42,
    "per_page": 100,
    "total": 4150
  }
}
```

### Mapping → fec_ecriture

| Champ FEC | JSON path |
|---|---|
| journal_code | `journal.code` |
| journal_lib | `journal.label` |
| ecriture_num | `document_number` |
| ecriture_date | `date` |
| compte_num | `planitem.number` (+ `auxiliary_code` si présent) |
| compte_lib | `planitem.label` |
| comp_aux_num | `planitem.auxiliary_code` |
| comp_aux_lib | `planitem.auxiliary_label` |
| piece_ref | `document_number` |
| piece_date | `date` |
| ecriture_lib | `label` |
| debit | `debit` |
| credit | `credit` |
| ecriture_let | `lettering_code` |
| date_let | `lettering_date` |
| valid_date | `validated_at` |

## Endpoints secondaires (référence)

| Endpoint | Usage Chantier A |
|---|---|
| `/ledger_accounts` | Vérification croisée du plan comptable (optionnel) |
| `/trial_balance` | Validation des vues matérialisées (phase A5) |
| `/journals` | Liste des journaux pour référence |

## Gestion des erreurs

| Code | Signification | Action |
|---|---|---|
| 200 | OK | Traiter les données |
| 401 | Token expiré/invalide | Alerter, arrêter la sync |
| 429 | Rate limit | Attendre 60s, retry |
| 500 | Erreur serveur | Retry 3x avec backoff, puis alerter |

## Tokens par structure

| Structure | Entrée Vaultwarden |
|---|---|
| HMA | `Pennylane API — HMA` |
| STIVMAT | `Pennylane API — STIVMAT` |
| STA | `Pennylane API — STA` |
| ETPA | `Pennylane API — ETPA` |
