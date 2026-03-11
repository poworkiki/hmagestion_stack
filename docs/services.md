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

## 🌐 Services Applicatifs

| Nom | Description | URL | Environnement | Statut | Dépôt GitHub | Tech |
|---|---|---|---|---|---|---|
| *(à compléter)* | — | — | Production | — | — | — |

---

## 🗃️ Bases de Données

| Nom | Type | Service lié | Instance Coolify | Statut | Sauvegarde | Notes |
|---|---|---|---|---|---|---|
| *(à compléter)* | PostgreSQL | — | — | — | — | — |

---

## 🤖 Services IA

| Nom | Modèle / API | Usage | Environnement | Statut | Notes |
|---|---|---|---|---|---|
| *(à compléter)* | API Anthropic | — | Production | — | — |

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

---

*Dernière mise à jour : Mars 2026 — HMA* · Coolify ✅ `coolify.hma.business`
