#!/usr/bin/env python
"""
Vaultwarden Crypto Helper — déchiffrement des secrets via master password.

Gère le flux complet :
1. Login password-based → access_token + clé chiffrée + clé privée RSA
2. Dérivation master key (PBKDF2-SHA256) → clé symétrique utilisateur
3. Déchiffrement de la clé RSA privée → déchiffrement des clés d'organisation
4. Déchiffrement des ciphers avec la clé d'organisation

Usage:
  python vw-crypto.py list [filtre]
  python vw-crypto.py get <nom> [--field username|password|uri|notes] [--json]
  python vw-crypto.py set <nom> <username> <password> [uri]
  python vw-crypto.py export <nom> <VAR_ENV>
"""

import sys
import json
import hashlib
import hmac as hmac_mod
import base64
import os
import urllib.request
import urllib.parse

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding


# --- Configuration ---
ORG_ID = 'f7bd1540-c6ed-45fb-8e8e-3ca9a9d9db23'  # stack_hma


# --- Chargement .env ---

def load_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    env = {}
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env


# --- HTTP helpers ---

def http_post(url, data=None, headers=None, json_data=None):
    if json_data is not None:
        body = json.dumps(json_data).encode('utf-8')
        headers = headers or {}
        headers['Content-Type'] = 'application/json'
    elif data is not None:
        body = urllib.parse.urlencode(data).encode('utf-8')
        headers = headers or {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


# --- Crypto Bitwarden/Vaultwarden ---

def make_master_key(password, email, kdf_iterations):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                email.lower().encode('utf-8'), kdf_iterations, dklen=32)


def make_master_password_hash(password, email, kdf_iterations):
    master_key = make_master_key(password, email, kdf_iterations)
    return base64.b64encode(
        hashlib.pbkdf2_hmac('sha256', master_key, password.encode('utf-8'), 1, dklen=32)
    ).decode('utf-8')


def stretch_key(key):
    """HKDF-Expand pour obtenir enc_key (32B) + mac_key (32B)."""
    enc_key = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'enc').derive(key)
    mac_key = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'mac').derive(key)
    return enc_key, mac_key


def decrypt_aes_cbc(enc_string, enc_key, mac_key):
    """Déchiffre type 2 = AES-CBC-256 + HMAC-SHA256. Retourne des bytes bruts."""
    if not enc_string:
        return b''

    raw = enc_string
    if raw.startswith('2.'):
        raw = raw[2:]
    elif '.' in raw.split('|')[0]:
        return b''  # Type non supporté

    parts = raw.split('|')
    if len(parts) < 2:
        return b''

    iv = base64.b64decode(parts[0])
    ct = base64.b64decode(parts[1])
    mac = base64.b64decode(parts[2]) if len(parts) > 2 else None

    # Vérification HMAC
    if mac and mac_key:
        expected = hmac_mod.new(mac_key, iv + ct, hashlib.sha256).digest()
        if not hmac_mod.compare_digest(mac, expected):
            raise ValueError('HMAC verification failed')

    # Déchiffrement AES-CBC
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    padded = cipher.decryptor().update(ct) + cipher.decryptor().finalize()

    # Workaround: re-decrypt proprement
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def encrypt_aes_cbc(plaintext_bytes, enc_key, mac_key):
    """Chiffre en type 2 = AES-CBC-256 + HMAC-SHA256. Retourne une enc_string."""
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext_bytes) + padder.finalize()
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    mac = hmac_mod.new(mac_key, iv + ct, hashlib.sha256).digest()
    return '2.' + base64.b64encode(iv).decode() + '|' + base64.b64encode(ct).decode() + '|' + base64.b64encode(mac).decode()


def encrypt_enc_string(plaintext, enc_key, mac_key):
    """Chiffre une chaîne UTF-8 en enc_string type 2."""
    if not plaintext:
        return None
    return encrypt_aes_cbc(plaintext.encode('utf-8'), enc_key, mac_key)


