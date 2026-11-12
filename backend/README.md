# CodeAlpha Event Registration backend

The backend uses Django REST Framework, PostgreSQL, token authentication, and Django admin. The React frontend is at `../frontend`.

See the **[complete project README](../README.md)** for installation, environment configuration, API documentation, database rules, frontend setup, security, testing, and deployment guidance.

From this directory, with the existing virtual environment and private `.env` configured:

```sh
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Safe in-memory tests:

```sh
DJANGO_TEST_SQLITE=True .venv/bin/python -B manage.py test --settings=config.test_settings
```

The original migrations are preserved. Do not reset an existing database. Never use test settings to run the normal application.
