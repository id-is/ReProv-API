"""Test configuration: make ``src`` importable and set dummy env vars.

The application modules read configuration from environment variables at import
time, so these must be present before any ``src`` module is imported. None of
them point at real services — the tests never open a DB/Keycloak/REANA
connection (sessions and engines are created lazily and stubbed where needed).
"""
import os
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_DUMMY_ENV = {
    "KEYCLOAK_AUTHORIZATION_URL": "http://keycloak/auth",
    "KEYCLOAK_TOKEN_URL": "http://keycloak/token",
    "KEYCLOAK_SERVER_URL": "http://keycloak/",
    "KEYCLOAK_REALM": "prov",
    "KEYCLOAK_CLIENT_ID": "api",
    "KEYCLOAK_CLIENT_SECRET": "",
    "MYSQL_USER": "user",
    "MYSQL_PASSWORD": "password",
    "MYSQL_SERVER": "db",
    "MYSQL_DATABASE": "prov_db",
    "REANA_SERVER_URL": "http://reana",
    "REANA_ACCESS_TOKEN": "dummy",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)
