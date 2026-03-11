# 📦 Inventaire des Services Déployés

> Liste exhaustive de tous les services actifs, en cours de déploiement ou planifiés sur l'infrastructure HMA.
> Mettre à jour ce fichier à chaque changement d'état d'un service.

**Légende des statuts :**
✅ `Actif` · 🚧 `En cours` · ⏸️ `Suspendu` · 🔴 `Inactif` · 🧪 `Test`

---

## 🏗️ Infrastructure

| Nom | Rôle | URL | Hébergeur | Statut | Notes |
|---|---|---|---|---|---|
| Coolify | PaaS self-hosted | [coolify.hma.business](https://coolify.hma.business) | Hostinger VPS | ✅ Actif | Serveur principal de déploiement |
| Traefik | Reverse proxy / SSL | — | Hostinger VPS | ✅ Actif | Intégré Coolify — SSL Let's Encrypt automatique |

---

## 🔧 Outils Internes

| Nom | Rôle | URL | Instance Coolify | Statut | Dépôt GitHub | Notes |
|---|---|---|---|---|---|---|
| Uptime Kuma | Monitoring / Status page | [status.hma.business](https://status.hma.business) | hma-uptime-kuma | ✅ Actif | — | Surveillance des services |
| Vaultwarden | Gestionnaire de mots de passe | [vault.hma.business](https://vault.hma.business) | hma-vaultwarden | ✅ Actif | — | Compatible clients Bitwarden |

---

## 🌐 Services Applicatifs (Projet Coolify : `hma-apps`)

| Nom | Description | URL | Statut | Tech |
|---|---|---|---|---|
| Odoo 18 | ERP / CRM open-source | [odoo.hma.business](https://odoo.hma.business) | ✅ Actif | Python / Docker |
| Apache Superset | BI / Data Visualization | [superset.hma.business](https://superset.hma.business) | ✅ Actif | Python / Docker |
| n8n | Workflow Automation | [n8n.hma.business](https://n8n.hma.business) | ✅ Actif | Node.js / Docker |

---

## 🗃️ Bases de Données

| Nom | Type | Service lié | Instance Coolify | Statut | Sauvegarde | Notes |
|---|---|---|---|---|---|---|
| odoo-db | PostgreSQL 16 | Odoo ERP | hma-apps | ✅ Actif | — | Base dédiée Odoo |
| superset-db | PostgreSQL 16 | Apache Superset | hma-apps | ✅ Actif | — | Base dédiée Superset |
| n8n-db | PostgreSQL 16 | n8n | hma-apps | ✅ Actif | — | Base dédiée n8n |

---

## 🤖 Services IA

| Nom | Modèle / API | Usage | Environnement | Statut | Notes |
|---|---|---|---|---|---|
| *(à compléter)* | API Anthropic | — | Production | — | — |

---

## 📂 Organisation des Projets Coolify

| Projet Coolify | Rôle | Services |
|---|---|---|
| `hma-monitoring` | Outils internes / infra | Uptime Kuma, Vaultwarden |
| `hma-apps` | Services métier | Odoo 18 + PostgreSQL, Apache Superset + PostgreSQL + Redis, n8n + PostgreSQL |

> **Convention** : tout nouveau service métier est déployé dans le projet `hma-apps`.

---

## 📋 Modèle pour ajouter un service

Copier-coller ce bloc dans la section appropriée lors de l'ajout d'un nouveau service :

```markdown
| Nom du service | Description courte | https://... | hma-[nom]-production | ✅ Actif | github.com/hmagestion/[repo] | Node.js / Docker |
```

---

## 🗓️ Historique des changements

| Date | Service | Action | Notes |
|---|---|---|---|
| 2026-03 | — | Initialisation du dépôt | — |
| 2026-03 | Coolify | DNS configuré + SSL actif | `coolify.hma.business` opérationnel |
| 2026-03 | DNS `hma.business` | Zone DNS Hostinger configurée | `A @`, `A www`, `A coolify`, `A *` pointent vers le VPS |
| 2026-03 | VPS Hostinger | Hardening sécurité | UFW, fail2ban, SSH clé uniquement, sysctl durci |
| 2026-03 | Uptime Kuma | Déployé via Coolify | `status.hma.business` opérationnel |
| 2026-03 | Vaultwarden | Déployé via Coolify | `vault.hma.business` opérationnel, inscriptions désactivées |
| 2026-03 | Odoo 18 | Déployé via Coolify | `odoo.hma.business` opérationnel — ERP/CRM |
| 2026-03 | Apache Superset | Déployé via Coolify | `superset.hma.business` opérationnel — BI |
| 2026-03 | n8n | Déployé via Coolify | `n8n.hma.business` opérationnel — Workflow Automation |
| 2026-03 | OpenProject | Échec déploiement | Conteneur crash — RAM VPS insuffisante (min 4GB requis) |
| 2026-03 | Projets Coolify | Réorganisation | Projet `hma-apps` créé, `hma-openproject` supprimé |

---

*Dernière mise à jour : Mars 2026 — HMA* · Coolify ✅ `coolify.hma.business`
