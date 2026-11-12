import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def flag(name, default=False):
    value = os.getenv(name, str(default)).lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ImproperlyConfigured(f"{name} must be true or false.")
    return value in {"true", "1", "yes"}


def origins(name, default=""):
    values = [
        value.strip() for value in os.getenv(name, default).split(",") if value.strip()
    ]
    for value in values:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ImproperlyConfigured(
                f"{name} must contain exact HTTP(S) origins without paths or credentials."
            )
    return values


ENVIRONMENT = os.getenv("DJANGO_ENV", "development")
if ENVIRONMENT not in {"development", "test", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV must be development, test, or production.")
DEBUG = flag("DJANGO_DEBUG")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(
    ("unsafe-", "replace-", "django-insecure-")
):
    raise ImproperlyConfigured(
        "Set a private DJANGO_SECRET_KEY of at least 50 characters."
    )
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
if any(
    host != "*"
    and not re.fullmatch(r"(?:\.?[A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9A-Fa-f:]+\])", host)
    for host in ALLOWED_HOSTS
):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain hostnames or IP addresses without schemes or ports."
    )
if not ALLOWED_HOSTS or (
    ENVIRONMENT == "production" and ("*" in ALLOWED_HOSTS or DEBUG)
):

    raise ImproperlyConfigured(
        "Production requires explicit allowed hosts and DEBUG=False."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "events",
    "registrations",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.api.NoStoreAPIMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if flag("DJANGO_TEST_SQLITE"):
    if ENVIRONMENT == "production":
        raise ImproperlyConfigured(
            "In-memory SQLite is only supported for local tests."
        )
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "event_registration"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
            "OPTIONS": {"connect_timeout": 5},
            "TEST": {"NAME": os.getenv("POSTGRES_TEST_DB", "test_event_registration")},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "event-registration-throttles",
    }
}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.api.exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("LOGIN_THROTTLE_RATE", "10/min"),
        "signup": os.getenv("SIGNUP_THROTTLE_RATE", "20/hour"),
        "registration": os.getenv("REGISTRATION_THROTTLE_RATE", "30/min"),
    },
}
APPEND_SLASH = False
CORS_ALLOWED_ORIGINS = origins("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CSRF_TRUSTED_ORIGINS = origins("CSRF_TRUSTED_ORIGINS")
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = flag("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(
    os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = "DENY"
# Set only when a trusted proxy strips incoming spoofed forwarding headers.
if flag("TRUST_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if ENVIRONMENT == "production" and not SECURE_SSL_REDIRECT:
    raise ImproperlyConfigured("Production requires HTTPS redirection.")
