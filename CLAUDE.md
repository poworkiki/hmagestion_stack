# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Nature du dépôt

Ce dépôt est un **dépôt de documentation et de suivi**, pas un dépôt de code applicatif.
Son contenu est principalement composé de fichiers Markdown, de templates et de configurations légères.

---

## ⚙️ Environnement de production

| Service | URL | Statut |
|---|---|---|
| Coolify (PaaS) | [coolify.hma.business](https://coolify.hma.business) | ✅ Actif |
| Domaine principal | `hma.business` | ✅ DNS configuré |
| Wildcard DNS | `*.hma.business` → VPS Hostinger | ✅ Actif |

> Tout nouveau service déployé via Coolify est automatiquement accessible sur `[nom].hma.business` sans modification DNS.

---

## 📂 Structure du dépôt

| Fichier | Rôle |
|---|---|
| `README.md` | Point d'entrée principal, vue d'ensemble du stack |
| `docs/stack.md` | Architecture technique, choix infra, DNS, Docker, CI/CD |
| `docs/services.md` | Inventaire des services déployés (tableaux par catégorie) |
| `docs/runbooks.md` | Procédures opérationnelles (déploiement, incidents, backups) |
| `CLAUDE.md` | Ce fichier |

---

## 📝 Règles d'édition

- Toujours écrire en **français**
- Maintenir les tableaux Markdown **alignés et lisibles**
- Mettre à jour la date "Dernière mise à jour" dans le README lors de chaque modification significative
- Les statuts de services utilisent ces émojis normalisés :
  - ✅ `Actif` — service en production, opérationnel
  - 🚧 `En cours` — déploiement ou migration en cours
  - ⏸️ `Suspendu` — service pausé temporairement
  - 🔴 `Inactif` — service arrêté
  - 🧪 `Test` — environnement de test/staging uniquement

---

## 🔄 Conventions de mise à jour

### Ajouter un service dans `services.md`
Toujours renseigner **tous les champs** du tableau avant de committer.
Ne pas laisser de cellules vides — utiliser `—` si l'information n'est pas applicable.
Ajouter une entrée dans la section "Historique des changements" en bas du fichier.

### Commits dans ce dépôt
Préfixe conventionnel obligatoire :
```
docs: ajout du service Mattermost dans l'inventaire
docs: mise à jour statut Nextcloud → Actif
chore: mise à jour des templates d'issues
```

### Convention de nommage Coolify
```
hma-[projet]-[env]    → ex: hma-crm-production, hma-wiki-staging
```

### Convention de nommage dépôts GitHub
```
hma-[type]-[nom]      → ex: hma-app-crm, hma-infra-scripts
```

---

## 🚫 Ce que ce dépôt ne contient PAS
- Code source applicatif (chaque service a son propre dépôt)
- Secrets ou variables d'environnement
- Fichiers binaires ou assets lourds
