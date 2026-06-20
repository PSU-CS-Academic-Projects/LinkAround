# LinkAround

> A role-aware portfolio matching platform that connects job **seekers** and **employers** through a card-based directory, field/region filtering, and private Google-Drive-style shortlist folders — *portfolio matching, not job posting*.

---

## Project Information

| Field | Details |
|-------|---------|
| Subject | Web Systems and Technologies |
| Academic Year | 2025-2026 |
| Project Category | Web Development / Portfolio Platform / Recruitment |
| Instructor | Ma'am Divine Grace Caabay |

### Members

* _Add team member name_
* _Add team member name_

---

## Project Description

LinkAround is a full-stack Django web application that reimagines early-career hiring around **portfolios instead of job posts**. Seekers publish one focused portfolio profile — degree level, region, work arrangement, preferred fields, and an uploaded portfolio file — and control their own visibility and download permissions. Employers browse a card-based directory, filter by business field, region, and work mode, and save promising candidates into private, foldered shortlists.

Rather than running a noisy job marketplace, the platform keeps the workflow intentional and private: employers organize candidates into Drive-style folders, and seekers are notified (in-app and by email) the moment their portfolio is shortlisted. Role-based access control cleanly separates the seeker, employer, and admin experiences, while a Nordic-inspired theme ships with Auto / Light / Dark modes.

---

## Features

* **Role-Based Accounts:** Separate Seeker, Employer, and Admin experiences enforced by group-based access control, with guarded views and an onboarding role-selection flow.
* **Social & Manual Sign-In:** Username/password plus Google, Microsoft, and Apple sign-in (via django-allauth), opened in a focused popup window so the login page stays in place.
* **Structured Seeker Profiles:** Degree level, region/location, work arrangement, preferred fields, bio, and a validated portfolio file upload, with per-profile visibility and download toggles.
* **Card-Based Portfolio Directory:** Browse seekers as cards with filtering by field, region, and work arrangement, keyword search (name / degree / bio), and sorting (newest, oldest, name).
* **Private Shortlist Folders:** Google-Drive-style folders for employers — create, rename, delete, and move saved candidates between folders, with "All saved" and "Unfiled" views.
* **Covered-Field Folders:** Public seekers are auto-grouped under each business field an employer registered, separate from manual shortlist folders.
* **Candidate Notifications:** Seekers receive an in-app notification and an email when shortlisted, with a mark-as-read notifications page.
* **Gated File Serving:** Portfolio files are served only to employer/admin accounts and only when the seeker allows downloads — never from a public media URL.
* **Theming:** Nordic color palette with an Auto / Light / Dark toggle persisted in the browser.

---

## Technologies Used

* Django 6 (Python 3.13)
* PostgreSQL (production) / SQLite (local) via `dj-database-url`
* django-allauth (Google / Microsoft / Apple social authentication)
* django-tailwind + Tailwind CSS v4 + DaisyUI v5 (styling engine)
* Gunicorn + WhiteNoise (production app server & static serving)
* psycopg (PostgreSQL driver)

---

## Installation Guide

> Follow these steps to run LinkAround locally on Windows. `manage.py` lives in `LinkAround/LinkAround_app/`.

1. **Open a terminal in the project root (`LinkAround`), then enter the Django app folder**
```bash
   cd LinkAround_app
```

2. **Activate the virtual environment** (recommended)
```bash
   ..\LinkAround\Scripts\Activate.ps1
```
   If PowerShell blocks activation, call the venv Python directly:
```bash
   ..\LinkAround\Scripts\python.exe -m pip --version
```

3. **Install Python dependencies**
```bash
   python -m pip install -r ..\..\requirements.txt
```

4. **Apply database migrations**
```bash
   python manage.py migrate
```

5. **Build the Tailwind assets**
```bash
   cd LookAround\static_src
   npm install
   npm run build
   cd ..\..
```

6. **(Optional) Start the Tailwind watcher** in a second terminal
```bash
   python manage.py tailwind start
```

7. **Run the development server**
```bash
   python manage.py runserver 8080
```

8. Open your browser and navigate to `http://127.0.0.1:8080/` to start browsing.

---

## Main Routes

| Route | Purpose |
|-------|---------|
| `/` | Home / dashboard (role-aware) |
| `/accounts/login/` | Username/password and social sign-in |
| `/accounts/register/` | Account registration |
| `/accounts/choose-role/` | Role onboarding for social-login users |
| `/seeker/register/` | Seeker profile registration |
| `/employer/register/` | Employer profile registration |
| `/seekers/` | Card-based portfolio directory |
| `/employer/<id>/dashboard/` | Employer private shortlist + folders |
| `/seeker/<id>/notifications/` | Seeker notifications |
| `/oauth/<provider>/login/callback/` | django-allauth OAuth callbacks |

---

## Theming & Dark Mode

* Implemented with DaisyUI themes and an **Auto / Light / Dark** toggle.
* **Auto** follows the operating system color scheme.
* The selected mode is saved in browser `localStorage`, so it persists across visits.

---

## Social Sign-In (SSO) Setup

Social sign-in requires a `SocialApp` row in Django admin **and** the exact callback URL registered in the provider console. The buttons open the provider in a popup; on success the popup closes and the main window lands on the dashboard.

### Microsoft

