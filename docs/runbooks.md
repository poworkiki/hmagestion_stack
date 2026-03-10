# 📖 Runbooks — Procédures Opérationnelles HMA

> Procédures pas-à-pas pour les opérations courantes et la gestion des incidents.

---

## 🚀 Déployer un nouveau service

### Prérequis
- Accès Coolify → [coolify.hma.business](https://coolify.hma.business)
- Dépôt GitHub créé dans l'organisation `hmagestion` avec `Dockerfile` ou `docker-compose.yml`
- Variables d'environnement listées dans `.env.example`

### Étapes

1. **[coolify.hma.business](https://coolify.hma.business) → New Resource → GitHub Repository**
2. Sélectionner le dépôt `hmagestion/[nom-du-projet]`
3. Choisir la branche `main` (production)
4. Configurer :
   - Nom : `hma-[projet]-production`
   - Domaine : `[sous-domaine].hma.business` *(wildcard DNS déjà configuré ✅)*
   - Port exposé (selon `Dockerfile`)
5. Ajouter les variables d'environnement (depuis `.env.example`)
6. Activer le **webhook GitHub** pour le déploiement automatique
7. Lancer le premier déploiement manuel
8. Vérifier le healthcheck dans les logs Coolify
9. **Mettre à jour [`docs/services.md`](services.md)** avec le nouveau service

---

## 🔄 Mettre à jour un service existant

### Via CI/CD automatique (recommandé)
```
Push sur branche main → GitHub Actions → Coolify Webhook → Redéploiement automatique
```

### Via Coolify manuellement
1. Coolify → Sélectionner le service
2. Cliquer **"Redeploy"**
3. Surveiller les logs en temps réel

---

## 🔴 Gérer un incident / service down

### Diagnostic rapide
```bash
# 1. Vérifier les logs dans Coolify
# https://coolify.hma.business → Service → Logs

# 2. Vérifier l'état des conteneurs (SSH sur le VPS Hostinger)
ssh user@[ip-vps-hostinger]
docker ps -a | grep hma-[service]
docker logs hma-[service] --tail=100

# 3. Vérifier l'espace disque
df -h

# 4. Vérifier la mémoire
free -h
```

### Restart d'urgence
```bash
# Via Docker directement
docker restart hma-[service]-production

# Via Coolify : bouton "Restart" dans l'interface
```

### Rollback vers la version précédente
1. Coolify → Service → Deployments
2. Identifier le dernier déploiement stable
3. Cliquer **"Rollback"** sur ce déploiement

---

## 🗃️ Sauvegardes

### PostgreSQL — Backup manuel
```bash
# Sur le VPS Hostinger
docker exec hma-postgres pg_dump -U [user] [database] > backup_$(date +%Y%m%d).sql

# Compression
gzip backup_$(date +%Y%m%d).sql
```

### Restauration PostgreSQL
```bash
gunzip backup_YYYYMMDD.sql.gz
docker exec -i hma-postgres psql -U [user] [database] < backup_YYYYMMDD.sql
```

---

## 🔐 Renouvellement / Rotation des secrets

1. Générer le nouveau secret/token
2. Mettre à jour dans **Coolify → Service → Environment Variables**
3. Mettre à jour dans **GitHub Secrets** (si utilisé en CI/CD)
4. Redéployer le service concerné
5. Vérifier le bon fonctionnement
6. Révoquer l'ancien secret sur la plateforme source

---

## 🆕 Ajouter un dépôt GitHub dans l'organisation HMA

1. GitHub → `hmagestion` organisation → New Repository
2. Nommage : `hma-[type]-[nom]` (ex: `hma-app-crm`, `hma-infra-scripts`)
3. Initialiser avec :
   - `README.md`
   - `CLAUDE.md` (copier depuis `hmagestion_stack`)
   - `.gitignore` adapté au langage
   - `Dockerfile` ou `docker-compose.yml`
4. Configurer les **Branch Protection Rules** sur `main`
5. Référencer dans [`docs/services.md`](services.md)

---

*Dernière mise à jour : Mars 2026 — HMA · Coolify : [coolify.hma.business](https://coolify.hma.business)*
