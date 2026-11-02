# CodeAlpha Event Registration API

A backend-only REST API for publishing events and managing authenticated user registrations. It uses Django's built-in user model, Django REST Framework token authentication, and PostgreSQL.

## Features

- Public event list and detail endpoints, including remaining capacity.
- Token-based account registration, login, and logout.
- Authenticated registration management with per-user data isolation.
- Cancellation and reactivation of a prior registration without duplicate rows.
- Capacity, event-time, and duplicate-registration checks inside database transactions.
- Admin management for events and registrations.
- Configurable CORS allowlist and environment-based secrets/database credentials.

## Technology

Python, Django, Django REST Framework, PostgreSQL, psycopg 3, django-cors-headers, and python-dotenv.

## Project structure

```text
backend/
├── config/                 # Django project settings and root URLs
├── events/                 # Event model, public API, serializer, admin
├── registrations/          # Auth, registration model, API, serializer, admin
├── tests/                  # Reserved for cross-app tests
├── manage.py
├── .env.example
├── requirements.txt
└── README.md
```

## Local setup

Requires Python 3.10+ and PostgreSQL 13+. Run commands from `backend/`.

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a PostgreSQL database and user (or use an existing local role):

   ```sql
   CREATE USER event_api WITH PASSWORD 'replace-this-password';
   CREATE DATABASE event_registration OWNER event_api;
   ```

3. Copy `.env.example` to `.env`, set a strong random `DJANGO_SECRET_KEY`, and set the PostgreSQL credentials. Keep `.env` private. Set `DJANGO_DEBUG=True` only for local development; use `False` in production and serve over HTTPS.

4. Apply migrations and create an admin user:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. Start the local server:

   ```bash
   python manage.py runserver
   ```

The API is available under `http://127.0.0.1:8000/api/`; the admin is at `/admin/`.

## Environment variables

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django signing secret; supply a unique random value |
| `DJANGO_DEBUG` | Enables debug mode only when explicitly set to `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated Django hostnames |
| `TIME_ZONE` | Django time zone (default `UTC`); timestamps use ISO 8601 |
| `POSTGRES_DB` | PostgreSQL database name |
| `POSTGRES_USER` | PostgreSQL role |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Database host and port |
| `POSTGRES_CONN_MAX_AGE` | Persistent connection lifetime in seconds |
| `CORS_ALLOWED_ORIGINS` | Comma-separated exact browser origins; no wildcard is enabled |
| `SECURE_SSL_REDIRECT` | HTTPS redirect toggle (default enabled when debug is off) |

## API

All request and response bodies are JSON. Authentication uses the `Authorization: Token <token>` header. Public event endpoints do not require a token.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/register/` | Public | Create an account and receive a token |
| `POST` | `/api/auth/login/` | Public | Obtain the account token |
| `POST` | `/api/auth/logout/` | Authenticated | Revoke the current token |
| `GET` | `/api/events/` | Public | List events |
| `GET` | `/api/events/{id}/` | Public | View an event |
| `POST` | `/api/registrations/` | Authenticated | Register or reactivate for an event |
| `GET` | `/api/registrations/` | Authenticated | List only your registrations |
| `GET` | `/api/registrations/{id}/` | Authenticated | View only your registration |
| `POST` | `/api/registrations/{id}/cancel/` | Authenticated | Cancel your registration |

### Account registration

```http
POST /api/auth/register/
Content-Type: application/json

{"username":"sam","email":"sam@example.com","password":"a-strong-password"}
```

Returns `201 Created` with the user summary and token. The password is never returned. Login accepts `username` and `password`; it returns the same shape with `200 OK`. Logout deletes the caller's token.

### Browse events

```http
GET /api/events/
```

```json
[
  {
    "id": 1,
    "title": "Backend Summit",
    "description": "Talks and workshops",
    "location": "Addis Ababa",
    "start_time": "2026-12-10T08:00:00Z",
    "end_time": "2026-12-10T16:00:00Z",
    "capacity": 100,
    "available_capacity": 99,
    "created_at": "2026-11-02T08:00:00Z",
    "updated_at": "2026-11-02T08:00:00Z"
  }
]
```

### Register for an event

```http
POST /api/registrations/
Authorization: Token your-token
Content-Type: application/json

{"event_id":1}
```

A new registration returns `201 Created`; reactivating a cancelled registration returns `200 OK`. Duplicate active requests, full events, and events that have started return `409 Conflict`. Invalid input returns `400 Bad Request`; unauthenticated requests return `401 Unauthorized`.

### View and cancel registrations

```http
GET /api/registrations/
Authorization: Token your-token
```

```http
POST /api/registrations/12/cancel/
Authorization: Token your-token
```

Other users' registration IDs return `404 Not Found`, avoiding disclosure of whether another person's record exists. Cancellation returns the updated registration with `status: "cancelled"`. Cancelled rows do not consume event capacity.

### Error response example

```json
{"detail":"The event is full."}
```

Field validation errors follow DRF's standard JSON format, for example `{"capacity":["Capacity must be greater than zero."]}`.

## Testing and checks

With dependencies installed and the configured PostgreSQL service available:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
```

Tests use Django's configured test database. Concurrency safety relies on PostgreSQL row-level `SELECT FOR UPDATE` locks on the event row; SQLite does not provide equivalent locking behavior.

For an environment without a running PostgreSQL service, the test suite can also be run with `DJANGO_TEST_SQLITE=True python manage.py test`. This switch is intended only for local logic tests; it does not change the normal PostgreSQL configuration and cannot verify concurrent locking.

## CodeAlpha attribution

Developed for the CodeAlpha Backend Development Internship, Task 2: Event Registration System.
