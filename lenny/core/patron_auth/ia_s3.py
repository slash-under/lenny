"""IA S3 patron credential validator.

Validates a patron's Internet Archive S3 access/secret key pair against
the IA S3 auth-check endpoint and returns the patron's email on success.
"""
from __future__ import annotations

import httpx

from lenny.core.exceptions import InvalidOLCredentialsError

_IA_S3_CHECK_URL = "https://s3.us.archive.org/?check_auth=1"


async def validate_patron_ia_s3(access: str, secret: str) -> str:
    """Validate patron IA S3 credentials; return their email.

    Calls the IA S3 auth-check endpoint with ``Authorization: LOW <access>:<secret>``.

    Raises:
        InvalidOLCredentialsError: credentials rejected, network failure, or
            the response is missing an identifiable email/username field.
    """
    headers = {"Authorization": f"LOW {access}:{secret}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_IA_S3_CHECK_URL, headers=headers)
    except httpx.HTTPError as exc:
        raise InvalidOLCredentialsError(
            f"IA S3 auth check failed: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise InvalidOLCredentialsError(
            f"IA rejected S3 credentials (HTTP {resp.status_code})"
        )

    try:
        data = resp.json()
    except Exception as exc:
        raise InvalidOLCredentialsError(
            f"IA S3 auth returned non-JSON response: {exc}"
        ) from exc

    if not data.get("authorized"):
        raise InvalidOLCredentialsError("IA S3 credentials not authorized")

    email = (
        data.get("email") or data.get("username") or data.get("screenname") or ""
    ).strip().lower()
    if not email:
        raise InvalidOLCredentialsError(
            "IA S3 auth response missing email/username/screenname field"
        )

    return email
