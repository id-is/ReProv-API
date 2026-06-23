"""Keycloak-based authentication.

Validates OAuth2/OpenID Connect bearer tokens against the configured Keycloak
realm and maps the token claims onto a :class:`~models.user.User`.
"""
import os
from fastapi.security import OAuth2AuthorizationCodeBearer
from models.user import User
from keycloak import KeycloakOpenID
from fastapi import Security, HTTPException, status, Depends


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=os.environ['KEYCLOAK_AUTHORIZATION_URL'],
    tokenUrl=os.environ['KEYCLOAK_TOKEN_URL']
)

keycloak_openid = KeycloakOpenID(
    server_url=os.environ['KEYCLOAK_SERVER_URL'],
    client_id=os.environ['KEYCLOAK_CLIENT_ID'],
    realm_name=os.environ['KEYCLOAK_REALM'],
    client_secret_key=os.environ['KEYCLOAK_CLIENT_SECRET'],
)


async def get_idp_public_key():
    """Return the realm's RSA public key in PEM format for token verification."""
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{keycloak_openid.public_key()}"
        "\n-----END PUBLIC KEY-----"
    )


async def get_payload(token: str = Security(oauth2_scheme)) -> dict:
    """Decode and verify the bearer token, returning its claims (401 on failure)."""
    try:
        return keycloak_openid.decode_token(
            token,
            key=await get_idp_public_key(),
            options={
                "verify_signature": True,
                "verify_aud": False,
                "exp": True
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user(payload: dict = Depends(get_payload)) -> User:
    """Map verified token claims onto a :class:`User` (400 if claims are missing)."""
    try:
        return User(
            id=payload.get("sub"),
            username=payload.get("preferred_username"),
            email=payload.get("email"),
            group=payload.get("groups")[0],
            first_name=payload.get("given_name"),
            last_name=payload.get("family_name"),
            realm_roles=payload.get("realm_access", {}).get("roles", []),
            client_roles=payload.get("resource_access", {}).get(
                os.environ['KEYCLOAK_CLIENT_ID'], {}
            ).get("roles", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*required_roles):
    """Build a dependency that allows the request only if the authenticated user
    holds at least one of ``required_roles`` (in their realm or client roles).

    Returns the authenticated :class:`User` on success, or raises ``403``.
    """
    async def checker(user: User = Depends(authenticate_user)) -> User:
        user_roles = set(user.realm_roles or []) | set(user.client_roles or [])
        if user_roles.isdisjoint(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role; requires one of: "
                       + ", ".join(required_roles),
            )
        return user
    return checker


# Standard operations require the user role (admins also satisfy this);
# destructive operations require the admin role.
require_user = require_roles("reprov_user", "reprov_admin")
require_admin = require_roles("reprov_admin")
