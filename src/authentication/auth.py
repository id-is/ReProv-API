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
            client_roles=payload.get("realm_access", {}).get("roles", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
