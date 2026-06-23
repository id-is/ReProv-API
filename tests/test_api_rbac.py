"""Integration tests: RBAC enforced through the real FastAPI request pipeline.

A FastAPI app is built from the real workflow-registry router. Authentication is
overridden to return a chosen user, and the module-level DB session is replaced
with a stub so no MySQL connection is needed. This lets us assert that the role
gate runs *before* the handler logic:

  - a non-admin DELETE is rejected with 403 (never reaches the DB),
  - an admin DELETE passes the gate and reaches the handler (which then reports
    "Invalid registry_id" because the stub returns no row),
  - a standard GET is allowed for a normal user.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import crud.workflow_registry as wr
from authentication.auth import authenticate_user
from models.user import User


def _client(monkeypatch, realm_roles):
    app = FastAPI()
    app.include_router(wr.router, prefix="/workflow_registry")

    user = User(id="1", username="u", email="e", group="g",
                first_name="f", last_name="l",
                realm_roles=realm_roles, client_roles=[])
    app.dependency_overrides[authenticate_user] = lambda: user

    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    monkeypatch.setattr(wr, "session", session)

    return TestClient(app)


def test_delete_forbidden_for_non_admin(monkeypatch):
    client = _client(monkeypatch, ["reprov_user"])
    assert client.delete("/workflow_registry/delete/1").status_code == 403


def test_delete_passes_rbac_for_admin(monkeypatch):
    client = _client(monkeypatch, ["reprov_admin"])
    resp = client.delete("/workflow_registry/delete/1")
    # Past the role gate; handler runs and reports the missing row (HTTP 200 envelope)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == 404


def test_list_allowed_for_standard_user(monkeypatch):
    client = _client(monkeypatch, ["reprov_user"])
    resp = client.get("/workflow_registry/")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
