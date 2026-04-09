# Recherche : Migration Odoo 17 vers Odoo 18

> Derniere mise a jour : 2026-04-06
> Sources : documentation officielle Odoo, GitHub OCA, GitHub odoo/owl

---

## Table des matieres

1. [Breaking changes Odoo 17 vers 18](#1-breaking-changes-odoo-17-vers-18)
2. [Changements OWL (framework frontend)](#2-changements-owl-framework-frontend)
3. [Changements Backend / ORM](#3-changements-backend--orm)
4. [Changements Frontend](#4-changements-frontend)
5. [Notes de migration (upgrade)](#5-notes-de-migration-upgrade)
6. [Nouvelles fonctionnalites Odoo 18](#6-nouvelles-fonctionnalites-odoo-18)
7. [Deprecation des endpoints XML-RPC / JSON-RPC](#7-deprecation-des-endpoints-xml-rpc--json-rpc)

---

## 1. Breaking changes Odoo 17 vers 18

### 1.1 ORM - Suppressions

| Element supprime | Remplacement | Details |
|---|---|---|
| `Model._sequence` | PostgreSQL gere la sequence par defaut | L'attribut `_sequence` du Model est supprime. PostgreSQL utilise la sequence par defaut de la cle primaire. |
| `Field.column_format` | Supprime sans remplacement | Attribut de champ supprime |
| `Field.deprecated` | Supprime sans remplacement | Attribut de champ supprime |
| `_name_search()` | `_search_display_name()` | Methode entierement supprimee |
| `_check_recursion()` | `_has_cycle()` | Methode de detection de recursion renommee |
| `user_has_groups()` | `self.env.user.has_group()` | Methode de verification des permissions supprimee |
| `check_access_rights()` + `check_access_rule()` | `check_access()` | Consolide en une seule methode |
| `_filter_access_rules()` + `_filter_access_rules_python()` | `_filtered_access()` | Consolide en une seule methode |
| Import `registry` depuis `odoo` | `from odoo.modules.registry import Registry` puis `Registry(db_name)` | Changement d'import |

### 1.2 ORM - Deprecations

| Element deprecie | Remplacement | Notes |
|---|---|---|
| `name_get()` | Lire le champ `display_name` directement | Ne plus surcharger `name_get()` |
| `fields_get_keys()` | Acces direct aux champs du modele | Deprecie |
| `get_xml_id()` | Utiliser `ir.model.data` directement | Deprecie |
| `_flush_search()` | `execute_query()` avec metadonnees SQL | Le flushing est gere par `execute_query()` via les metadonnees du wrapper SQL |
| `group_operator` (attribut de champ) | `aggregator` | Renommage d'attribut |
| `_()` (traduction) | `self.env._()` | Optionnel, meilleure performance |

### 1.3 ORM - Changements de comportement

| Changement | Impact |
|---|---|
| `_write()` ne leve plus d'erreur pour les enregistrements inexistants | Verifier la logique de gestion d'erreurs dans le code custom |
| `_read_group()` a une nouvelle signature | Refactoring de l'implementation des methodes de recherche et lecture |
| `search()` n'est plus toujours appele | Si vous surchargez `search()` pour modifier les resultats, surcharger `search_fetch()` a la place |
| `copy()` et `copy_data()` operent sur des multi-recordsets | `copy_data` retourne une **liste** de valeurs (et non plus un seul dictionnaire). `self` peut etre un multi-recordset |
| Recherche sur champs related non stockes | Ne genere plus un warning mais leve une **exception** |
| Index PostgreSQL configurable | La propriete `index` de `odoo.fields.Field` permet de definir le type d'index PostgreSQL |

### 1.4 Modules supprimes

| Module | Statut |
|---|---|
| eBay Connector | Supprime |
| Alipay (payment) | Supprime |
| PayU Latam (payment) | Supprime |
| PayUmoney (payment) | Supprime |
| Ogone (payment) | Remplace par le provider Worldline |
| SIPS (payment) | Remplace par le provider Worldline |

---

## 2. Changements OWL (framework frontend)

Odoo 18 utilise **OWL 2.x**. Voici les changements majeurs par rapport a OWL 1.x (utilise dans Odoo 15-17).

### 2.1 Breaking changes OWL 2.x

#### Cycle de vie des composants

| Avant (OWL 1.x) | Apres (OWL 2.x) | Notes |
|---|---|---|
| `mounted()`, `willUnmount()`, etc. | Hooks dans `setup()` : `onMounted()`, `onWillUnmount()` | Les methodes de cycle de vie sur la classe sont **supprimees** |
| `shouldUpdate()` | Supprime | Le systeme de reactivite gere les mises a jour granulaires automatiquement |
| `component.el` | Supprime | Les composants supportent les fragments (noeuds racines multiples) |
| Instanciation manuelle des composants | Interdit | Le framework gere toute l'instanciation |
| Demontage/remontage de composants | Non supporte | |

#### Templates et directives

| Avant | Apres |
|---|---|
| `t-set` pour definir des slots | `t-set-slot` obligatoire |
| `t-component` accepte des strings | Doit recevoir une **classe** de composant |
| `t-ref` sur les composants | Ne fonctionne plus sur les composants |
| `t-on` accepte des expressions | Accepte uniquement des **fonctions** |
| `t-foreach` sans `t-key` | `t-key` **obligatoire** (plus d'indexation implicite) |
| `t-raw` | Remplace par `t-out` |
| Nom de template infere du nom de classe | `Component.template = "nom"` **explicite** obligatoire |

#### APIs supprimees

| Element supprime | Remplacement |
|---|---|
| `Context` API | Systeme de reactivite ameliore |
| `Store` class | Utiliser `reactive()` |
| `Router` class | Supprime |
| Systeme de transitions | Supprime |
| Composants/templates globaux | Non supporte |
| `AsyncRoot` | Supprime |
| `renderToString()` sur QWeb | Supprime |
| `debounce()` utilitaire | Supprime |
| Objet `browser` | Supprime |

#### Environnement et portails

- `env` est desormais **gele** (frozen) et vide du point de vue d'OWL (concept user-space)
- Les portails (`Portal`) ne transferent plus les evenements DOM
- Les portails sont rendus comme des noeuds texte vides au lieu de `<portal/>`
- `mount()` simplifie : `mount(Root, target)` au lieu de `mount(Root, { target })`
- `position=self` supprime des options de montage

### 2.2 Nouvelles fonctionnalites OWL 2.x

| Fonctionnalite | Description |
|---|---|
| `reactive()` | Cree un etat reactif sans liaison a un composant |
| `markRaw()` | Exclut un objet du systeme de reactivite |
| `toRaw()` | Extrait l'objet non-reactif sous-jacent |
| `useEffect` hook | Effets de bord reactifs |
| `useChildSubEnv` hook | Environnement specifique aux composants enfants |
| `onWillDestroy`, `onWillRender`, `onRendered` | Nouveaux hooks de cycle de vie |
| Fragments | Composants avec contenu vide ou noeuds racines multiples |
| Slots ameliores | Parametres et portees (scopes) |
| `.bind` suffix | Liaison de fonctions props aux composants |
| `t-portal` directive | Remplace l'ancien systeme de portails |
| Classe `App` | Encapsule le composant racine avec sa configuration |
| Evenements synthetiques | Support ajoute |
| Validation props avec `*` | Autorise des props supplementaires |
| Reactivite par cle/composant | Tracking des changements plus granulaire |

---

## 3. Changements Backend / ORM

### 3.1 Nouvelles methodes ORM

| Methode | Description |
|---|---|
| `search_fetch()` | Combine recherche et lecture en une seule operation. **A surcharger au lieu de `search()`** |
| `fetch()` | Similaire a `search_fetch` mais pour des cas specifiques de lecture |
| `check_access()` | Remplace `check_access_rights()` + `check_access_rule()` |
| `_filtered_access()` | Remplace `_filter_access_rules()` + `_filter_access_rules_python()` |
| `_search_display_name()` | Remplace `_name_search()` |
| `_has_cycle()` | Remplace `_check_recursion()` |

### 3.2 Wrapper SQL

Odoo 18 introduit un **objet wrapper SQL** qui :
- Facilite la composition SQL de maniere plus sure
- Protege contre les injections SQL
- Est utilise en interne par les methodes ORM
- Les metadonnees SQL sont utilisees par `execute_query()` pour le flushing automatique

### 3.3 Invalidation de cache

Trois niveaux d'invalidation disponibles :
- `env.invalidate_all()` : tout le cache ORM
- `Model.invalidate_model(fields)` : cache d'un modele (optionnellement certains champs)
- `records.invalidate_recordset(fields)` : cache d'un recordset specifique

**Recommandation** : etre le plus specifique possible pour maintenir les performances.

### 3.4 Scripts de migration (upgrade scripts)

Structure des scripts : `$module/migrations/$version/pre,post,end-*.py`

Trois phases d'execution :
1. **pre-phase** : avant le chargement du module
2. **post-phase** : apres le chargement du module et de ses dependances
3. **end-phase** : apres le chargement de tous les modules

```python
# Exemple de script de migration
import logging
from odoo.upgrade import util

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = util.env(cr)
    # Operations de migration ici
```

---

## 4. Changements Frontend

### 4.1 Vues XML

#### Tree vers List

Le type de vue **"tree" est renomme "list"** dans tout le code (XML, Python, JavaScript).

| Avant (17) | Apres (18) |
|---|---|
| `<tree>` | `<list>` |
| `tree_view_ref` (dans context) | `list_view_ref` |
| XML-IDs contenant "tree" | **Conserver** les XML-IDs pour eviter les cascades sur les modules dependants |

Script d'automatisation disponible : `upgrade_code --script 17.5-01-tree-to-list.py`

#### Chatter simplifie

```xml
<!-- Avant (17) -->
<div class="oe_chatter">
    <field name="message_follower_ids"/>
    <field name="activity_ids"/>
    <field name="message_ids"/>
</div>

<!-- Apres (18) -->
<chatter />
```

#### Kanban redesign

| Avant | Apres |
|---|---|
| `kanban-box` | `card` |
| `<div>` englobant | Elements `<field>` standard |
| `kanban-tooltip` | Supprime |
| `<ul class="oe_kanban_colorpicker">` | `<field widget="kanban_color_picker"/>` |
| Images many2one manuelles | `<field widget="image" options="{'preview_image': 'document'}"/>` |

#### Champs invisibles auto-ajoutes

Les champs manquants references dans des expressions (`invisible`, `column_invisible`, `readonly`, `required`, `context`, `domain`) sont **automatiquement ajoutes comme champs invisibles**. Il faut supprimer les declarations `invisible="True"` ou `invisible="1"` redondantes.

### 4.2 JavaScript

| Changement | Details |
|---|---|
| `/** @odoo-module **/` | Commentaire **supprimable** de tous les fichiers JS |
| `extra_trigger` (test tours) | Deprecie. Creer des etapes independantes a la place |
| Widgets vs Composants | "widget" = anciens widgets Odoo. "component" = nouveaux composants OWL. Tout nouveau dev doit utiliser OWL |
| Framework de test HOOT | Nouveau framework de tests unitaires JS |

### 4.3 Gestion des assets

Les assets sont groupes par **bundles** definis dans le `__manifest__.py` :

```python
'assets': {
    'web.assets_backend': [
        'mon_module/static/src/js/**/*.js',
        'mon_module/static/src/css/**/*.css',
    ],
}
```

Directives disponibles :
- **Include** : `('include', 'web._assets_helpers')` pour reutiliser des sous-bundles
- **Remove** : `('remove', 'web/static/src/legacy/file.js')` pour retirer un fichier
- **Replace** : `('replace', 'web/static/src/old.js', 'mon_module/static/src/new.js')`

### 4.4 Registries et Services

L'architecture frontend Odoo 18 repose sur :
- **Registries** : systeme de registration modulaire pour composants, vues, widgets, actions
- **Services** : injection de dependances (pattern similaire a Angular)
- **Hooks OWL** : hooks personnalises Odoo (`useService`, etc.)
- **Environnement** : contexte utilisateur et contexte d'action separes

---

## 5. Notes de migration (upgrade)

### 5.1 Processus de migration officiel (on-premise)

```bash
# Lancer la migration via l'outil officiel
python <(curl -s https://upgrade.odoo.com/upgrade) test -d <nom_bdd> -t 18.0
```

### 5.2 Etapes pour les modules custom

1. **Arreter le developpement** sur la version 17
2. **Mettre a jour la version** dans `__manifest__.py` : `'version': '18.0.1.0.0'`
3. **Supprimer le dossier `migrations`** du module
4. **Appliquer les changements de code** :
   - Tree vers List (XML, Python, JS)
   - Methodes ORM supprimees/renommees
   - OWL 2.x si code JS custom
   - Supprimer `/** @odoo-module **/`
5. **Tester** avec pre-commit et tests standards
6. **Scripts de migration** si champs company-dependent

### 5.3 Checklist de migration (code Python)

- [ ] `_name_search()` -> `_search_display_name()`
- [ ] `name_get()` -> lire `display_name`
- [ ] `user_has_groups()` -> `self.env.user.has_group()`
- [ ] `check_access_rights()` + `check_access_rule()` -> `check_access()`
- [ ] `_filter_access_rules()` -> `_filtered_access()`
- [ ] `_check_recursion()` -> `_has_cycle()`
- [ ] `group_operator` -> `aggregator` dans les definitions de champs
- [ ] `copy_data()` retourne une **liste** (adapter le code appelant)
- [ ] `search()` surcharge -> `search_fetch()` surcharge
- [ ] Import `registry` -> `from odoo.modules.registry import Registry`
- [ ] Recherche sur champs related non stockes : gerer l'exception au lieu du warning

### 5.4 Checklist de migration (vues XML)

- [ ] `<tree>` -> `<list>` (script automatise disponible)
- [ ] `tree_view_ref` -> `list_view_ref` dans les contextes
- [ ] `<div class="oe_chatter">...</div>` -> `<chatter />`
- [ ] `kanban-box` -> `card`
- [ ] Supprimer les declarations `invisible="True"` redondantes
- [ ] Supprimer `kanban-tooltip`
- [ ] Convertir les color pickers kanban

### 5.5 Checklist de migration (JavaScript)

- [ ] Supprimer `/** @odoo-module **/`
- [ ] Remplacer `extra_trigger` par des etapes de test independantes
- [ ] Migrer les lifecycles OWL 1.x vers hooks OWL 2.x dans `setup()`
- [ ] `t-raw` -> `t-out`
- [ ] `t-set` (slots) -> `t-set-slot`
- [ ] `t-foreach` : ajouter `t-key` si manquant

---

## 6. Nouvelles fonctionnalites Odoo 18

### 6.1 Fonctionnalites techniques majeures

| Fonctionnalite | Description |
|---|---|
| **URLs lisibles** | `/odoo/project/5/tasks` au lieu d'URLs cryptiques. Attribut `path` sur `ir.actions.act_window` |
| **Passkeys (WebAuthn)** | Nouvelle methode d'authentification sans mot de passe |
| **PWA dediees** | Apps progressives pour Barcode, PoS, Attendances, Kiosk, Registration Desk, Shop Floor |
| **HOOT** | Nouveau framework de tests unitaires JavaScript |
| **Wrapper SQL** | Composition SQL plus sure contre les injections |
| **search_fetch() / fetch()** | Nouvelles methodes ORM combinant recherche + lecture |
| **Peppol** | Integration native pour facturation electronique europeenne |
| **Multi-ledger** | Ameliorations pour les environnements multi-societes |
| **Comptes partages** | Un meme compte peut appartenir a plusieurs societes |

### 6.2 Nouvelles fonctionnalites comptabilite (pertinent pour HMA)

| Fonctionnalite | Description |
|---|---|
| **Peppol** | Envoi de factures sur le reseau Peppol |
| **Comptes partages multi-societes** | Fusion de comptes entre societes |
| **Reconciliation de brouillons** | Les ecritures brouillon peuvent etre rapprochees |
| **Remise a zero de factures** | Reset to draft avec detachement des documents generes |
| **ISO 20022 priorite** | Support de l'instruction de priorite dans les paiements ISO 20022 |
| **OCR bancaire** | Correction manuelle OCR pour les releves bancaires |
| **Suivi lots inter-societes** | Tracabilite complete des lots et numeros de serie entre societes |

### 6.3 Ameliorations Odoo 18.1 et 18.2

**18.1 :**
- Ouverture de fichiers CSV dans Spreadsheet
- Validation de donnees par formule avec auto-completion
- Import/export des validations de donnees depuis/vers XLSX
- Carte d'irregularites pour analyse de formules spreadsheet

**18.2 :**
- Vue Gantt amelioree (zoom intelligent, drag-and-drop, heures creuses pliables)
- Vue List : double-clic sur bordures de colonnes pour auto-redimensionnement
- Kanban : actions de masse via ALT+click (desktop) ou appui long (mobile)
- Pull-to-refresh pour les PWA
- Gestion des abonnes (followers) depuis plusieurs enregistrements simultanement

### 6.4 Nouveaux packages metier

Bakery, Cleaning Service, Dropshipping, Electrician, Food Truck, Marketing Agency, Outdoor Activities, Shoemaker, Tattoo Shop, Wedding Planner.

---

## 7. Deprecation des endpoints XML-RPC / JSON-RPC

### 7.1 Calendrier de deprecation

| Version | Evenement | Date estimee |
|---|---|---|
| **Odoo 18** | XML-RPC et JSON-RPC **fonctionnels** (pas de deprecation) | Octobre 2024 |
| **Odoo 19** | **Deprecation** : warning dans les logs lors de l'utilisation de `/xmlrpc`, `/xmlrpc/2`, `/jsonrpc` | Automne 2025 |
| **Odoo Online 21.1** | **Suppression** pour Odoo Online | Hiver 2027 |
| **Odoo 22** | **Suppression** pour Odoo on-premise | Automne 2028 |

### 7.2 Endpoints concernes

| Endpoint | Statut Odoo 18 | Statut Odoo 19+ |
|---|---|---|
| `/xmlrpc` | Actif | Deprecie (warning) |
| `/xmlrpc/2` | Actif | Deprecie (warning) |
| `/jsonrpc` | Actif | Deprecie (warning) |
| Autres `@route(type='json')` | Actif | **Non concernes** par la deprecation |

### 7.3 API de remplacement : External JSON-2 API

Introduite dans Odoo 19, la nouvelle API JSON-2 apporte :

| Aspect | Ancien (XML-RPC/JSON-RPC) | Nouveau (JSON-2) |
|---|---|---|
| **Authentification** | Login/password | **API Key** via header `Authorization: bearer <key>` |
| **Structure requete** | Methode en parametre | Modele et methode **dans l'URL** |
| **Arguments** | Positionnels et nommes | **Uniquement nommes** (objet JSON avec `ids`, `context`, etc.) |
| **Format** | XML-RPC ou JSON-RPC wrapping | JSON pur |

### 7.4 Impact pour HMA

**Pour Odoo 18** : aucun changement requis. Les endpoints XML-RPC et JSON-RPC fonctionnent normalement.

**Planification** : preparer la migration vers l'API JSON-2 avant Odoo 22 (2028). Si n8n est utilise pour l'integration Odoo, surveiller l'issue GitHub [n8n-io/n8n#21545](https://github.com/n8n-io/n8n/issues/21545) pour le support de la nouvelle API.

---

## Sources

- [Odoo 18 Release Notes](https://www.odoo.com/odoo-18-release-notes)
- [Odoo 18.0 ORM Changelog](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm/changelog.html)
- [Odoo 18.2 Release Notes](https://www.odoo.com/odoo-18-2-release-notes)
- [Odoo 18.0 External API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Odoo 18.0 Frontend Framework Overview](https://www.odoo.com/documentation/18.0/developer/reference/frontend/framework_overview.html)
- [Odoo 18.0 Assets](https://www.odoo.com/documentation/18.0/developer/reference/frontend/assets.html)
- [Odoo 18.0 View Architectures](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)
- [Odoo 18.0 Upgrade Scripts](https://www.odoo.com/documentation/18.0/developer/reference/upgrades/upgrade_scripts.html)
- [Odoo 18.0 Upgrade Custom DB](https://www.odoo.com/documentation/18.0/developer/howtos/upgrade_custom_db.html)
- [OCA Migration to 18.0 Wiki](https://github.com/OCA/maintainer-tools/wiki/Migration-to-version-18.0)
- [OWL Changelog (GitHub)](https://github.com/odoo/owl/blob/master/CHANGELOG.md)
- [Odoo 19.0 External JSON-2 API](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
- [n8n Issue #21545 - Odoo RPC deprecation](https://github.com/n8n-io/n8n/issues/21545)
