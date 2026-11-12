# Gather · CodeAlpha Event Registration

A full-stack community event platform built for the CodeAlpha Backend Development Internship and a developer portfolio. Visitors discover events, create an account, reserve a place, and manage cancellations. Organizers use Django admin to manage events and attendance.

The application replaces manual attendance lists with authenticated, private registration records, duplicate prevention, and capacity controls shared by the API and administrator interface.

Repository: [Luel-dev27/CodeAlpha_EventRegistration](https://github.com/Luel-dev27/CodeAlpha_EventRegistration).

## Features

- Public event directory, event details, title/location search, upcoming/started filters, and availability filters.
- Signup with Django password validators, hashed passwords, token login, and token-revoking logout.
- Owner-only registration listing/details, cancellation, and reactivation of cancelled rows.
- PostgreSQL transactions and event-first row locking coordinate ordinary model saves, API writes, admin validation, reactivation, and capacity changes.
- Administrators cannot overbook events, reactivate into full/started events, or reduce capacity below active attendance.
- Optional pagination preserves existing array responses for clients that do not request pages.
- Batched capacity counts avoid N+1 queries in event and registration lists.
- Login, signup, and registration throttles; safe JSON errors; explicit CORS and security settings.
- Responsive React frontend with public browsing, authentication, a protected dashboard, loading/empty states, and cancellation confirmation.
- No unnecessary REST admin CRUD, JWT migration, external UI framework, or schema rewrite.

## Technology and verified runtime

Backend: Python, Django, Django REST Framework, PostgreSQL, psycopg 3, django-cors-headers, and python-dotenv. Frontend: React, React Router, Vite, JavaScript, and modular CSS. Tests: Django's test runner, Node's test runner, PostgreSQL threads, and existing Firefox/geckodriver through WebDriver.

Verified locally on **Python 3.12.3, Node.js 20.20.2, npm 11.21.1**, with Django 6.1.2 and disposable PostgreSQL 16. No system-wide upgrades are required for these versions. Install the backend's pinned `requirements.lock` and frontend's `package-lock.json` for the verified dependency set. `requirements.txt` retains the broader original direct-dependency ranges.

## Architecture

```text
React + React Router
       │ relative /api requests; Token header from tab memory
       ▼
Vite proxy (development/preview) or reverse proxy (deployment)
       ▼
Django middleware → DRF authentication/permissions → views/serializers
       ▼
registration services → shared model rules → atomic transactions / row locks
       ▼
PostgreSQL

Django admin → locked change forms → the same model rules → PostgreSQL
```

### Relevant structure

```text
CodeAlpha_EventRegistration/
├── .gitignore
├── README.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt / requirements.lock / requirements-dev.txt
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py             # Environment, DB, security, DRF, throttles
│   │   ├── api.py                  # Safe exceptions, opt-in pagination, no-store
│   │   ├── urls.py
│   │   ├── test_settings.py         # Test-only fast password hasher
│   │   ├── test_configuration.py
│   │   └── asgi.py / wsgi.py
│   ├── events/
│   │   ├── models.py / serializers.py / views.py / urls.py / admin.py
│   │   ├── tests.py / test_features.py
│   │   └── migrations/0001_initial.py
│   ├── registrations/
│   │   ├── models.py / serializers.py / views.py / urls.py / admin.py
│   │   ├── auth_views.py / services.py / throttles.py
│   │   ├── tests.py / test_admin.py / test_security.py / test_concurrency.py
│   │   └── migrations/0001_initial.py
│   └── tests/                      # Original reserved directory
├── frontend/
│   ├── .env.example
│   ├── index.html
│   ├── package.json / package-lock.json / vite.config.js
│   ├── src/
│   │   ├── main.jsx / App.jsx
│   │   ├── api.js / auth.jsx
│   │   ├── pages.jsx / components.jsx / styles.css
│   └── test/api.test.js
└── scripts/
    ├── test_postgres.py            # Disposable, independent PostgreSQL cluster
    ├── test_server.py              # In-memory browser fixture server only
    └── browser.test.js             # Real browser + real HTTP integration
```

Virtual environments, actual `.env` files, dependencies, build output, collected static assets, and `.test-artifacts/` are ignored by Git. Test fixture data is never loaded into the normal database.

## Backend setup

Run from the repository root. An existing `.venv` and `.env` can be reused; preserve existing credentials and data.

```sh
cd backend
python3 -m venv .venv                  # Only if a virtual environment does not exist
source .venv/bin/activate
python -m pip install -r requirements.lock
cp -n .env.example .env                # Does not overwrite an existing .env
chmod 600 .env
```

Set a private signing secret in `.env`. Generate one locally:

```sh
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Keep the generated value private. The configured local environment may already contain a generated key. The application refuses to start with an absent, short, or known-placeholder secret.

### PostgreSQL

Set credentials for an existing database in `.env`. For a fresh installation only, provision a dedicated database and role using your database administrator's normal process. Example SQL placeholders:

```sql
CREATE USER event_app WITH PASSWORD '<private-password>';
CREATE DATABASE event_registration OWNER event_app;
```

Do not reset an existing database. Do not grant database-creation privileges just to run tests: the disposable PostgreSQL runner below avoids the configured server entirely.

For a new database, apply the original migrations and create an administrator:

```sh
python manage.py migrate
python manage.py createsuperuser
```

No new application migration was required for the finalization changes. Existing local PostgreSQL records were not modified during implementation.

Start the backend:

```sh
python manage.py runserver 127.0.0.1:8000
```

Django admin: **http://127.0.0.1:8000/admin/**. The backend root is not the React frontend.

## Frontend setup

In another terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` to `http://127.0.0.1:8000` by default.

Optional frontend `.env`:

```env
VITE_API_BASE_URL=/api/
API_PROXY_TARGET=http://127.0.0.1:8000
```

`VITE_API_BASE_URL` is public browser configuration. `API_PROXY_TARGET` is server-side Vite proxy configuration. Never put signing keys, database credentials, or tokens in frontend environment variables.

```sh
npm run build
npm run preview
```

Preview also proxies `/api`; its printed URL is usually port 4173. It is a local preview server, not a production hosting service.

## Environment settings

Backend values are read from `backend/.env`, with process environment variables taking precedence.

| Variable                                            | Purpose                                                                                                                |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `DJANGO_ENV`                                        | `development`, `test`, or `production`.                                                                                |
| `DJANGO_DEBUG`                                      | Explicit Boolean; `True` only for local development.                                                                   |
| `DJANGO_SECRET_KEY`                                 | Required private random value, at least 50 characters.                                                                 |
| `DJANGO_ALLOWED_HOSTS`                              | Comma-separated hostnames/IP addresses, without URL schemes or ports. Production rejects `*` and debug mode.           |
| `TIME_ZONE`                                         | Django timezone, default UTC; browser dates are localized.                                                             |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Persistent database credentials.                                                                                       |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | PostgreSQL connection address.                                                                                         |
| `POSTGRES_CONN_MAX_AGE`                             | Connection lifetime in seconds, default 60.                                                                            |
| `POSTGRES_TEST_DB`                                  | Isolated Django test database name, default `test_event_registration`; never use the live database name.               |
| `DJANGO_TEST_SQLITE`                                | Explicit in-memory local logic-test mode; rejected in production.                                                      |
| `CORS_ALLOWED_ORIGINS`                              | Exact HTTP(S) browser origins; defaults to `http://localhost:5173`. No wildcard.                                       |
| `CSRF_TRUSTED_ORIGINS`                              | Optional exact origins for trusted cookie-authenticated requests. Empty by default.                                    |
| `SECURE_SSL_REDIRECT`                               | Defaults on when debug is off; required in production.                                                                 |
| `SECURE_HSTS_SECONDS`                               | Defaults to one year outside debug; configure only after HTTPS is working.                                             |
| `TRUST_PROXY_SSL_HEADER`                            | Default false. Enable only behind a proxy that strips spoofed incoming forwarding headers and sets the correct scheme. |
| `LOGIN_THROTTLE_RATE`                               | Per-IP login allowance, default `10/min`.                                                                              |
| `SIGNUP_THROTTLE_RATE`                              | Per-IP signup allowance, default `20/hour`.                                                                            |
| `REGISTRATION_THROTTLE_RATE`                        | Per-user registration-attempt allowance, default `30/min`.                                                             |

## Database design and consistency

`Event` stores title, description, location, start/end times, capacity, and timestamps. `Registration` connects one user to one event and stores registered/cancelled status and timestamps.

```text
Django User 1 ─── many Registration many ─── 1 Event
```

Existing constraints guarantee positive event capacity, end time after start time, and a unique `(user, event)` pair. Cancellation updates status rather than deleting the row; reactivation reuses it. Deleting an event/user through Django cascades to related registrations.

Shared model rules protect ordinary `save()` and `objects.create()` calls. Transactions consistently acquire the event lock before the registration lock. Admin locks remain held through form validation and saving. Existing registrations cannot be moved to another user or event. Capacity reductions are checked under the event lock.

**Scope boundary:** bulk `QuerySet.update()`, `bulk_create()`, raw SQL, and external database tools bypass model saves. They are not supported capacity-changing application write paths. Do not use them for attendance mutations. Database uniqueness still applies, but enforcing a cross-table capacity count against arbitrary external SQL would require additional database-level machinery outside this project's scope.

## API documentation

Requests and responses support JSON. Existing token authentication uses:

```http
Authorization: Token <token>
```

| Method | Endpoint                          | Permission                   | Behavior                                                        |
| ------ | --------------------------------- | ---------------------------- | --------------------------------------------------------------- |
| POST   | `/api/auth/register/`             | Public; IP throttle          | Create account; return user summary and token, 201.             |
| POST   | `/api/auth/login/`                | Public; IP throttle          | Return user summary and token, 200.                             |
| POST   | `/api/auth/logout/`               | Authenticated                | Delete the account token, 200.                                  |
| GET    | `/api/events/`                    | Public                       | Event directory with filters and optional pagination.           |
| GET    | `/api/events/{id}/`               | Public                       | Event information, capacity, and caller's registration status.  |
| GET    | `/api/registrations/`             | Authenticated                | Only the caller's records, with optional status and pagination. |
| POST   | `/api/registrations/`             | Authenticated; user throttle | Create, 201, or reactivate, 200.                                |
| GET    | `/api/registrations/{id}/`        | Authenticated owner          | One personal record.                                            |
| POST   | `/api/registrations/{id}/cancel/` | Authenticated owner          | Cancel; repeat calls remain 200.                                |

Other users' registration IDs return 404. Users cannot supply another owner or write registration status through API input. Event CRUD remains in Django admin. Unsupported edit/delete methods return 405. Paths require the documented trailing slash.

### Signup/login

```http
POST /api/auth/register/
Content-Type: application/json

{"username":"sam","email":"sam@example.com","password":"<strong-private-password>"}
```

Email is optional. Passwords run through all configured Django validators and are never returned. Login accepts username/password. Both endpoints return this shape:

```json
{
  "user": { "id": 1, "username": "sam", "email": "sam@example.com" },
  "token": "<private-token>"
}
```

Invalid credentials preserve the original 400 response. Missing/invalid tokens on protected endpoints return 401.

### Event directory

```http
GET /api/events/?search=workshop&when=upcoming&available=true&page=1&page_size=9
```

- `search`: case-insensitive title or location.
- `when=upcoming`: start time is in the future.
- `when=past`: start time has passed, including currently running events.
- `available=true|false`: remaining capacity above zero / no remaining capacity. Combine with `when=upcoming` to find bookable events.
- `page` or `page_size`: enable pagination; default page size 12, maximum 100.

Without page parameters, list endpoints preserve their original JSON arrays. With pagination:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Workshop",
      "description": "Learn together",
      "location": "Campus",
      "start_time": "2026-12-10T08:00:00Z",
      "end_time": "2026-12-10T10:00:00Z",
      "capacity": 20,
      "available_capacity": 19,
      "created_at": "2026-11-12T08:00:00Z",
      "updated_at": "2026-11-12T08:00:00Z",
      "registration_status": null
    }
  ]
}
```

Values above are illustrative. `registration_status` is additive: null for anonymous/unregistered callers, or the authenticated caller's `registered`/`cancelled` status. Other attendees' identities are never included.

### Registration and cancellation

```http
POST /api/registrations/
Authorization: Token <private-token>
Content-Type: application/json

