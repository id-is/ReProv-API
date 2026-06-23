"""Unit tests for the role-based access dependency in authentication.auth."""
import asyncio

import pytest
from fastapi import HTTPException

from authentication.auth import require_roles
from models.user import User


def _user(realm_roles):
    return User(id="1", username="u", email="e", group="g",
                first_name="f", last_name="l",
                realm_roles=realm_roles, client_roles=[])


def test_require_roles_allows_when_role_present():
    checker = require_roles("reprov_user", "reprov_admin")
    u = _user(["reprov_user"])
    assert asyncio.run(checker(user=u)) is u


def test_require_roles_denies_when_role_missing():
    checker = require_roles("reprov_admin")
    u = _user(["reprov_user"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(user=u))
    assert exc.value.status_code == 403