1. In the Microsoft Entra admin center, create an **App Registration**.
2. Set supported account types to *Accounts in any organizational directory and personal Microsoft accounts*.
3. Add a **Web** redirect URI: `http://localhost:8080/oauth/microsoft/login/callback/`.
4. Add the Microsoft Graph delegated permission `User.Read`.
5. Create a client secret.
6. In Django admin, add the Microsoft **Social Application** (Provider: Microsoft, Client ID, Secret, Site: your host).

### Google

1. In Google Cloud Console, create an OAuth 2.0 Client (Web application).
2. Add an **Authorized redirect URI** matching your host exactly, e.g.
   `https://<your-host>/oauth/google/login/callback/`.
3. Add the host as an **Authorized JavaScript origin**.
4. Create the Google **Social Application** in Django admin with the Client ID and Secret.

> Most "I can't sign in with Google" issues are a `redirect_uri_mismatch` — the URL in the provider console must match your live host (including the ngrok/production domain) character-for-character.

---

## Production Deployment

LinkAround targets a portable PaaS deploy (Railway, Render, Fly.io, or a VPS) using **Gunicorn + WhiteNoise**. All runtime config is environment-driven — see [.env.example](.env.example) for every variable the app reads.

### Deployment artifacts (repo root)

* `Procfile` — `release:` runs migrations; `web:` boots Gunicorn against `LinkAround/LinkAround_app`.
* `runtime.txt` — pins the Python version.
* `requirements.txt` — includes `gunicorn`, `whitenoise`, `dj-database-url`, and `psycopg`.
* `.gitignore` — keeps secrets, the venv, SQLite, `media/`, and collected static out of git.

### Required environment variables (production)

```
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<a long random value>
DJANGO_ALLOWED_HOSTS=yourapp.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourapp.example.com
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
DJANGO_BEHIND_TLS_PROXY=true
```

With `DEBUG=False`, settings automatically enable secure cookies, HSTS, the SSL redirect, and refuse to boot on the insecure development `SECRET_KEY`.

### Pre-deploy checklist (run locally first)

```bash
pip install -r requirements.txt
python LinkAround\LinkAround_app\manage.py check --deploy
python LinkAround\LinkAround_app\manage.py makemigrations --check --dry-run
python LinkAround\LinkAround_app\manage.py test LinkAround_main
cd LinkAround\LinkAround_app\LookAround\static_src && npm run build && cd ..\..\..\..
python LinkAround\LinkAround_app\manage.py collectstatic --noinput
```

### SQLite → PostgreSQL data migration

The schema is database-agnostic, so only a data copy is needed:

```bash
# 1) Export from the current SQLite DB (DATABASE_URL unset)
python LinkAround\LinkAround_app\manage.py dumpdata --natural-primary --natural-foreign ^
  --exclude contenttypes --exclude auth.permission --exclude admin.logentry ^
  --exclude sessions.session -o data.json

# 2) Point at Postgres, create the schema, then load the data
set DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
python LinkAround\LinkAround_app\manage.py migrate
python LinkAround\LinkAround_app\manage.py loaddata data.json
```

> **Portfolio files:** `dumpdata` carries only file *paths*, not bytes. Copy the `media/` directory to the production host, or configure object storage (S3 / Cloudinary) — PaaS disks are ephemeral, so uploaded portfolios will not persist on local disk across deploys.

---

## Testing

The project ships with an automated test suite covering role access, the shortlist-folder feature, directory filtering/sorting, structured profiles, cross-role guards, and migration/system-check health.

```bash
python LinkAround\LinkAround_app\manage.py test LinkAround_main
```

---

## Screenshots

> _Add screenshots of the home page, portfolio directory, employer shortlist folders, and the seeker profile form here._

---

## Live Demo

**Live URL:** _N/A — runs locally, or tunneled via ngrok during development._

> If a tunneled/hosted instance appears inaccessible, the deployment may be paused due to free-tier inactivity limits. Restart the server (and ngrok tunnel) to bring it back online.

---

## Future Improvements

* **Object Storage for Media:** Move portfolio file uploads to S3 / Cloudinary so files persist across PaaS deploys.
* **Saved Searches & Alerts:** Let employers save directory filters and get notified when new matching seekers appear.
* **Richer Seeker Analytics:** Show seekers how often their portfolio was viewed or shortlisted, and by which fields.
* **Continuous Integration:** Add a GitHub Actions workflow to run the test suite and `collectstatic` on every push.
* **In-App Messaging:** Allow employers and shortlisted seekers to exchange messages without leaving the platform.

---

## Notes for Development

* Email notifications use the console backend in development (printed to the server log).
* Portfolio uploads are stored under `media/` and served only through the gated `portfolio_file` view.
* Default field and region options are auto-seeded the first time the app is accessed if those tables are empty.

---

## Troubleshooting

* **`runserver` fails with "No module named django":** you are using the wrong Python interpreter — use the project venv executable shown in the Installation Guide.
* **Tailwind commands fail:** verify Node.js and npm are installed and available on your PATH.
* **CSS changes don't appear:** rebuild the bundle with `npm run build` from `LookAround/static_src` (the compiled file is what the server serves).
* **Google sign-in fails:** confirm the `SocialApp` exists in Django admin and the redirect URI in Google Cloud Console matches your host exactly.
