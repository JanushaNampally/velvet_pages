# Velvet Pages

A private, single-user reading archive + encrypted diary.
Built **only with Python + Django** (no React, Tailwind, Firebase or any JavaScript).

## Quick start
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py create_owner
python manage.py runserver

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py create_owner        # asks for phone, name, vault passphrase; prints your RECOVERY KEY once
python manage.py runserver
```

Open http://127.0.0.1:8000/ → enter your phone number → the 6-digit code is **printed in the terminal**
(dev mode) → enter it → enter your vault passphrase.

Run the tests (they cover login, encryption at rest, diary, uploads, backup/restore):

```bash
python manage.py test core
```

## How login & privacy work

1. **Phone OTP** proves it's you (rate-limited, 5-minute expiry, 5 attempts, hashed codes).
   Only the one registered number can ever log in; there is no registration page.
2. **Vault passphrase** (second factor) unlocks encryption. OTP alone can never read your data.
3. Diary text/title/mood, dialogues, thoughts and **screenshots** are encrypted with **AES-256-GCM**
   (`cryptography` library) using a random master key. The master key is stored only *wrapped*
   (by your passphrase via scrypt, and by your recovery key). Unlocked keys live in server RAM
   only and are dropped on lock / auto-lock / logout.
4. Screenshots sit in `private_storage/` (not web-served) and are decrypted per-request for you only.
5. Lose both passphrase **and** recovery key = data is unrecoverable. Store the recovery key offline.

## Real SMS codes

```bash
export VELVET_OTP_BACKEND=twilio TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... TWILIO_FROM=+1...
```

## PostgreSQL (optional; SQLite is the default)

```bash
pip install "psycopg[binary]"
export VELVET_DB=postgres PGDATABASE=velvet_pages PGUSER=postgres PGPASSWORD=... PGHOST=localhost
python manage.py migrate
```

## Backups

* UI: **Backup & Export** → create, verify, download, restore, readable export.
* Automatic: schedule `python manage.py make_backup --keep 10` (cron / Task Scheduler).
* Archive layout: `books/ memories/screenshots/ diary/encrypted_entries/ tags/ security/ export_manifest.json`
  (SHA-256 checksums for every file; "Verify" re-checks them; restore makes a safety backup first).
* Test a restore occasionally — a backup you never restored is only a hope.

## Production checklist

```bash
export VELVET_DEBUG=0 VELVET_SECRET_KEY='<long random>' VELVET_ALLOWED_HOSTS=yourdomain.com \
       VELVET_CSRF_ORIGINS=https://yourdomain.com
python manage.py collectstatic
gunicorn velvet.wsgi --workers 1 --threads 4   # ONE worker: the unlocked key is held in process memory
```
Serve behind HTTPS (nginx/Caddy) and serve `/static/` from `staticfiles/` (or add WhiteNoise).
Keep `private_storage/` and the database on encrypted disks and back them up off-site.

## Honest limitations (because of "Python + Django only")

| Spec item | What is done instead |
|---|---|
| Client-side encryption (Web Crypto) | Needs browser JavaScript. Encryption is **server-side** with a key that exists only in RAM while unlocked. DB admins / stolen DB / stolen backups cannot read content, but a compromised *running* server could. |
| Rich-text editor, live word count, auto-save | Need JavaScript. Plain-text editor (paragraphs/line breaks kept), word & character counts shown after saving, manual save. |
| Firebase phone auth | Own OTP implementation (console in dev, Twilio SMS in prod). |
| Passkeys | Not included. |
| Encrypted archive as a whole | Private content is ciphertext; book titles, tag names and dates are plain metadata. |
| Phone number change | Done on the server (`manage.py shell`). |

ML/DL/AI add-ons (OCR of screenshots, tag suggestions, semantic search) are not included in v1; they can be
added later in pure Python without touching the privacy design — keep them local so diary text never leaves your machine.
