"""
Per-user AWS credentials for workspace S3 access.

The AgentCore runtime role has no access to the workspace bucket. Instead,
every S3 operation runs with temporary credentials from a Cognito Identity
Pool, obtained by exchanging the caller's Cognito ID token. The pool maps the
token's `sub` claim to the `sub` principal tag, and the pool's authenticated
role only allows `{prefix}/${aws:PrincipalTag/sub}/*`. So even code running
inside the user's own microVM (the agent, the shell, the terminal) can only
reach that user's prefix.

The ID token arrives in the X-Amzn-Bedrock-AgentCore-Runtime-Custom-Id-Token
header. It is not verified here: Cognito Identity verifies it during the
exchange, and it must carry the same `sub` as the access token that the
AgentCore JWT authorizer already validated.

Set IDENTITY_POOL_ID to enable this. Without it (local development), S3
commands use the ambient AWS credentials as before.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import jwt

logger = logging.getLogger(__name__)

ID_TOKEN_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-id-token"

# Refresh credentials this many seconds before they expire
_REFRESH_MARGIN_SECONDS = 300


class UserCredentialsError(Exception):
    """Raised when per-user S3 credentials cannot be obtained."""


@dataclass
class _UserEntry:
    id_token: Optional[str] = None
    id_token_exp: float = 0.0
    access_key_id: Optional[str] = None
    secret_key: Optional[str] = None
    session_token: Optional[str] = None
    expiration: float = 0.0


_entries: dict[str, _UserEntry] = {}
_locks: dict[str, asyncio.Lock] = {}


def identity_pool_id() -> Optional[str]:
    return os.environ.get("IDENTITY_POOL_ID") or None


def is_enabled() -> bool:
    return identity_pool_id() is not None


def register_id_token(user_id: str, id_token: str) -> None:
    """
    Remember the caller's latest ID token for later credential exchanges.

    Raises UserCredentialsError if the token is not an ID token for user_id.
    """
    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.PyJWTError as e:
        raise UserCredentialsError(f"Malformed ID token: {e}") from e

    if claims.get("token_use") != "id":
        raise UserCredentialsError("Token in the ID token header is not a Cognito ID token")
    if claims.get("sub") != user_id:
        raise UserCredentialsError("ID token does not belong to the authenticated caller")
    if not claims.get("iss"):
        raise UserCredentialsError("ID token has no issuer")

    entry = _entries.setdefault(user_id, _UserEntry())
    entry.id_token = id_token
    entry.id_token_exp = float(claims.get("exp", 0))


def _exchange(id_token: str) -> dict:
    """Exchange a Cognito ID token for Identity Pool credentials (blocking)."""
    import boto3

    claims = jwt.decode(id_token, options={"verify_signature": False})
    # iss is https://cognito-idp.{region}.amazonaws.com/{user_pool_id};
    # the Identity Pool login key is the issuer without the scheme.
    provider = claims["iss"].removeprefix("https://")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    client = boto3.client("cognito-identity", region_name=region)
    logins = {provider: id_token}

    identity = client.get_id(IdentityPoolId=identity_pool_id(), Logins=logins)
    creds = client.get_credentials_for_identity(
        IdentityId=identity["IdentityId"], Logins=logins
    )["Credentials"]
    return creds


async def get_s3_env(user_id: Optional[str]) -> Optional[dict]:
    """
    Return the environment for an S3 subprocess acting as user_id.

    Returns None when per-user credentials are disabled (the subprocess then
    inherits the ambient environment). Raises UserCredentialsError when they
    are enabled but cannot be obtained, so S3 work never silently falls back
    to broader credentials.
    """
    if not is_enabled():
        return None
    if not user_id:
        raise UserCredentialsError("No user identity for S3 access")

    lock = _locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        entry = _entries.get(user_id)
        now = time.time()

        if entry is None or not entry.access_key_id or entry.expiration - now < _REFRESH_MARGIN_SECONDS:
            if entry is None or not entry.id_token:
                raise UserCredentialsError(
                    f"No ID token received for user {user_id}; cannot access S3"
                )
            if entry.id_token_exp and entry.id_token_exp <= now:
                raise UserCredentialsError(
                    f"ID token for user {user_id} has expired; S3 access resumes on the next request"
                )
            try:
                creds = await asyncio.to_thread(_exchange, entry.id_token)
            except Exception as e:
                raise UserCredentialsError(
                    f"Failed to get Identity Pool credentials for user {user_id}: {e}"
                ) from e
            entry.access_key_id = creds["AccessKeyId"]
            entry.secret_key = creds["SecretKey"]
            entry.session_token = creds["SessionToken"]
            entry.expiration = creds["Expiration"].timestamp()
            logger.info(f"Obtained per-user S3 credentials for user {user_id}")

        env = dict(os.environ)
        # Make sure nothing in the environment points s5cmd at the runtime role
        for key in (
            "AWS_PROFILE",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_CONTAINER_AUTHORIZATION_TOKEN",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_ROLE_ARN",
        ):
            env.pop(key, None)
        env["AWS_ACCESS_KEY_ID"] = entry.access_key_id
        env["AWS_SECRET_ACCESS_KEY"] = entry.secret_key
        env["AWS_SESSION_TOKEN"] = entry.session_token
        return env
