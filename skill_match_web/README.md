# Skill Match (web version)

Flask port of the Tkinter app. Same features: register/login, campus feed (posts, likes, comments),
find tutors (search + program filter), help requests (accept/decline), profile with photo upload.

## Run locally
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                        # http://localhost:5000
```
With no `DATABASE_URL` it uses a local SQLite file (`skill_match.db`).

## Why it works on any server
The app itself is stateless. Everything that used to live on one computer is now shared:

| Before (Tkinter) | Now |
|---|---|
| `skill_match_data.json` | SQL database via `DATABASE_URL` (PostgreSQL in production) |
| `avatars/` folder | Stored in the database, served at `/avatar/<id>` |
| "current user" in the JSON | Signed session cookie (needs the same `SECRET_KEY` everywhere) |

So you can run 1 or 10 copies on any host, as long as they all share the same `DATABASE_URL` and `SECRET_KEY`.

## Environment variables
| Name | Purpose |
|---|---|
| `SECRET_KEY` | **Required in production.** Long random string, identical on every instance. `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | PostgreSQL URL. `postgres://` and `postgresql://` both work. |
| `COOKIE_SECURE` | Set `1` when served over HTTPS. |
| `APP_TZ` | Display timezone, default `Asia/Manila`. |

## Deploy options
Do NOT rely on a host's local disk or SQLite in production; many hosts wipe it on every deploy. Use PostgreSQL.

**Render (easy)** - push this folder to GitHub, then New > Blueprint (uses `render.yaml`). Add a `DATABASE_URL`
(Render Postgres, or a free one from Neon / Supabase). Start command: `gunicorn app:app`.

**Railway / Heroku-style hosts** - they read `Procfile` automatically. Add a Postgres plugin; `DATABASE_URL` is set for you.

**Docker / any VPS (DigitalOcean, AWS, etc.)**
```bash
docker build -t skill-match .
docker run -p 8000:8000 -e SECRET_KEY=... -e DATABASE_URL=postgresql://... -e COOKIE_SECURE=1 skill-match
```
Put Nginx or Caddy in front for HTTPS. Run several containers behind it for more capacity.

**PythonAnywhere** - upload the files, create a web app pointing at `app.py` (`app` is the WSGI object), set the env vars.

## Notes
- Tables are created automatically on first start.
- Passwords are hashed with Werkzeug (scrypt/pbkdf2) with per-user salts; forms are CSRF-protected.
- Old data in `skill_match_data.json` is not imported (its password hashes use a different scheme); users re-register.
