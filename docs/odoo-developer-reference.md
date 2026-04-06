# Odoo — Référence Développeur Complète (v17/18)

**Dernière mise à jour** : 2026-04-06
**Sources** : documentation officielle Odoo SA (`odoo.com/documentation/18.0`, `17.0`), code source `github.com/odoo/odoo`, OCA `github.com/OCA/l10n-france` branche 18.0, framework OWL `github.com/odoo/owl`

---

## Table des matières

1. [Localisation française (l10n_fr)](#1-localisation-française-officielle-l10n_fr)
2. [Modules OCA France](#2-modules-oca--dépôt-ocal10n-france)
3. [Architecture & Framework](#3-architecture--framework)
4. [Backend — ORM & Modèles](#4-backend--orm--modèles)
5. [Frontend — Vues XML](#5-frontend--vues-xml)
6. [Frontend — OWL 2 (JavaScript)](#6-frontend--owl-2-javascript)
7. [Templates QWeb](#7-templates-qweb)
8. [Contrôleurs Web & API](#8-contrôleurs-web--api)
9. [API externe (XML-RPC / JSON-RPC)](#9-api-externe-xml-rpc--json-rpc)
10. [Sécurité](#10-sécurité)
11. [Fichiers de données](#11-fichiers-de-données)
12. [Tests](#12-tests)
13. [Migrations](#13-migrations)
14. [Développement mobile](#14-développement-mobile)
15. [Changelog Odoo 17 → 18](#15-changelog-odoo-17--18)
16. [Pertinence pour le projet HMA](#16-pertinence-pour-le-projet-hma)

---

## 1. Localisation française officielle (l10n_fr)

### 1.1 Modules natifs

| Module | Nom technique | Description |
|--------|---------------|-------------|
| **France - Accounting** | `l10n_fr` | Plan Comptable Général (PCG), taxes TVA, positions fiscales |
| **France - Accounting Reports** | `l10n_fr_account` | Bilan comptable (FR), Compte de Résultats (FR), Rapport de taxes (FR) |
| **France - FEC Export** | `l10n_fr_fec` | Export du Fichier des Écritures Comptables (obligation légale) |
| **France - FEC Import** | `l10n_fr_fec_import` | Import de fichiers FEC (migration depuis d'autres logiciels) |
| **France - POS VAT Anti-Fraud** | `l10n_fr_pos_cert` | Certification NF525 pour le Point de Vente |

### 1.2 Plan Comptable Général (PCG)

- Comptes définis dans des fichiers CSV chargés à l'installation (`account.account.template`)
- Numérotation PCG standard (classes 1 à 7, sous-comptes sur 6 chiffres)
- Import FEC : comparaison sur les **6 premiers chiffres** du code compte
- Plan comptable lié à une **société** (`res.company`) — chaque société a son propre PCG

### 1.3 FEC — Fichier des Écritures Comptables (Art. A.47 A-1 du LPF)

**Export FEC** (`l10n_fr_fec`) :
- Chemin : *Comptabilité > Reporting > FEC*
- Paramètres : date de début, date de fin, journaux exclus, option "fichier de test"
- Format : CSV avec en-tête, une ligne par écriture, **ordre chronologique**

**Import FEC** (`l10n_fr_fec_import`) :
- Format : CSV uniquement
- Détection automatique encodage, terminateurs, séparateurs
- Ordre d'import : comptes → journaux → partenaires → écritures
- Correspondance des comptes sur les 6 premiers chiffres

**18 colonnes obligatoires du FEC** :

| # | Champ | Description |
|---|-------|-------------|
| 1 | JournalCode | Code journal |
| 2 | JournalLib | Libellé journal |
| 3 | EcritureNum | Numéro d'écriture |
| 4 | EcritureDate | Date d'écriture |
| 5 | CompteNum | Numéro de compte |
| 6 | CompteLib | Libellé de compte |
| 7 | CompAuxNum | Numéro de compte auxiliaire |
| 8 | CompAuxLib | Libellé de compte auxiliaire |
| 9 | PieceRef | Référence de la pièce |
| 10 | PieceDate | Date de la pièce |
| 11 | EcritureLib | Libellé de l'écriture |
| 12 | Debit | Montant débit |
| 13 | Credit | Montant crédit |
| 14 | EcrtureLet | Lettre de lettrage |
| 15 | DateLet | Date de lettrage |
| 16 | ValidDate | Date de validation |
| 17 | Montantdevise | Montant en devise |
| 18 | Idevise | Identifiant devise |

Format : CSV, encodage UTF-8 ou ISO-8859, séparateur tabulation ou pipe, ordre chronologique obligatoire.

### 1.4 Taxes / TVA

Taux préconfigurés :
- **20%** (taux normal)
- **10%** (taux intermédiaire)
- **5,5%** (taux réduit)
- **2,1%** (taux super-réduit, presse, médicaments)
- **0%** (exonéré, non soumis)

Chaque taxe définie avec lignes de répartition (base, taxe, comptes collecte/déduction) et tags pour le rapport de taxes.

### 1.5 Positions fiscales

- **France métropolitaine** (domestique) — appliquée automatiquement
- **Intracommunautaire** (avec TVA intracommunautaire) — autoliquidation
- **Intracommunautaire privé** (sans numéro de TVA)
- **Export hors UE** (exonération)

Chaque position contient des règles de **mapping de taxes** et de **mapping de comptes**. Application automatique basée sur le pays et la présence d'un numéro de TVA.

### 1.6 E-facturation — Chorus Pro

Support natif de l'envoi via **Chorus Pro** (portail de facturation de l'État français) :
- Configuration infos client (service exécutant, numéro d'engagement)
- Transmission via l'API Chorus Pro
- Obligatoire pour les fournisseurs de l'État et collectivités

---

## 2. Modules OCA — Dépôt `OCA/l10n-france`

**28 modules** sur la branche 18.0 (`github.com/OCA/l10n-france`).

### 2.1 Comptabilité et reporting financier

| Module | Version | Description |
|--------|---------|-------------|
| `account_balance_ebp_csv_export` | 18.0.1.1.0 | Export balance format EBP (CSV/XLSX) |
| `l10n_fr_account_tax_unece` | 18.0.1.0.0 | Codes UNECE sur les taxes (norme UN/CEFACT pour Factur-X) |
| `l10n_fr_mis_reports` | 18.0.1.0.0 | Templates Bilan et CR pour MIS Builder (OCA) |

### 2.2 DAS2 — Déclaration d'honoraires

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_das2` | 18.0.2.0.0 | Déclaration annuelle DAS2 (honoraires, commissions, droits d'auteur) |

Dépendance Python : `pyfrdas2` (clés PGP de la DGFiP). Workflow : création rapport → génération lignes depuis écritures → révision → fichier chiffré pour impots.gouv.fr.

### 2.3 Intrastat (EMEBI / DES)

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_intrastat_product` | 18.0.2.0.0 | Déclaration EMEBI (biens intracommunautaires) |
| `l10n_fr_intrastat_service` | 18.0.1.2.0 | Déclaration DES (services intracommunautaires) |

### 2.4 Facturation électronique et Factur-X

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_account_invoice_facturx` | 18.0.1.0.0 | Génération factures Factur-X (EN16931) |
| `l10n_fr_account_invoice_import_facturx` | 18.0.1.0.0 | Import factures Factur-X |
| `l10n_fr_account_invoice_import_simple_pdf` | 18.0.1.0.0 | Import factures PDF par SIREN |
| `l10n_fr_business_document_import` | 18.0.1.0.0 | Adaptation import documents commerciaux France |

### 2.5 Chorus Pro (e-facturation publique)

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_chorus_account` | 18.0.1.0.0 | Factures conformes Chorus Pro + transmission API |
| `l10n_fr_chorus_facturx` | 18.0.1.0.0 | Factures Factur-X conformes Chorus Pro |
| `l10n_fr_chorus_sale` | 18.0.1.0.0 | Contrôles validation commandes client Chorus Pro |

### 2.6 Paiements bancaires

| Module | Version | Description |
|--------|---------|-------------|
| `account_payment_fr_lcr` | 18.0.1.2.0 | Fichiers LCR format CFONB |
| `account_statement_import_fr_cfonb` | 18.0.1.0.0 | Import relevés bancaires CFONB |
| `l10n_fr_account_payment_intl_credit_transfer` | 18.0.2.0.0 | Codes réglementaires virements ISO 20022 |

### 2.7 Identification entreprises (SIRET/SIREN)

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_siret` | 18.0.1.2.0 | Support SIRET/SIREN/NIC + validation checksum |
| `l10n_fr_siret_account` | 18.0.1.0.0 | Pont SIRET ↔ module comptabilité |
| `l10n_fr_siret_lookup` | 18.0.1.0.0 | Recherche partenaires via API SIRENE INSEE |

### 2.8 Données géographiques

| Module | Version | Description |
|--------|---------|-------------|
| `country_fr` | 18.0.1.0.0 | Configuration pays France |
| `l10n_fr_cog` | 18.0.1.0.0 | Code Officiel Géographique (COG) INSEE |
| `l10n_fr_department` | 18.0.2.1.0 | Départements métropolitains |
| `l10n_fr_department_oversea` | 18.0.1.0.0 | **DOM** (Guyane 973, etc.) |
| `l10n_fr_state` | 18.0.1.0.0 | Régions françaises |

### 2.9 Autres

| Module | Version | Description |
|--------|---------|-------------|
| `l10n_fr_hr_check_ssnid` | 18.0.1.0.0 | Validation numéro Sécurité sociale |
| `l10n_fr_pos_caisse_ap_ip` | 18.0.1.4.0 | Protocole paiement Caisse-AP pour POS |

### 2.10 Note sur `l10n_fr_fec_oca`

Ce module **n'existe plus en branche 18.0**. L'export FEC est intégré nativement dans Odoo (`l10n_fr_fec`) depuis Odoo 17+.

---

## 3. Architecture & Framework

### 3.1 Architecture MVC

```
Utilisateurs → HTTPS → Contrôleur HTTP (Python)
                            ↓
                      Modèle ORM (Python) ←→ PostgreSQL
                            ↓
                      Vue (XML/QWeb/OWL)
```

L'application est un ensemble de **modules** (addons). Chaque module est un dossier Python avec `__manifest__.py`.

### 3.2 Structure d'un module

```
mon_module/
├── __init__.py              # Import des sous-packages Python
├── __manifest__.py          # Manifeste du module (métadonnées)
├── controllers/
│   ├── __init__.py
│   └── controllers.py       # Contrôleurs HTTP
├── demo/
│   └── demo.xml             # Données de démonstration
├── models/
│   ├── __init__.py
│   └── models.py            # Définitions des modèles ORM
├── security/
│   ├── ir.model.access.csv  # Droits d'accès par modèle
│   └── security.xml         # Règles d'enregistrement (ir.rule)
├── static/
│   ├── description/
│   │   └── icon.png         # Icône du module
│   └── src/
│       ├── js/              # JavaScript / OWL
│       ├── xml/             # Templates QWeb frontend
│       └── scss/            # Styles
├── views/
│   ├── views.xml            # Vues (form, tree, kanban...)
│   ├── templates.xml        # Templates QWeb backend
│   └── menus.xml            # Menus et actions
├── data/
│   └── data.xml             # Données initiales
├── wizard/
│   ├── __init__.py
│   └── wizard.py            # TransientModel (assistants)
├── report/
│   └── report_templates.xml # Templates de rapports
└── migrations/
    └── 18.0.1.0.0/
        ├── pre-migrate.py   # Script pré-migration
        └── post-migrate.py  # Script post-migration
```

### 3.3 Le manifeste `__manifest__.py`

```python
{
    'name': 'Mon Module',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Résumé court du module',
    'description': """Description longue en RST ou texte""",
    'author': 'HMA Gestion',
    'website': 'https://hma.business',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'sale'],
    'data': [
        'security/ir.model.access.csv',      # Toujours en premier
        'security/security.xml',
        'views/views.xml',
        'views/menus.xml',
        'data/data.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mon_module/static/src/js/**/*',
            'mon_module/static/src/xml/**/*',
            'mon_module/static/src/scss/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
```

| Clé | Type | Description |
|-----|------|-------------|
| `name` | str | Nom affiché du module |
| `version` | str | Format : `ODOO_VERSION.MODULE_VERSION` |
| `depends` | list | Modules requis (minimum `['base']`) |
| `data` | list | Fichiers XML/CSV chargés à l'installation |
| `demo` | list | Données de démo (mode démonstration uniquement) |
| `assets` | dict | Bundles d'assets JS/CSS/XML par bundle cible |
| `installable` | bool | Si le module peut être installé (défaut: True) |
| `application` | bool | Si c'est une application principale |
| `license` | str | Licence (LGPL-3, OEEL-1, etc.) |
| `auto_install` | bool | Installation automatique si toutes les dépendances sont présentes |

### 3.4 Trois classes de modèles

| Classe | Table BDD | Nettoyage auto | Usage |
|--------|-----------|----------------|-------|
| `models.Model` | Oui (automatique) | Non | Modèles persistants (clients, factures) |
| `models.TransientModel` | Oui | Oui (vacuum périodique) | Données temporaires (wizards) |
| `models.AbstractModel` | Non | N/A | Classes abstraites (mixins) |

```python
from odoo import models, fields

class MonModele(models.Model):
    _name = 'mon.modele'
    _description = 'Description du modèle'
    name = fields.Char(string='Nom', required=True)

class MonWizard(models.TransientModel):
    _name = 'mon.wizard'
    _transient_max_hours = 0.5
    _transient_max_count = 100

class MonMixin(models.AbstractModel):
    _name = 'mon.mixin'
    active = fields.Boolean(default=True)
```

### 3.5 Trois types d'héritage

#### a) Héritage classique (extension in-place)

Même table BDD, même `_name`. Ajoute des champs/méthodes au modèle existant.

```python
class ResPartner(models.Model):
    _inherit = 'res.partner'

    code_comptable = fields.Char(string='Code comptable')

    def name_get(self):
        result = super().name_get()
        return result
```

#### b) Héritage prototype (copie avec nouveau nom)

Nouveau modèle, nouvelle table. Copie tous les champs/méthodes du parent.

```python
class MonPartenaire(models.Model):
    _name = 'mon.partenaire'
    _inherit = 'res.partner'
    _description = 'Mon Partenaire'

    statut_special = fields.Selection([
        ('vip', 'VIP'),
        ('standard', 'Standard'),
    ])
```

#### c) Héritage par délégation

Délègue l'accès aux champs du parent via Many2one. Accès transparent.

```python
class Laptop(models.Model):
    _name = 'delegation.laptop'
    _inherits = {
        'delegation.screen': 'screen_id',
        'delegation.keyboard': 'keyboard_id',
    }

    name = fields.Char(string='Name')
    screen_id = fields.Many2one('delegation.screen', required=True, ondelete="cascade")
    keyboard_id = fields.Many2one('delegation.keyboard', required=True, ondelete="cascade")
    # Accès direct à screen_id.size et keyboard_id.layout
```

**Résumé comparatif** :

| Aspect | Classique `_inherit` | Prototype `_inherit` + `_name` | Délégation `_inherits` |
|--------|---------------------|-------------------------------|----------------------|
| Nouveau modèle ? | Non | Oui | Oui |
| Nouvelle table ? | Non | Oui | Oui (+ Many2one) |
| Champs copiés ? | Non (étendus) | Oui (dupliqués) | Non (délégués) |
| Méthodes héritées ? | Oui | Oui | Non |

---

## 4. Backend — ORM & Modèles

### 4.1 Types de champs

#### Champs basiques

```python
from odoo import fields

name = fields.Char(string='Nom', required=True, size=128, trim=True)
description = fields.Text(string='Description')
contenu_html = fields.Html(string='Contenu', sanitize=True)
age = fields.Integer(string='Age', default=0)
montant = fields.Float(string='Montant', digits=(16, 2))
prix = fields.Monetary(string='Prix', currency_field='currency_id')
actif = fields.Boolean(string='Actif', default=True)
date_debut = fields.Date(string='Date début', default=fields.Date.today)
date_heure = fields.Datetime(string='Date/heure', default=fields.Datetime.now)
fichier = fields.Binary(string='Fichier')
image = fields.Image(string='Photo', max_width=1024, max_height=1024)
etat = fields.Selection([
    ('brouillon', 'Brouillon'),
    ('confirme', 'Confirmé'),
    ('annule', 'Annulé'),
], string='État', default='brouillon')
```

#### Champs relationnels

```python
# Many2one : lien vers UN enregistrement
partner_id = fields.Many2one(
    'res.partner',
    string='Client',
    required=True,
    ondelete='cascade',   # ou 'set null', 'restrict'
    domain=[('is_company', '=', True)],
    index=True,
)

# One2many : lien inverse (un-à-plusieurs)
line_ids = fields.One2many(
    'mon.modele.line',     # Modèle cible
    'parent_id',           # Champ Many2one inverse
    string='Lignes',
)

# Many2many : relation plusieurs-à-plusieurs
tag_ids = fields.Many2many(
    'mon.tag',
    'mon_modele_tag_rel',   # Table de relation (optionnel)
    'modele_id',            # Colonne source (optionnel)
    'tag_id',               # Colonne cible (optionnel)
    string='Tags',
)
```

#### Champs calculés et liés

```python
# Champ calculé (compute)
total = fields.Float(
    string='Total',
    compute='_compute_total',
    store=True,              # Stocké en BDD (sinon calculé à la volée)
    readonly=True,
)

@api.depends('line_ids.montant', 'line_ids.quantite')
def _compute_total(self):
    for record in self:
        record.total = sum(
            line.montant * line.quantite
            for line in record.line_ids
        )

# Champ inverse (éditable malgré compute)
nom_affiche = fields.Char(
    compute='_compute_nom',
    inverse='_inverse_nom',
    search='_search_nom',
)

# Champ lié (Related) — raccourci vers un champ d'un modèle lié
pays_id = fields.Many2one(related='partner_id.country_id', store=True)
```

### 4.2 Méthodes CRUD

```python
# CREATE
record = self.env['mon.modele'].create({
    'name': 'Test',
    'montant': 100.0,
})
# Création multiple
records = self.env['mon.modele'].create([
    {'name': 'A'}, {'name': 'B'}
])

# READ
data = record.read(['name', 'montant'])  # Liste de dicts

# SEARCH
records = self.env['mon.modele'].search([
    ('etat', '=', 'confirme'),
    ('montant', '>=', 1000),
], limit=10, order='montant DESC')

# SEARCH_COUNT
nb = self.env['mon.modele'].search_count([('etat', '=', 'brouillon')])

# SEARCH_READ (optimisé)
data = self.env['mon.modele'].search_read(
    [('etat', '=', 'confirme')],
    fields=['name', 'montant'],
    limit=50,
    order='create_date DESC',
)

# BROWSE (par ID)
record = self.env['mon.modele'].browse(42)
records = self.env['mon.modele'].browse([1, 2, 3])

# WRITE
record.write({'montant': 200.0, 'etat': 'confirme'})

# UNLINK
record.unlink()
```

### 4.3 Décorateurs

```python
from odoo import api, models, fields
from odoo.exceptions import ValidationError

class MonModele(models.Model):
    _name = 'mon.modele'

    # @api.depends — dépendances d'un champ compute
    @api.depends('prix_unitaire', 'quantite', 'taxe')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.prix_unitaire * rec.quantite * (1 + rec.taxe / 100)

    # @api.constrains — validation côté serveur
    @api.constrains('montant')
    def _check_montant_positif(self):
        for rec in self:
            if rec.montant < 0:
                raise ValidationError("Le montant doit être positif !")

    # @api.onchange — réaction dans le formulaire (avant sauvegarde)
    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            self.adresse = self.partner_id.street
            return {
                'warning': {
                    'title': 'Attention',
                    'message': 'Vérifiez l\'adresse',
                }
            }

    # @api.model — méthode de classe
    @api.model
    def recherche_avancee(self, criteres):
        return self.search([...])

    # @api.model_create_multi — surcharge optimisée de create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['reference'] = self.env['ir.sequence'].next_by_code('mon.modele')
        return super().create(vals_list)

    # @api.autovacuum — maintenance périodique automatique
    @api.autovacuum
    def _nettoyer_anciens(self):
        limite = fields.Datetime.subtract(fields.Datetime.now(), days=90)
        self.search([('create_date', '<', limite)]).unlink()
```

### 4.4 Recordsets et Environnement

```python
# L'environnement (self.env)
self.env.cr          # Curseur de base de données (psycopg2)
self.env.uid         # ID de l'utilisateur courant
self.env.user        # Recordset utilisateur courant (res.users)
self.env.company     # Société courante (res.company)
self.env.companies   # Toutes les sociétés accessibles
self.env.context     # Dictionnaire de contexte
self.env.lang        # Langue courante
self.env['res.partner']  # Accès à un modèle via l'environnement

# Opérations sur les recordsets
for record in records:       # Itération
    print(record.name)

record = records[0]           # Indexation
subset = records[:5]          # Slicing
combined = records1 | records2   # Union
common = records1 & records2     # Intersection
diff = records1 - records2       # Différence

len(records)                  # Nombre d'enregistrements
bool(records)                 # True si non vide
record.ids                    # Liste des IDs
record.ensure_one()           # Lève erreur si != 1 enregistrement

# Changer de contexte / utilisateur
records_fr = records.with_context(lang='fr_FR')
records_sudo = records.sudo()
records_user = records.with_user(user)
records_company = records.with_company(company)
```

### 4.5 Syntaxe des domaines (filtres)

Notation **polonaise préfixée** :

```python
# Syntaxe : [('champ', 'opérateur', 'valeur')]

# Opérateurs :
# =, !=, <, <=, >, >=
# in, not in
# like, not like       (pattern SQL, sensible casse)
# ilike, not ilike     (insensible casse)
# =like, =ilike        (pattern exact)
# child_of, parent_of  (hiérarchie)

# Opérateurs logiques :
# '&'  → ET (implicite entre tuples)
# '|'  → OU
# '!'  → NON

# ET implicite
[('etat', '=', 'confirme'), ('montant', '>=', 1000)]

# OU explicite
['|', ('etat', '=', 'brouillon'), ('etat', '=', 'confirme')]

# Combinaison complexe : (etat=confirme ET montant>=1000) OU actif=False
['|',
    '&', ('etat', '=', 'confirme'), ('montant', '>=', 1000),
    ('actif', '=', False),
]

# Champs relationnels (dot notation)
[('partner_id.country_id.code', '=', 'FR')]
```

### 4.6 Contraintes

```python
# Contrainte SQL
class EstateProperty(models.Model):
    _name = "estate.property"

    _sql_constraints = [
        ('check_expected_price', 'CHECK(expected_price > 0)',
         'Le prix attendu doit être strictement positif.'),
        ('unique_name', 'UNIQUE(name)',
         'Le nom de la propriété doit être unique.'),
    ]

# Contrainte Python
from odoo.tools.float_utils import float_compare

@api.constrains('price', 'property_id.expected_price')
def _check_price(self):
    for record in self:
        if float_compare(record.price,
                         record.property_id.expected_price * 0.9,
                         precision_digits=2) < 0:
            raise ValidationError(
                "Le prix de l'offre doit être au moins 90% du prix attendu."
            )
```

### 4.7 Actions planifiées (ir.cron)

```xml
<record id="ir_cron_nettoyage" model="ir.cron">
    <field name="name">Nettoyage quotidien des brouillons</field>
    <field name="model_id" ref="model_mon_modele"/>
    <field name="state">code</field>
    <field name="code">model._nettoyer_brouillons()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="numbercall">-1</field>
    <field name="active" eval="True"/>
</record>
```

---

## 5. Frontend — Vues XML

### 5.1 Vue formulaire (form)

```xml
<record id="view_mon_modele_form" model="ir.ui.view">
    <field name="name">mon.modele.form</field>
    <field name="model">mon.modele</field>
    <field name="arch" type="xml">
        <form string="Mon Modèle">
            <header>
                <button name="action_confirmer" type="object"
                        string="Confirmer" class="oe_highlight"
                        invisible="etat != 'brouillon'"/>
                <field name="etat" widget="statusbar"
                       statusbar_visible="brouillon,confirme,termine"/>
            </header>
            <sheet>
                <div class="oe_title">
                    <h1><field name="name" placeholder="Nom..."/></h1>
                </div>
                <group>
                    <group string="Informations">
                        <field name="partner_id"/>
                        <field name="date_debut"/>
                    </group>
                    <group string="Montants">
                        <field name="montant"/>
                        <field name="total" widget="monetary"/>
                    </group>
                </group>
                <notebook>
                    <page string="Lignes" name="lines">
                        <field name="line_ids">
                            <tree editable="bottom">
                                <field name="produit_id"/>
                                <field name="quantite"/>
                                <field name="prix"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Notes">
                        <field name="notes"/>
                    </page>
                </notebook>
            </sheet>
            <!-- Chatter (Odoo 18) -->
            <chatter/>
        </form>
    </field>
</record>
```

### 5.2 Vue liste (tree/list)

```xml
<record id="view_mon_modele_tree" model="ir.ui.view">
    <field name="name">mon.modele.tree</field>
    <field name="model">mon.modele</field>
    <field name="arch" type="xml">
        <list decoration-danger="montant &lt; 0"
              decoration-success="etat == 'confirme'"
              default_order="date_debut desc">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="montant" sum="Total"/>
            <field name="etat" widget="badge"
                   decoration-info="etat == 'brouillon'"
                   decoration-success="etat == 'confirme'"/>
        </list>
    </field>
</record>
```

> **Note Odoo 18** : `<tree>` est renommé `<list>`. Les deux fonctionnent mais `<list>` est le standard.

### 5.3 Autres types de vues

```xml
<!-- Vue Kanban -->
<kanban default_group_by="etat">
    <field name="name"/>
    <templates>
        <t t-name="card">
            <field name="name"/>
            <field name="montant"/>
        </t>
    </templates>
</kanban>

<!-- Vue Pivot -->
<pivot string="Analyse">
    <field name="partner_id" type="row"/>
    <field name="date_debut" type="col" interval="month"/>
    <field name="montant" type="measure"/>
</pivot>

<!-- Vue Graphique -->
<graph string="Graphique" type="bar">
    <field name="etat" type="row"/>
    <field name="montant" type="measure"/>
</graph>

<!-- Vue Calendrier -->
<calendar string="Calendrier" date_start="date_debut" date_stop="date_fin"
          color="etat" mode="month">
    <field name="name"/>
    <field name="partner_id"/>
</calendar>

<!-- Vue Search -->
<search string="Recherche">
    <field name="name"/>
    <field name="partner_id"/>
    <filter name="confirmes" string="Confirmés"
            domain="[('etat', '=', 'confirme')]"/>
    <group expand="0" string="Grouper par">
        <filter name="group_partner" string="Client"
                context="{'group_by': 'partner_id'}"/>
    </group>
</search>
```

### 5.4 Actions et menus

```xml
<record id="action_mon_modele" model="ir.actions.act_window">
    <field name="name">Mes Modèles</field>
    <field name="res_model">mon.modele</field>
    <field name="view_mode">list,form,kanban,pivot,graph,calendar</field>
    <field name="domain">[('actif', '=', True)]</field>
    <field name="context">{'default_etat': 'brouillon'}</field>
    <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
            Créez votre premier enregistrement
        </p>
    </field>
</record>

<menuitem id="menu_root" name="Mon App" sequence="10"/>
<menuitem id="menu_modeles" name="Modèles"
          parent="menu_root" action="action_mon_modele" sequence="1"/>
```

### 5.5 Héritage de vues (XPath)

```xml
<record id="view_partner_form_inherit" model="ir.ui.view">
    <field name="name">res.partner.form.inherit.mon_module</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <!-- Ajouter après -->
        <xpath expr="//field[@name='email']" position="after">
            <field name="code_comptable"/>
        </xpath>

        <!-- Ajouter avant -->
        <field name="phone" position="before">
            <field name="mon_champ"/>
        </field>

        <!-- Remplacer -->
        <field name="website" position="replace">
            <field name="website" widget="url"/>
        </field>

        <!-- Modifier attributs -->
        <field name="name" position="attributes">
            <attribute name="required">True</attribute>
        </field>

        <!-- Ajouter dans un notebook -->
        <xpath expr="//notebook" position="inside">
            <page string="Mon Onglet">
                <field name="mon_champ_custom"/>
            </page>
        </xpath>
    </field>
</record>
```

---

## 6. Frontend — OWL 2 (JavaScript)

### 6.1 Concepts fondamentaux

| Concept | Description |
|---------|-------------|
| **Components** | Classes JS avec template QWeb, état réactif, lifecycle |
| **Hooks** | `useState`, `useRef`, `onWillStart`, `onMounted`, `onWillUnmount` |
| **Services** | Singletons injectables (notifications, RPC, user) |
| **Registries** | Registres dynamiques pour composants, actions, vues |
| **Props** | Propriétés transmises du parent à l'enfant |

### 6.2 Exemple de composant OWL

```javascript
/** @odoo-module */
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MonDashboard extends Component {
    static template = "mon_module.Dashboard";
    static props = {
        title: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            compteur: 0,
            donnees: [],
        });

        this.orm = useService("orm");
        this.notification = useService("notification");

        onMounted(() => {
            this.chargerDonnees();
        });
    }

    async chargerDonnees() {
        this.state.donnees = await this.orm.searchRead(
            "mon.modele",
            [["etat", "=", "confirme"]],
            ["name", "montant"]
        );
    }

    incrementer() {
        this.state.compteur++;
        this.notification.add("Compteur incrémenté !", { type: "success" });
    }
}

// Enregistrement comme action client
registry.category("actions").add("mon_dashboard", MonDashboard);
```

Template QWeb associé (`static/src/xml/dashboard.xml`) :

```xml
<templates>
    <t t-name="mon_module.Dashboard">
        <div class="o_dashboard">
            <h2 t-out="props.title or 'Dashboard'"/>
            <button t-on-click="incrementer">
                Compteur: <t t-out="state.compteur"/>
            </button>
            <div t-foreach="state.donnees" t-as="item" t-key="item.id">
                <span t-out="item.name"/> - <span t-out="item.montant"/>
            </div>
        </div>
    </t>
</templates>
```

### 6.3 Composants OWL pré-intégrés (Odoo 18)

| Composant | Usage |
|-----------|-------|
| `ActionSwiper` | Interactions par geste (swipe mobile) |
| `CheckBox` | Case à cocher |
| `Dropdown` / `DropdownItem` | Menus déroulants |
| `Notebook` | Onglets |
| `Pager` | Pagination |
| `SelectMenu` | Menu de sélection |
| `TagsList` | Liste de tags |
| `ColorList` | Sélection de couleurs |

### 6.4 Bundles d'assets

```python
# Dans __manifest__.py
'assets': {
    'web.assets_backend': [
        'mon_module/static/src/**/*',
        # Ou fichier par fichier
        'mon_module/static/src/js/dashboard.js',
        'mon_module/static/src/xml/dashboard.xml',
        'mon_module/static/src/scss/dashboard.scss',
        # Prepend (charger avant)
        ('prepend', 'mon_module/static/src/scss/variables.scss'),
        # Remove (exclure un fichier)
        ('remove', 'autre_module/static/src/js/unwanted.js'),
        # Replace
        ('replace', 'autre_module/static/src/js/old.js',
                     'mon_module/static/src/js/new.js'),
    ],
    'web.assets_frontend': [
        'mon_module/static/src/frontend/**/*',
    ],
},
```

---

## 7. Templates QWeb

### Directives principales

| Directive | Usage |
|-----------|-------|
| `t-if` / `t-elif` / `t-else` | Rendu conditionnel |
| `t-foreach` / `t-as` | Boucle d'itération |
| `t-set` / `t-value` | Déclaration de variable |
| `t-esc` | Sortie avec échappement HTML (sécurisé) |
| `t-out` | Sortie moderne (remplace `t-raw` et `t-esc` en Odoo 17+) |
| `t-att-*` | Attribut HTML dynamique |
| `t-call` | Inclusion de sous-template |
| `t-inherit` / `t-inherit-mode` | Héritage de template |
| `t-cache` | Mise en cache de fragments |

```xml
<template id="mon_template">
    <div t-if="records">
        <t t-foreach="records" t-as="rec">
            <div t-att-class="'active' if rec.actif else 'inactive'">
                <span t-out="rec.name"/>
                <span t-out="rec.montant" t-options='{"widget": "monetary"}'/>
            </div>
        </t>
    </div>
    <div t-else="">Aucun enregistrement</div>
</template>
```

---

## 8. Contrôleurs Web & API

### 8.1 Contrôleurs HTTP

```python
from odoo import http
from odoo.http import request

class MonControleur(http.Controller):

    # Page web publique
    @http.route('/mon/page', type='http', auth='public', website=True)
    def ma_page(self, **kwargs):
        records = request.env['mon.modele'].sudo().search([])
        return request.render('mon_module.ma_page_template', {
            'records': records,
        })

    # API JSON (appels AJAX / RPC)
    @http.route('/mon/api/donnees', type='json', auth='user', methods=['POST'])
    def api_donnees(self, **kwargs):
        records = request.env['mon.modele'].search_read(
            [], ['name', 'montant'], limit=100
        )
        return {'status': 'ok', 'data': records}

    # Endpoint REST-like
    @http.route('/mon/api/record/<int:record_id>', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_record(self, record_id):
        record = request.env['mon.modele'].browse(record_id)
        if not record.exists():
            return request.not_found()
        return request.make_json_response({
            'id': record.id,
            'name': record.name,
        })
```

**Paramètres de `@http.route`** :

| Paramètre | Description |
|-----------|-------------|
| `route` | Chemin URL (supporte `<int:id>`, `<string:slug>`) |
| `type` | `'http'` (pages/REST) ou `'json'` (JSON-RPC) |
| `auth` | `'none'`, `'public'` (visiteur/utilisateur), `'user'` (authentifié requis) |
| `methods` | `['GET']`, `['POST']`, etc. |
| `csrf` | Protection CSRF (True par défaut) |
| `website` | `True` pour les pages du site web |

### 8.2 Méthodes utiles de `request`

```python
request.render(template, qcontext=None)     # Rendre un template QWeb
request.redirect(location, code=303)         # Redirection
request.not_found()                          # Erreur 404
request.make_response(data, headers=None)    # Réponse HTTP personnalisée
request.make_json_response(data)             # Réponse JSON
```

---

## 9. API externe (XML-RPC / JSON-RPC)

### 9.1 XML-RPC

```python
import xmlrpc.client

url = 'https://mon-odoo.hma.business'
db = 'ma_base'
username = 'admin'
password = 'mon_api_key'

# 1. Authentification
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

# 2. Appels ORM
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# search_read
partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
    [[('is_company', '=', True)]],
    {'fields': ['name', 'email'], 'limit': 10}
)

# create
new_id = models.execute_kw(db, uid, password, 'res.partner', 'create',
    [{'name': 'Nouveau Client', 'email': 'client@test.com'}]
)

# write
models.execute_kw(db, uid, password, 'res.partner', 'write',
    [[new_id], {'phone': '0594123456'}]
)

# unlink
models.execute_kw(db, uid, password, 'res.partner', 'unlink', [[new_id]])
```

### 9.2 JSON-RPC

```python
import requests

url = 'https://mon-odoo.hma.business/jsonrpc'

def jsonrpc(url, service, method, args):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": args,
        },
        "id": 1,
    }
    return requests.post(url, json=payload).json()['result']

uid = jsonrpc(url, "common", "login", ["ma_base", "admin", "password"])

result = jsonrpc(url, "object", "execute_kw", [
    "ma_base", uid, "password",
    "res.partner", "search_read",
    [[("is_company", "=", True)]],
    {"fields": ["name", "email"], "limit": 5}
])
```

### 9.3 Authentification session (pour clients web/mobile)

```python
session = requests.Session()
auth_response = session.post(f"{url}/web/session/authenticate", json={
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "ma_base",
        "login": "admin",
        "password": "mot_de_passe"
    },
    "id": 1
})
# Le cookie session_id est stocké automatiquement

result = session.post(f"{url}/web/dataset/call_kw", json={
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "res.partner",
        "method": "search_read",
        "args": [[["is_company", "=", True]]],
        "kwargs": {"fields": ["name", "email"], "limit": 10}
    },
    "id": 2
})
```

### 9.4 Modèles comptables principaux

| Modèle | Description |
|--------|-------------|
| `account.move` | Écritures comptables (factures, avoirs, OD) |
| `account.move.line` | Lignes d'écritures |
| `account.account` | Plan comptable |
| `account.journal` | Journaux |
| `account.tax` | Taxes |
| `account.fiscal.position` | Positions fiscales |
| `account.payment` | Paiements |
| `account.bank.statement` | Relevés bancaires |

### 9.5 Dépréciation (timeline)

| Version | Statut |
|---------|--------|
| Odoo 18 (2024) | XML-RPC et JSON-RPC fonctionnent normalement |
| Odoo 19 (2025) | Dépréciation avec warning dans les logs |
| Odoo 22 (2028) | **Suppression définitive** |

**Remplacement** : External JSON-2 API avec authentification Bearer API Key, modèle/méthode dans l'URL, arguments exclusivement nommés.

---

## 10. Sécurité

### 10.1 Droits d'accès (ir.model.access) — CSV

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_mon_modele_user,mon.modele.user,model_mon_modele,base.group_user,1,1,1,0
access_mon_modele_manager,mon.modele.manager,model_mon_modele,mon_module.group_manager,1,1,1,1
```

### 10.2 Règles d'enregistrement (ir.rule) — XML

```xml
<record id="rule_mon_modele_propres" model="ir.rule">
    <field name="name">Voir uniquement ses propres enregistrements</field>
    <field name="model_id" ref="model_mon_modele"/>
    <field name="domain_force">[
        '|', ('user_id', '=', user.id),
             ('user_id', '=', False)
    ]</field>
    <field name="groups" eval="[Command.link(ref('base.group_user'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
</record>
```

Les droits `ir.model.access` + les règles `ir.rule` se combinent : un utilisateur doit avoir l'accès au modèle **ET** satisfaire la règle de domaine.

### 10.3 Consolidation sécurité (Odoo 18)

`check_access_rights()` + `check_access_rule()` fusionnés en **`check_access()`**.

---

## 11. Fichiers de données

### 11.1 XML

```xml
<odoo>
    <data noupdate="1">
        <record id="enregistrement_demo" model="mon.modele">
            <field name="name">Exemple</field>
            <field name="montant">1500.00</field>
            <field name="partner_id" ref="base.res_partner_1"/>
        </record>

        <record id="seq_mon_modele" model="ir.sequence">
            <field name="name">Séquence Mon Modèle</field>
            <field name="code">mon.modele</field>
            <field name="prefix">MOD/%(year)s/</field>
            <field name="padding">5</field>
        </record>
    </data>
</odoo>
```

### 11.2 CSV

Pour le chargement en masse (typiquement `ir.model.access.csv`). Le nom du fichier doit correspondre au nom technique du modèle.

### 11.3 Séquences

```python
reference = self.env['ir.sequence'].next_by_code('mon.modele')
# Résultat : "MOD/2026/00001"

partner = self.env.ref('base.res_partner_1')  # Référence par XML ID
```

---

## 12. Tests

### 12.1 Classes de test

| Classe | Usage |
|--------|-------|
| `TransactionCase` | Tests unitaires avec rollback automatique |
| `SingleTransactionCase` | Transaction partagée entre tests |
| `HttpCase` | Tests intégration HTTP + tours navigateur |
| `Form` | Simulation d'interactions formulaire (onchange) |

### 12.2 Exemple complet

```python
from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import ValidationError

class TestMonModele(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.modele = cls.env['mon.modele'].create({
            'name': 'Test',
            'montant': 100,
        })

    def test_creation(self):
        self.assertEqual(self.modele.name, 'Test')
        self.assertEqual(self.modele.montant, 100)

    def test_confirmation(self):
        self.modele.action_confirmer()
        self.assertEqual(self.modele.etat, 'confirme')

    def test_contrainte_montant(self):
        with self.assertRaises(ValidationError):
            self.modele.write({'montant': -50})

    def test_formulaire(self):
        """Test du comportement onchange via Form."""
        with Form(self.env['mon.modele']) as f:
            f.name = 'Nouveau'
            f.partner_id = self.env.ref('base.res_partner_1')
        record = f.save()
        self.assertTrue(record.adresse)
```

### 12.3 Exécution

```bash
# Tous les tests d'un module
./odoo-bin -d test_db --test-enable -i mon_module --stop-after-init

# Tests spécifiques avec tags
./odoo-bin -d test_db --test-tags /mon_module:TestMonModele.test_creation
```

> **Odoo 18** : nouveau framework de tests JS **HOOT** (remplace QUnit).

---

## 13. Migrations

### 13.1 Structure

```
migrations/
└── 18.0.1.1.0/
    ├── pre-migrate.py   # Avant la mise à jour du schéma
    └── post-migrate.py  # Après la mise à jour du schéma
```

### 13.2 Scripts

```python
# pre-migrate.py
def migrate(cr, version):
    cr.execute("ALTER TABLE mon_modele ADD COLUMN IF NOT EXISTS temp_col VARCHAR")

# post-migrate.py
def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    for record in env['mon.modele'].search([]):
        record.nouveau_champ = record.ancien_champ
```

---

## 14. Développement mobile

### 14.1 Approche PWA (recommandée par Odoo)

Depuis Odoo 16+, la **PWA est l'approche officielle** pour l'accès mobile.

- Installation sur l'écran d'accueil (Android et iOS)
- Navigation sans bordure (expérience app native)
- Push notifications (via Firebase)
- Contenu adaptatif selon la taille de l'appareil

**Installation** :
- **Android (Chrome)** : Menu > "Installer l'application"
- **iOS (Safari)** : Bouton Partager > "Sur l'écran d'accueil"

**Limites** : pas de mode offline complet, pas de service worker avancé, push via Firebase uniquement.

### 14.2 ActionSwiper — Composant OWL mobile

```xml
<ActionSwiper
  onLeftSwipe="{
    action: '() => deleteItem()',
    icon: 'fa-delete',
    bgColor: 'bg-danger'
  }"
  onRightSwipe="{
    action: '() => starItem()',
    icon: 'fa-star',
    bgColor: 'bg-warning'
  }">
  <div>Élément balayable</div>
</ActionSwiper>
```

| Prop | Type | Description |
|------|------|-------------|
| `animationOnMove` | Boolean | Effet de translation pendant le swipe |
| `animationType` | String | `bounce` ou `forwards` |
| `onLeftSwipe` | Object | Action, icône, couleur pour swipe gauche |
| `onRightSwipe` | Object | Action, icône, couleur pour swipe droit |
| `swipeDistanceRatio` | Number | Ratio minimum de largeur à balayer |

### 14.3 Bridge JavaScript natif (OdooMobile)

Disponible quand l'app tourne dans le conteneur mobile natif Odoo :

| Méthode | Description |
|---------|-------------|
| `OdooMobile.showToast()` | Notification temporaire |
| `OdooMobile.vibrate()` | Retour haptique |
| `OdooMobile.showSnackbar()` | Message avec action |
| `OdooMobile.showNotification()` | Notification système |
| `OdooMobile.createContact()` | Créer un contact dans le répertoire |
| `OdooMobile.scanBarcode()` | Scanner de codes-barres |
| `OdooMobile.switchAccount()` | Changer de compte utilisateur |

Ces méthodes sont **ignorées silencieusement** sur desktop (rétrocompatible).

### 14.4 Options pour apps mobiles custom

| Approche | Performance | Réutilisation web | Accès natif | Recommandé |
|----------|-------------|-------------------|-------------|------------|
| **PWA Odoo** | Moyenne | Maximale | Limité | Court terme |
| **Capacitor/Ionic** | Moyenne | Très élevée | Oui | Équipe web |
| **React Native** | Élevée | Faible | Oui | App riche |
| **Flutter** | Très élevée | Faible | Oui | UI performante |
| **WebView native** | Faible-Moyenne | Maximale | Limité | MVP rapide |

### 14.5 Authentification mobile (session)

```python
import requests

session = requests.Session()
session.post(f"{url}/web/session/authenticate", json={
    "jsonrpc": "2.0",
    "method": "call",
    "params": {"db": "ma_base", "login": "admin", "password": "pass"},
    "id": 1
})
# Le cookie session_id est réutilisé automatiquement pour les appels suivants
```

Recommandation : session-based auth pour les apps mobiles (vs API keys pour serveur-à-serveur).

---

## 15. Changelog Odoo 17 → 18

### 15.1 Breaking changes ORM

| Changement | Détail |
|------------|--------|
| `_sequence` supprimé | PostgreSQL gère la séquence de clé primaire par défaut |
| `name_get()` déprécié | Lire `display_name` directement |
| `search()` pas toujours appelé | Surcharger `search_fetch()` à la place |
| `copy_data()` multi-recordset | Retourne une **liste**, pas un dictionnaire |
| Sécurité consolidée | `check_access_rights()` + `check_access_rule()` → **`check_access()`** |
| `_name_search()` supprimé | Remplacé par `_search_display_name()` |

### 15.2 Changements OWL 2.x

| Avant (Odoo 17) | Après (Odoo 18) |
|-----------------|-----------------|
| `mounted()` méthode | `onMounted()` hook dans `setup()` |
| `willUnmount()` méthode | `onWillUnmount()` hook dans `setup()` |
| `t-raw` | `t-out` |
| `t-set` (slots) | `t-set-slot` |
| `t-foreach` sans `t-key` | `t-key` **obligatoire** |
| `Store`, `Router`, `Context` | **Supprimés** |
| `debounce()`, `browser` | **Supprimés** |

**Nouvelles APIs** : `reactive()`, `markRaw()`, `toRaw()`, `useEffect`, classe `App`.

### 15.3 Changements frontend

| Changement | Détail |
|------------|--------|
| `<tree>` → `<list>` | Renommé dans tout le code |
| Chatter | `<chatter/>` remplace `<div class="oe_chatter">...</div>` |
| Kanban | `kanban-box` → `card`, nouveau `kanban_color_picker` |
| `/** @odoo-module **/` | Peut être supprimé de tous les fichiers JS |
| `attrs` déprécié | Expressions directes : `invisible="etat != 'brouillon'"` |
| Tests JS | **HOOT** remplace QUnit |

### 15.4 Modules supprimés (Odoo 18)

eBay Connector, Alipay, PayU Latam, PayUmoney, Ogone/SIPS (remplacés par Worldline).

### 15.5 Nouveautés Odoo 18

- **Peppol** (facturation électronique européenne)
- **Comptes partagés multi-sociétés** (un compte peut appartenir à plusieurs sociétés)
- **URLs lisibles** et **Passkeys (WebAuthn)**
- **PWA dédiées** pour les apps mobiles
- **Réconciliation de brouillons** et améliorations comptables

---

## 16. Pertinence pour le projet HMA

### 16.1 Points d'intégration Odoo ↔ Stack HMA

1. **FEC comme pivot** : Odoo exporte le FEC au même format que Pennylane → importable dans Supabase (`fec_ecriture`)
2. **API XML-RPC/JSON-RPC** : lecture temps réel des écritures Odoo (`account.move.line`, `account.account`)
3. **Multi-sociétés** : 4 structures HMA = 4 `res.company` distinctes dans Odoo
4. **Module `l10n_fr_department_oversea`** : spécifiquement pertinent pour la **Guyane (973)**
5. **DAS2 via OCA** : automatise une obligation fiscale gérée par le cabinet HMA

### 16.2 Limites d'Odoo vs stack actuel

| Besoin HMA | Odoo natif | Stack Supabase actuel |
|------------|------------|----------------------|
| SIG (9 soldes + CAF) | Non disponible | `mv_sig` |
| Bilan fonctionnel (FRNG/BFR/TN) | Non disponible | `mv_bilan_fonctionnel` |
| Résultat différentiel / seuil rentabilité | Non disponible | `mv_resultat_differentiel` |
| Mapping analytique PCG (V/F, BF) | Non disponible | `pcg_analytique` (1 412 comptes) |
| Consolidation groupe | Enterprise uniquement | À développer |

### 16.3 Recommandation mobile pour HMA

1. **PWA Odoo** (court terme) : zéro développement, accès mobile immédiat
2. **Capacitor/Ionic** (moyen terme) : si besoin d'app dédiée, réutilise les compétences web
3. **React Native** (long terme) : si besoin d'app mobile riche avec mode offline et interaction agents IA

---

*Document généré à partir de la documentation officielle Odoo SA (v17/18), OCA/l10n-france (branche 18.0), et github.com/odoo/owl. Aucune source tierce non officielle.*
