# 🛠️ Architecture du Stack HMA

> Documentation des choix techniques et de l'architecture globale.

---

## Vue d'ensemble

```
                        ┌─────────────────────────┐
                        │       UTILISATEURS       │
                        └────────────┬────────────┘
                                     │ HTTPS
                        ┌────────────▼────────────┐
                        │    Reverse Proxy / SSL   │
                        │  (Coolify / Traefik)     │
                        └────────────┬────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                       │
   ┌──────────▼─────────┐ ┌─────────▼──────────┐ ┌────────▼────────┐
   │   Service A         │ │   Service B         │ │   Service C     │
   │   (Conteneur Docker)│ │   (Conteneur Docker)│ │   ...           │
   └──────────┬──────────┘ └─────────┬──────────┘ └────────┬────────┘
              │                      │                       │
              └──────────────────────▼──────────────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │   Hostinger VPS / Cloud  │
                        │   Ubuntu Linux           │
                        └─────────────────────────┘
```

---

## 🌐 DNS — hma.business

Zone DNS gérée chez **Hostinger**. Configuration wildcard pour couvrir tous les sous-domaines automatiquement.

| Type | Nom | Valeur | Statut |
|---|---|---|---|
| `A` | `@` | IP VPS Hostinger | ✅ Configuré |
| `A` | `www` | IP VPS Hostinger | ✅ Configuré |
| `A` | `coolify` | IP VPS Hostinger | ✅ Configuré |
| `A` | `*` | IP VPS Hostinger | ✅ Configuré |

> Le wildcard `*` couvre tous les futurs services sans modification DNS.
> SSL Let's Encrypt est géré automatiquement par Traefik (Coolify).

**Conventions de sous-domaines :**
```
coolify.hma.business      → Interface Coolify (admin)
[service].hma.business    → Services métier déployés via Coolify
```

---



| Paramètre | Valeur |
|---|---|
| Fournisseur | Hostinger |
| Type | VPS / Cloud |
| OS | Ubuntu 22.04 LTS |
| Philosophie | Auto-hébergé, données souveraines |

**Pourquoi Hostinger ?**
- Rapport qualité/prix compétitif pour l'auto-hébergement
- Serveurs en Europe (conformité données)
- Accès SSH complet et root

---

## 🚀 Déploiement — Coolify

| Paramètre | Valeur |
|---|---|
| Outil | Coolify v4 |
| Type | Self-hosted PaaS |
| Runtimes supportés | Docker, Nixpacks, Dockerfile, Docker Compose |
| SSL | Let's Encrypt automatique via Traefik |

**Pourquoi Coolify ?**
- Alternative open source à Heroku/Railway/Render
- Interface graphique pour gérer les déploiements
- Gestion des variables d'environnement sécurisée
- Webhooks GitHub pour le déploiement continu
- Monitoring et logs intégrés

**Conventions de nommage dans Coolify :**
```
hma-[projet]-[env]
Exemples :
  hma-crm-production
  hma-wiki-staging
  hma-analytics-production
```

---

## 🔁 Versioning & CI/CD — GitHub

| Paramètre | Valeur |
|---|---|
| Plateforme | GitHub (hmagestion organisation) |
| CI/CD | GitHub Actions |
| Stratégie de branches | `main` (prod) / `develop` (staging) / `feature/*` |

**Pipeline type :**
```
Push → GitHub Actions → Tests → Build Docker → Coolify Webhook → Déploiement
```

---

## 🤖 Intelligence Artificielle

| Cas d'usage | Solution | Notes |
|---|---|---|
| IA conversationnelle / agents | API Anthropic (Claude) | Modèles Sonnet/Haiku |
| Assistance développement | Claude Code (VS Code) | Via extension |
| Modèles internes / privés | Ollama (auto-hébergé) | Pour données sensibles |

**Principes :**
- Les clés API sont **exclusivement** dans les variables d'environnement
- Encapsuler les appels IA dans des services dédiés
- Préférer les modèles auto-hébergés pour les données confidentielles

---

## 🗃️ Bases de Données

| Type | Technologie | Usage |
|---|---|---|
| Relationnel | PostgreSQL | Données métier principales |
| Cache / Queue | Redis | Sessions, queues de tâches |
| Documents | *(si besoin)* | MongoDB ou PocketBase |

**Règles :**
- Toutes les BDD sont hébergées sur Hostinger via Coolify
- Migrations versionnées obligatoires (Prisma / Drizzle / Alembic)
- Sauvegardes automatiques configurées dans Coolify

---

## 🔒 Sécurité

| Mesure | Implémentation |
|---|---|
| SSL/TLS | Let's Encrypt automatique (Coolify/Traefik) |
| Secrets | GitHub Secrets (CI/CD) + Variables Coolify (runtime) |
| Accès SSH | Clés SSH uniquement, pas de mot de passe |
| Réseau | Isolation par réseau Docker dans Coolify |
| Sauvegardes | Coolify backup ou scripts cron sur Hostinger |

---

## 📦 Standards Docker

```dockerfile
# ✅ Bonne pratique : multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci --only=production

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app .
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
EXPOSE 3000
CMD ["node", "server.js"]
```

**Règles :**
- Images de base : préférer les variantes `-alpine` ou `-slim`
- Toujours définir un `HEALTHCHECK`
- Ne jamais utiliser le tag `latest` en production
- `.dockerignore` obligatoire dans chaque projet

---

*Dernière mise à jour : Mars 2026 — HMA*