{"event_id":1}
```

Response: `id`, nested `event`, `status`, `registered_at`, `updated_at`. New rows return 201; reactivation returns 200. Full, started, or duplicate active registration requests return 409.

```http
GET /api/registrations/?status=registered&page=1
Authorization: Token <private-token>
```

`status` accepts `registered` or `cancelled`. Cancelling uses `POST /api/registrations/{id}/cancel/`. The first response contains the updated object; an already-cancelled record retains the original `{"detail":"Registration is already cancelled."}` response for compatibility.

### Errors

400: invalid/missing input or filters. 401: unauthenticated/invalid token. 404: missing resource or another user's registration. 405: unsupported method. 409: registration conflict. 429: throttle exceeded, with `Retry-After`. 500: unexpected failure with a safe generic message.

```json
{ "detail": "The event is full." }
```

Field validation uses DRF's usual field-to-message-list structure. Unexpected database details and stack traces are excluded from API responses, including during local development. Error logs record the exception class and view, not credentials, request bodies, tokens, or raw database error text.

## Authentication and security tradeoffs

The existing DRF token contract is preserved. Repeated logins return the same account token. Logout revokes that shared token for every client using it. Tokens do not automatically expire; no JWT framework was added.

The React client keeps the token only in memory. It never writes it to localStorage, sessionStorage, cookies, URLs, or logs. Reloading closes the interface session, although the server token remains valid until revoked. The API client pins requests to the configured API origin/path, omits browser cookies, refuses unrelated URLs, and rejects HTTP redirects. A 401 from the current token clears frontend authentication. Network failure during logout leaves the session available to retry revocation.

Memory storage reduces persistence risk but does not make tokens immune to XSS while a tab is open. Use HTTPS in deployment. Django admin separately uses session cookies and CSRF protection. The browser API remains Token-authenticated, so no silent cookie/session API migration or CSRF exemption of the admin was introduced.

DRF cache-based throttles are approximate, not a strict security boundary. The default process-local cache resets on restart and is not shared across workers. Before multi-worker public hosting, configure a shared Django cache and infrastructure-level rate limiting. Do not blindly trust `X-Forwarded-For`; configure the trusted proxy chain deliberately.

Nonblank email uniqueness remains an application check, not a database constraint; username remains the unique login identifier. A multi-account/email verification policy is outside current scope.

## User and administrator workflows

Attendee: browse → sign up/sign in → reserve on an event page → view My registrations → confirm cancellation or register again → log out. Full and started events show clear feedback; server rules remain authoritative even if displayed capacity is stale.

Administrator: sign into `/admin/` using an existing staff account with appropriate permissions. Create/edit events, search/filter records, manage status, and delete records using Django's confirmation screens. New/changed active registrations must fit capacity and precede event start. Cancellation remains possible after start. User/event identity is read-only on an existing registration; cancel it and create the correct record instead of reassigning it.

No test users or fixtures are added to the persistent database. An empty database displays useful empty states until an administrator creates events.

## Tests and verification

From the repository root:

```sh
# Logic suite, in-memory DB; PostgreSQL-only cases explicitly skip
cd backend
DJANGO_TEST_SQLITE=True .venv/bin/python -B manage.py test --settings=config.test_settings

