# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🎯 Aperçu du projet

HMA est un stack d'entreprise self-hosted qui centralise la gestion métier (ERP, CRM, BI, monitoring, sécurité) sur une infrastructure VPS Hostinger pilotée par Coolify. Ce dépôt est le **point d'entrée unique** : documentation, inventaire des services, scripts d'automatisation et roadmap.

---

## 🏗️ Architecture globale

```
Utilisateurs → HTTPS → Traefik (SSL Let's Encrypt) → Coolify → Conteneurs Docker
                                    ↓
                          VPS Hostinger (Ubuntu 24.04)
                          IP / accès dans .env
                          Wildcard DNS *.hma.business
```

| Couche | Technologie | Détails |
|---|---|---|
| Hébergement | Hostinger VPS | Ubuntu 24.04 LTS, SSH clé uniquement |
| PaaS | Coolify v4 (self-hosted) | Orchestration Docker, déploiement automatisé |
| Reverse Proxy / SSL | Traefik (intégré Coolify) | Certificats Let's Encrypt automatiques |
| DNS | Hostinger Zone DNS | Wildcard `*.hma.business` → VPS |
| BDD | PostgreSQL 16 | Instance dédiée par service |
| Cache | Redis 7 | Pour services nécessitant du cache |
| CI/CD | GitHub Actions | Organisation `hmagestion` |
| Sécurité VPS | UFW, fail2ban, sysctl | `hardening.sh` |

**Services déployés** : Coolify, Traefik, Odoo 18 (ERP/CRM), Apache Superset (BI), n8n (Workflow Automation), Uptime Kuma (monitoring), Vaultwarden (mots de passe)

> Tout nouveau service déployé via Coolify est automatiquement accessible sur `[nom].hma.business` sans modification DNS.

---

## 📂 Structure du dépôt

| Fichier / Dossier | Rôle |
|---|---|
| `README.md` | Point d'entrée, vue d'ensemble du stack |
| `docs/stack.md` | Architecture technique, choix infra, DNS, Docker |
| `docs/services.md` | Inventaire des services déployés (tableaux par catégorie) |
| `docs/runbooks.md` | Procédures opérationnelles (déploiement, incidents, backups) |
| `scripts/vw-*.sh` | Scripts d'automatisation Vaultwarden (auth, backup, audit, ajout, healthcheck) |
| `hardening.sh` | Script de sécurisation du VPS |
| `.env` | Variables sensibles — **gitignored** |
| `.specify/` | Templates et mémoire Specify (spec-driven development) |
| `backups/` | Exports Vaultwarden horodatés — **gitignored** |

---

## 🔧 Commandes utiles

### Scripts Vaultwarden (API OAuth 2.0)

Tous les scripts chargent automatiquement le `.env` pour l'authentification.

```bash
# Health check complet (HTTP, API, OAuth, Admin)
./scripts/vw-healthcheck.sh

# Audit du coffre (liste les éléments, stats, vérifications sécurité)
./scripts/vw-audit.sh

# Backup chiffré horodaté (rotation automatique des 30 derniers)
./scripts/vw-backup.sh [dossier_destination]

# Ajouter un identifiant
./scripts/vw-add.sh "Nom du service" "utilisateur" "mot_de_passe" "https://url"

# Obtenir un token OAuth (utilisé par les autres scripts)
source scripts/vw-auth.sh
```

### Déploiement via API Coolify

```bash
# Lister les services
curl -s "https://coolify.hma.business/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

# Démarrer un service
curl -s -X POST "https://coolify.hma.business/api/v1/services/{uuid}/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

---

## 📝 Règles d'édition

- Toujours écrire en **français**
- Maintenir les tableaux Markdown **alignés et lisibles**
- Mettre à jour la date "Dernière mise à jour" dans le README lors de chaque modification significative
- Les statuts de services utilisent ces émojis normalisés :
  - ✅ `Actif` · 🚧 `En cours` · ⏸️ `Suspendu` · 🔴 `Inactif` · 🧪 `Test`

---

## 🔄 Conventions

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

## 🎨 Style visuel

- Interface claire et minimaliste
- Pas de mode sombre pour le MVP

---

## 🔒 Contraintes et Politiques

- NE JAMAIS exposer les clés API au client
- NE JAMAIS committer de secrets — tout passe par `.env` (gitignored) et Vaultwarden
- Préférer les composants existants plutôt que d'ajouter de nouvelles bibliothèques UI
- Privilégier les images Docker officielles pour les services

---

## 🧪 Tests

À la fin de chaque développement impliquant l'interface graphique :
- Tester avec playwright-skill — l'interface doit être responsive, fonctionnelle et répondre au besoin développé

---

## 📚 Documentation

| Document | Description |
|---|---|
| [PRD.md](PRD.md) | Product Requirements Document — exigences produit |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture technique détaillée |
| [docs/stack.md](docs/stack.md) | Choix techniques et infrastructure |
| [docs/services.md](docs/services.md) | Inventaire des services déployés |
| [docs/runbooks.md](docs/runbooks.md) | Procédures opérationnelles |

---

## 🔍 Context7

Utiliser **toujours** Context7 (MCP) lorsqu'il y a besoin de :
- Génération de code
- Étapes de configuration ou d'installation
- Documentation de bibliothèque / API

Utiliser automatiquement les outils MCP Context7 (`resolve-library-id` puis `query-docs`) pour obtenir la documentation à jour, sans que l'utilisateur ait à le demander.

---

## 🛠️ Specify (Spec-Driven Development)

Ce dépôt utilise **Specify** (spec-kit) pour le développement piloté par spécifications.
Slash commands : `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`, `/speckit.clarify`, `/speckit.analyze`, `/speckit.checklist`.

---

## 📝 Spécifications

- Toutes les spécifications doivent être rédigées en **français**, y compris les sections Purpose et Scenarios des specs Spec-Kit
- Seuls les titres de Requirements doivent rester en **anglais** avec les mots-clés `SHALL` / `MUST` pour la validation Spec-Kit
