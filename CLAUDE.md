# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Aperçu du projet

HMA est un stack d'entreprise self-hosted qui centralise la gestion métier (ERP, CRM, BI, monitoring, sécurité) sur une infrastructure VPS Hostinger pilotée par Coolify. Ce dépôt est le **point d'entrée unique** : documentation, inventaire des services, scripts d'automatisation et roadmap.

---

## Architecture globale

```
Utilisateurs → HTTPS → Traefik (SSL Let's Encrypt) → Coolify → Conteneurs Docker
                                    ↓
                          VPS Hostinger (Ubuntu 24.04)
                          Wildcard DNS *.hma.business
```

**Services déployés** : Coolify, Traefik, Odoo 18 (ERP/CRM), Apache Superset (BI), n8n (Workflow Automation), Uptime Kuma (monitoring), Vaultwarden (mots de passe), Metabase (BI/Analytics), Budibase (low-code platform).

Tout nouveau service déployé via Coolify est automatiquement accessible sur `[nom].hma.business` sans modification DNS (wildcard `*` configuré).

Détails techniques complets : `docs/stack.md` · Inventaire des services : `docs/services.md` · Procédures opérationnelles : `docs/runbooks.md`

---

## Commandes utiles

### Scripts Vaultwarden (API OAuth 2.0)

Tous les scripts chargent automatiquement le `.env` pour l'authentification. Variables requises dans `.env` : identifiants Vaultwarden, token API Coolify.

```bash
./scripts/vw-healthcheck.sh                              # Health check complet (HTTP, API, OAuth, Admin)
./scripts/vw-audit.sh                                     # Audit du coffre (éléments, stats, sécurité)
./scripts/vw-backup.sh [dossier_destination]              # Backup chiffré horodaté (rotation 30 derniers)
./scripts/vw-add.sh "Nom" "user" "pass" "https://url"    # Ajouter un identifiant
source scripts/vw-auth.sh                                 # Obtenir un token OAuth (utilisé par les autres scripts)
```

### Déploiement via API Coolify

```bash
curl -s "https://coolify.hma.business/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

curl -s -X POST "https://coolify.hma.business/api/v1/services/{uuid}/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

---

## Règles d'édition

- Toujours écrire en **français**
- Maintenir les tableaux Markdown **alignés et lisibles**
- Mettre à jour la date "Dernière mise à jour" dans le README lors de chaque modification significative
- Les statuts de services utilisent ces émojis normalisés :
  - ✅ `Actif` · 🚧 `En cours` · ⏸️ `Suspendu` · 🔴 `Inactif` · 🧪 `Test`

---

## Conventions

### Ajouter un service dans `docs/services.md`
Toujours renseigner **tous les champs** du tableau. Utiliser `—` si non applicable.
Ajouter une entrée dans "Historique des changements" en bas du fichier.

### Commits
Préfixe conventionnel obligatoire :
```
docs: ajout du service Mattermost dans l'inventaire
infra: déploiement Odoo via Coolify
chore: mise à jour des templates d'issues
fix: correction script vw-backup
```

### Nommage
```
Coolify :  hma-[projet]-[env]     → ex: hma-crm-production
GitHub :   hma-[type]-[nom]       → ex: hma-app-crm, hma-infra-scripts
Branches : main (prod) / develop (staging) / feature/* / fix/*
```

---

## Contraintes

- NE JAMAIS committer de secrets — tout passe par `.env` (gitignored) et Vaultwarden
- Privilégier les images Docker officielles pour les services
- Interface claire et minimaliste, pas de mode sombre pour le MVP

---

## Tests

À la fin de chaque développement impliquant l'interface graphique :
- Tester avec playwright-skill — l'interface doit être responsive, fonctionnelle et répondre au besoin développé

---

## Context7

Utiliser **toujours** Context7 (MCP) lorsqu'il y a besoin de :
- Génération de code
- Étapes de configuration ou d'installation
- Documentation de bibliothèque / API

Utiliser automatiquement les outils MCP Context7 (`resolve-library-id` puis `query-docs`) pour obtenir la documentation à jour, sans que l'utilisateur ait à le demander.

---

## Specify (Spec-Driven Development)

Ce dépôt utilise **Specify** (spec-kit) pour le développement piloté par spécifications.
Slash commands : `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`, `/speckit.clarify`, `/speckit.analyze`, `/speckit.checklist`.

- Toutes les spécifications doivent être rédigées en **français**, y compris les sections Purpose et Scenarios
- Seuls les titres de Requirements doivent rester en **anglais** avec les mots-clés `SHALL` / `MUST` pour la validation Spec-Kit