# Regular checks and migration consistency; no migration files are written
DJANGO_TEST_SQLITE=True .venv/bin/python -B manage.py check
DJANGO_TEST_SQLITE=True .venv/bin/python -B manage.py makemigrations --check --dry-run
cd ..

# Full suite on a disposable PostgreSQL cluster, including concurrent writes
backend/.venv/bin/python -B scripts/test_postgres.py

# Frontend unit tests and production bundle
npm test --prefix frontend
npm run build --prefix frontend

# Actual Vite → Django requests and real Firefox user journey
npm run test:browser --prefix frontend
```

The PostgreSQL helper needs installed `initdb` and `pg_ctl` binaries and must run as a non-root user. It discovers binaries under `/usr/lib/postgresql/*/bin` or PATH. It creates only its own ignored temporary directory, starts an independent loopback-only cluster, overrides all DB connection settings for its child test process, and removes that cluster afterward. The configured local database and its role are untouched. Do not run it as root or change database privileges to force it to work.

Browser checks require an existing Firefox and geckodriver on PATH (`GECKODRIVER_PATH` may override the executable). They never install a browser. They start an in-memory Django fixture server and Vite, exercise forms/navigation/actions, and stop owned processes. Browser fixtures are disposable. Screenshots are saved under ignored `.test-artifacts/`.

The test-only MD5 password hasher speeds fixtures; password-strength validators remain enabled. It is never used by the normal application settings.

To audit pinned runtime dependencies using project-local developer tools:

```sh
cd backend
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip_audit -r requirements.lock --no-deps --disable-pip
cd ..
npm audit --prefix frontend
```

The pinned runtime file is separate from audit-tool dependencies. Security results are a snapshot, not a guarantee against future advisories.

## Recorded verification — 12 November 2026

| Check | Final result |
| --- | --- |
| Full backend suite on disposable PostgreSQL 16 | 50 passed; includes 6 concurrency tests |
| In-memory SQLite suite | 44 passed, 6 PostgreSQL-only tests explicitly skipped |
| Frontend API-client tests | 5 passed |
| Firefox / actual React-to-Django journey | 8 subtests passed; Node reports 9 including the parent test |
| Frontend production build | Passed on Node.js 20.20.2 |
| Django system checks | No issues |
| Production-like `check --deploy` with normal settings | No issues |
| Migration dry run | No changes detected; original migrations unchanged |
| Pinned backend runtime advisory audit | No known vulnerabilities in 9 pinned packages |
| Frontend dependency audit | 0 reported vulnerabilities after router patch |
| Existing PostgreSQL data preservation | Before/after fingerprints match for application, user, token, session, and migration tables |
| Submission secret/generated-file scan | No actual secrets or generated artifacts found |

All final test runs succeeded. Earlier test-harness failures were corrected and rerun. SQLite results are not used as evidence of PostgreSQL locking. Dependency audits are snapshots of the checked versions. These results do not establish real public HTTPS, hosting, shared-cache infrastructure, load capacity, or a comprehensive accessibility audit. No deployment, commit, or push was performed.

## Deployment guidance — no deployment is performed

Set production variables explicitly, including `DJANGO_ENV=production`, `DJANGO_DEBUG=False`, a private signing secret, real `DJANGO_ALLOWED_HOSTS`, and HTTPS. Production settings reject known signing-key fallbacks, wildcard hosts, SQLite test mode, and disabled HTTPS redirection.

Example configuration check (uses your private existing environment secret):

```sh
cd backend
DJANGO_ENV=production DJANGO_DEBUG=False \
DJANGO_ALLOWED_HOSTS=events.example.org SECURE_SSL_REDIRECT=True \
DJANGO_TEST_SQLITE=False .venv/bin/python -B manage.py check --deploy
```

Before actual hosting:

1. Use a supported production WSGI/ASGI server, not Django `runserver` or Vite preview. Select/configure it for the hosting environment.
2. Build React and serve `frontend/dist` as static files with SPA fallback to `index.html`.
3. Forward `/api/` and `/admin/` to Django; serve the frontend and backend through HTTPS, preferably on one origin.
4. Run `collectstatic` for a new deployment and serve `backend/staticfiles` at `/static/`. `STATIC_ROOT` is configured for Django admin assets.
5. Configure trusted forwarding headers only at a proxy that strips client-supplied copies. Test for HTTPS redirect loops before enabling HSTS for the real domain.
6. Use a dedicated least-privilege PostgreSQL role, backups, a shared cache for workers, external request limits, monitoring, and protected logs.
7. Run checks and tests on that environment. A successful local production-settings check is not verification of real TLS, proxy, static hosting, backups, or operational capacity.

No database triggers were added; raw SQL/bulk writes can bypass application capacity checks. Lists remain optionally unpaginated for legacy compatibility. No email delivery, payment processing, waitlists, independent registration deadline, or per-device token sessions are included.

## Submission

Review `git diff` and `git status`, rerun verification, and capture screenshots without credentials. Confirm `.env`, database dumps, virtual environments, node_modules, build output, and test-cluster files are not staged. Commit and push only when you choose; nothing in this project automatically publishes or deploys it.

Developed for the CodeAlpha Backend Development Internship, Task 2: Event Registration System.
