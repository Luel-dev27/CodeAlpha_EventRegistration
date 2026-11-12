"""Isolated tests: fast password hashing; real password validators stay enabled."""

from .settings import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
