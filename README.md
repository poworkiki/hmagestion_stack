# 🏢 HMA — Suivi du Stack d'Entreprise

> Dépôt central de documentation, d'inventaire et de roadmap du stack technique HMA.

[![Stack](https://img.shields.io/badge/Hébergement-Hostinger-purple)](https://hostinger.fr)
[![Deploy](https://img.shields.io/badge/Déploiement-Coolify-blue)](https://coolify.hma.business)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-black)](https://github.com/features/actions)
[![Open Source](https://img.shields.io/badge/Philosophie-Open%20Source-green)](#)
[![DNS](https://img.shields.io/badge/Domaine-hma.business-orange)](https://hma.business)

---

## 📋 Table des matières

- [À propos](#-à-propos)
- [Stack technologique](#️-stack-technologique)
- [Services déployés](#-services-déployés)
- [Documentation](#-documentation)
- [Roadmap](#-roadmap)
- [Contribuer](#-contribuer)

---

## 🎯 À propos

Ce dépôt est le **point d'entrée unique** pour le suivi du stack d'entreprise HMA. Il centralise :

- 📐 La documentation de l'architecture et des choix techniques
- 📦 L'inventaire de tous les services déployés (Coolify / Hostinger)
- 🗺️ La roadmap et le suivi des évolutions via GitHub Issues

---

## 🛠️ Stack Technologique

| Rôle | Technologie | URL | Documentation |
|---|---|---|---|
| ☁️ Hébergement | Hostinger VPS/Cloud | — | [docs/stack.md](docs/stack.md) |
| 🌐 DNS | Hostinger Zone DNS | `*.hma.business` | [docs/stack.md](docs/stack.md) |
| 🚀 Déploiement | Coolify (self-hosted PaaS) | [coolify.hma.business](https://coolify.hma.business) | [docs/stack.md](docs/stack.md) |
| 🔁 Versioning & CI/CD | GitHub + GitHub Actions | [github.com/hmagestion](https://github.com/hmagestion) | [docs/stack.md](docs/stack.md) |
| 🤖 Intelligence Artificielle | API Anthropic + OSS | — | [docs/stack.md](docs/stack.md) |
| 💻 Développement | VS Code + Claude Code | — | [CLAUDE.md](CLAUDE.md) |

---

## 📦 Services Déployés

Voir le fichier détaillé → **[docs/services.md](docs/services.md)**

| Nom du service | Type | URL | Statut |
|---|---|---|---|
| Coolify | Infrastructure / PaaS | [coolify.hma.business](https://coolify.hma.business) | ✅ Actif |
| Traefik | Reverse Proxy / SSL | — | ✅ Actif |
| Uptime Kuma | Monitoring | [status.hma.business](https://status.hma.business) | ✅ Actif |
| Vaultwarden | Mots de passe | [vaultwarden.poworkiki.cloud](https://vaultwarden.poworkiki.cloud) | ✅ Actif |
| Odoo 18 | ERP / CRM | [odoo.hma.business](https://odoo.hma.business) | ✅ Actif |
| Apache Superset | BI / Data Visualization | [superset.hma.business](https://superset.hma.business) | ✅ Actif |
| n8n | Workflow Automation | [n8n.hma.business](https://n8n.hma.business) | ✅ Actif |
| Appsmith | Low-code / Saisie | [appsmith.hma.business](https://appsmith.hma.business) | ✅ Actif |
| pgAdmin 4 | Admin PostgreSQL | [pgadmin.hma.business](https://pgadmin.hma.business) | ✅ Actif |

---

## 📚 Documentation

| Document | Description |
|---|---|
| [docs/stack.md](docs/stack.md) | Architecture globale et choix techniques |
| [docs/services.md](docs/services.md) | Inventaire des services déployés |
| [docs/runbooks.md](docs/runbooks.md) | Procédures opérationnelles |
| [CLAUDE.md](CLAUDE.md) | Instructions pour Claude Code (IA) |

---

## 🗺️ Roadmap

Le suivi des évolutions est géré via les **[GitHub Issues](../../issues)** avec les labels suivants :

| Label | Description |
|---|---|
| `roadmap` | Fonctionnalité planifiée |
| `bug` | Problème sur un service existant |
| `infra` | Évolution infrastructure |
| `documentation` | Amélioration de la doc |
| `service-nouveau` | Ajout d'un nouveau service |
| `service-migration` | Migration d'un service existant |

👉 Voir le **[tableau de bord Roadmap](../../issues?q=is%3Aissue+label%3Aroadmap)**

---

## 🤝 Contribuer

1. Ouvrir une **Issue** avec le bon label
2. Créer une branche `feature/[nom]` ou `fix/[nom]`
3. Soumettre une **Pull Request** vers `main`
4. Respecter les conventions définies dans [CLAUDE.md](CLAUDE.md)

---

*Maintenu par l'équipe HMA — Dernière mise à jour : Avril 2026 · Coolify ✅ · Uptime Kuma ✅ · Vaultwarden ✅ · Odoo ✅ · Superset ✅ · n8n ✅ · Appsmith ✅ · pgAdmin ✅*