def decrypt_enc_string(enc_string, enc_key, mac_key):
    """Déchiffre une enc_string et retourne du texte UTF-8."""
    if not enc_string:
        return ''
    try:
        raw = decrypt_aes_cbc(enc_string, enc_key, mac_key)
        return raw.decode('utf-8')
    except Exception as e:
        return f'[decrypt error: {e}]'


def decrypt_rsa_oaep(enc_string, private_key):
    """Déchiffre type 4 = RSA-OAEP-SHA1. Retourne des bytes bruts."""
    raw = enc_string
    if raw.startswith('4.'):
        raw = raw[2:]

    ct = base64.b64decode(raw)
    return private_key.decrypt(
        ct,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )


def decrypt_symmetric_key(encrypted_key_str, master_key):
    """Déchiffre la clé symétrique utilisateur (retournée par login)."""
    enc_key, mac_key = stretch_key(master_key)
    raw = decrypt_aes_cbc(encrypted_key_str, enc_key, mac_key)

    if len(raw) == 64:
        return raw[:32], raw[32:]
    elif len(raw) == 32:
        return stretch_key(raw)
    else:
        raise ValueError(f'Symmetric key unexpected length: {len(raw)}')


def decrypt_private_key(encrypted_private_key, user_enc_key, user_mac_key):
    """Déchiffre la clé RSA privée de l'utilisateur."""
    raw = decrypt_aes_cbc(encrypted_private_key, user_enc_key, user_mac_key)
    return serialization.load_der_private_key(raw, password=None)


def decrypt_org_key(encrypted_org_key, private_key):
    """Déchiffre la clé symétrique d'une organisation (chiffrée RSA-OAEP)."""
    raw = decrypt_rsa_oaep(encrypted_org_key, private_key)

    if len(raw) == 64:
        return raw[:32], raw[32:]
    elif len(raw) == 32:
        return stretch_key(raw)
    else:
        raise ValueError(f'Org key unexpected length: {len(raw)}')


# --- Session Vaultwarden ---

class VwSession:
    """Gère l'authentification et le déchiffrement Vaultwarden."""

    def __init__(self, base_url, email, master_password):
        self.base_url = base_url
        self.email = email
        self.master_password = master_password
        self.access_token = None
        self.user_enc_key = None
        self.user_mac_key = None
        self.org_keys = {}  # org_id -> (enc_key, mac_key)

    def login(self):
        # Prelogin
        prelogin = http_post(f'{self.base_url}/identity/accounts/prelogin',
                             json_data={'email': self.email})
        kdf_iterations = prelogin['kdfIterations']

        # Derive keys
        master_key = make_master_key(self.master_password, self.email, kdf_iterations)
        master_hash = make_master_password_hash(self.master_password, self.email, kdf_iterations)

        # Login
        login_resp = http_post(f'{self.base_url}/identity/connect/token', data={
            'grant_type': 'password',
            'username': self.email,
            'password': master_hash,
            'scope': 'api offline_access',
            'client_id': 'cli',
            'deviceIdentifier': 'hma-cli-python',
            'deviceType': '14',
            'deviceName': 'HMA-CLI-Python',
        })

        self.access_token = login_resp['access_token']

        # Déchiffrer la clé symétrique utilisateur
        self.user_enc_key, self.user_mac_key = decrypt_symmetric_key(
            login_resp['Key'], master_key)

        # Déchiffrer la clé privée RSA (pour les clés d'organisation)
        if login_resp.get('PrivateKey'):
            self.private_key = decrypt_private_key(
                login_resp['PrivateKey'], self.user_enc_key, self.user_mac_key)
        else:
            self.private_key = None

        # Récupérer les clés d'organisation via /api/sync
        headers = {'Authorization': f'Bearer {self.access_token}'}
        sync = http_get(f'{self.base_url}/api/sync', headers=headers)

        for org in sync.get('profile', {}).get('organizations', []):
            org_id = org.get('id', '')
            org_key_enc = org.get('key', '')
            if org_key_enc and self.private_key:
                try:
                    enc_k, mac_k = decrypt_org_key(org_key_enc, self.private_key)
                    self.org_keys[org_id] = (enc_k, mac_k)
                except Exception as e:
                    print(f"Warning: cannot decrypt org key for {org.get('name')}: {e}",
                          file=sys.stderr)

    def get_keys_for_cipher(self, cipher):
        """Retourne (enc_key, mac_key) appropriées pour un cipher."""
        org_id = cipher.get('organizationId')
        if org_id and org_id in self.org_keys:
            return self.org_keys[org_id]
        return self.user_enc_key, self.user_mac_key

    def fetch_ciphers(self, org_id=None):
        headers = {'Authorization': f'Bearer {self.access_token}'}
        data = http_get(f'{self.base_url}/api/ciphers', headers=headers)
        ciphers = data.get('data', [])
        if org_id:
            ciphers = [c for c in ciphers if c.get('organizationId') == org_id]
        return ciphers

    def decrypt_cipher(self, cipher):
        enc_key, mac_key = self.get_keys_for_cipher(cipher)

        name = decrypt_enc_string(cipher.get('name', ''), enc_key, mac_key)

        login = cipher.get('login') or {}
        username = decrypt_enc_string(login.get('username', ''), enc_key, mac_key)
        password = decrypt_enc_string(login.get('password', ''), enc_key, mac_key)
        notes = decrypt_enc_string(cipher.get('notes', ''), enc_key, mac_key)

        uris = []
        for u in (login.get('uris') or []):
            uris.append(decrypt_enc_string(u.get('uri', ''), enc_key, mac_key))

        return {
            'id': cipher.get('id', ''),
            'name': name,
            'username': username,
            'password': password,
            'uris': uris,
            'notes': notes,
            'organizationId': cipher.get('organizationId', ''),
        }


# --- Commandes CLI ---

def get_session(env):
    session = VwSession(
        base_url=env['VAULTWARDEN_URL'],
        email=env.get('VAULTWARDEN_EMAIL', 'poworkiki@gmail.com'),
        master_password=env['VAULTWARDEN_MASTER_PASSWORD'],
    )
    session.login()
    return session


def cmd_list(args, env):
    filtre = args[0].lower() if args else ''
    session = get_session(env)
    ciphers = session.fetch_ciphers(ORG_ID)

    items = []
    for c in ciphers:
        d = session.decrypt_cipher(c)
        if filtre and filtre not in d['name'].lower():
            continue
        items.append(d)

    if not items:
        print('Aucun secret' + (f' pour "{filtre}"' if filtre else ''))
        return

    max_name = max(len(i['name']) for i in items)
    max_user = max(len(i['username']) for i in items)
    header = f"{'Nom':<{max_name}}  {'Username':<{max_user}}  {'Password':>8}  URI"
    print(header)
    print('-' * len(header))
    for item in sorted(items, key=lambda x: x['name']):
        has_pw = 'YES' if item['password'] else 'NO'
        uri = item['uris'][0] if item['uris'] else ''
        print(f"{item['name']:<{max_name}}  {item['username']:<{max_user}}  {has_pw:>8}  {uri}")
    print(f"\n{len(items)} secret(s)")


def cmd_get(args, env):
    if not args:
        print('Usage: vw-crypto.py get <nom> [--field ...] [--json]', file=sys.stderr)
        sys.exit(1)

    name = args[0]
    field = 'password'
    json_mode = False

    i = 1
    while i < len(args):
        if args[i] == '--field' and i + 1 < len(args):
            field = args[i + 1]
            i += 2
        elif args[i] == '--json':
            json_mode = True
            i += 1
        else:
            i += 1

    session = get_session(env)
    ciphers = session.fetch_ciphers(ORG_ID)

    # Recherche exacte
    matches = [session.decrypt_cipher(c) for c in ciphers
               if decrypt_enc_string(c.get('name', ''), *session.get_keys_for_cipher(c)) == name]

    # Fallback sous-chaîne
    if not matches:
        all_decrypted = [session.decrypt_cipher(c) for c in ciphers]
        matches = [d for d in all_decrypted if name.lower() in d['name'].lower()]

    if not matches:
        print(f"Secret '{name}' introuvable (org stack_hma)", file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        print(f"Ambigu: {len(matches)} résultats", file=sys.stderr)
        for m in matches:
            print(f"  - {m['name']}", file=sys.stderr)
        sys.exit(1)

    item = matches[0]

    if json_mode:
        out = {
            'name': item['name'],
            'username': item['username'],
            'uri': item['uris'],
            'has_password': bool(item['password']),
            'notes': item['notes'],
        }
        print(json.dumps(out, ensure_ascii=False))
    elif field == 'username':
        print(item['username'])
    elif field == 'uri':
        print(item['uris'][0] if item['uris'] else '')
    elif field == 'notes':
        print(item['notes'])
    elif field == 'password':
        print(item['password'])
    else:
        print(item.get(field, ''))


def cmd_export(args, env):
    if len(args) < 2:
        print('Usage: vw-crypto.py export <nom> <VAR_ENV>', file=sys.stderr)
        sys.exit(1)

    name = args[0]
    var_name = args[1]

    session = get_session(env)
    ciphers = session.fetch_ciphers(ORG_ID)

    for c in ciphers:
        d = session.decrypt_cipher(c)
        if d['name'] == name or name.lower() in d['name'].lower():
            print(f"export {var_name}='{d['password']}'")
            return

    print(f"Secret '{name}' introuvable", file=sys.stderr)
    sys.exit(1)


def cmd_set(args, env):
    """Crée ou met à jour un secret dans l'organisation."""
    if len(args) < 3:
        print('Usage: vw-crypto.py set <nom> <username> <password> [uri]', file=sys.stderr)
        sys.exit(1)

    name = args[0]
    username = args[1]
    password = args[2]
    uri = args[3] if len(args) > 3 else ''

    session = get_session(env)
    ciphers = session.fetch_ciphers(ORG_ID)

    # Clé de l'organisation
    org_enc_key, org_mac_key = session.org_keys[ORG_ID]

    # Chercher un cipher existant avec le même nom
    existing_id = None
    for c in ciphers:
        d = session.decrypt_cipher(c)
        if d['name'] == name:
            existing_id = c['id']
            break

    # Chiffrer les champs
    enc_name = encrypt_enc_string(name, org_enc_key, org_mac_key)
    enc_user = encrypt_enc_string(username, org_enc_key, org_mac_key)
    enc_pw = encrypt_enc_string(password, org_enc_key, org_mac_key)

    uris_payload = []
    if uri:
        enc_uri = encrypt_enc_string(uri, org_enc_key, org_mac_key)
        uris_payload = [{'match': None, 'uri': enc_uri}]

    payload = {
        'type': 1,  # Login
        'organizationId': ORG_ID,
        'name': enc_name,
        'notes': None,
        'login': {
            'username': enc_user,
            'password': enc_pw,
            'uris': uris_payload,
            'totp': None,
        },
        'collectionIds': [],
    }

    headers = {
        'Authorization': f'Bearer {session.access_token}',
        'Content-Type': 'application/json',
    }

    if existing_id:
        # PUT update
        url = f'{session.base_url}/api/ciphers/{existing_id}'
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='PUT', headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                print(f"OK: '{name}' mis à jour")
            else:
                print(f"ERREUR: HTTP {resp.status}", file=sys.stderr)
                sys.exit(1)
    else:
        # POST create
        url = f'{session.base_url}/api/ciphers'
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST', headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status in (200, 201):
                print(f"OK: '{name}' créé")
            else:
                print(f"ERREUR: HTTP {resp.status}", file=sys.stderr)
                sys.exit(1)


# --- Main ---

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    env = load_env()

    for var in ('VAULTWARDEN_URL', 'VAULTWARDEN_MASTER_PASSWORD'):
        if var not in env:
            print(f'{var} manquant dans .env', file=sys.stderr)
            sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {'list': cmd_list, 'get': cmd_get, 'set': cmd_set, 'export': cmd_export}
    if command in commands:
        commands[command](args, env)
    else:
        print(f'Commande inconnue: {command}', file=sys.stderr)
        sys.exit(1)
