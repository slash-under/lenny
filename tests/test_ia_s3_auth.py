"""Tests for IA S3 patron credential validation and the /oauth/ia-s3 route."""
import os
os.environ["TESTING"] = "true"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

pytestmark = pytest.mark.anyio(backends=["asyncio"])

from lenny.core.patron_auth.ia_s3 import validate_patron_ia_s3
from lenny.core.exceptions import InvalidOLCredentialsError


# ── validate_patron_ia_s3 unit tests ─────────────────────────────────────────

@pytest.mark.anyio
async def test_validate_patron_ia_s3_returns_email_on_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "authorized": 1,
        "access": "TESTACC",
        "email": "patron@example.com",
    }
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await validate_patron_ia_s3("TESTACC", "TESTSEC")

    assert result == "patron@example.com"


@pytest.mark.anyio
async def test_validate_patron_ia_s3_strips_and_lowercases_email():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 1, "email": "  PATRON@EXAMPLE.COM  "}
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await validate_patron_ia_s3("A", "B")

    assert result == "patron@example.com"


@pytest.mark.anyio
async def test_validate_patron_ia_s3_uses_username_fallback_when_no_email():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 1, "username": "patron@example.com"}
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await validate_patron_ia_s3("A", "B")

    assert result == "patron@example.com"


@pytest.mark.anyio
async def test_validate_patron_ia_s3_raises_on_authorized_zero():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 0}
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        with pytest.raises(InvalidOLCredentialsError):
            await validate_patron_ia_s3("BAD", "CREDS")


@pytest.mark.anyio
async def test_validate_patron_ia_s3_raises_on_non_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        with pytest.raises(InvalidOLCredentialsError):
            await validate_patron_ia_s3("A", "B")


@pytest.mark.anyio
async def test_validate_patron_ia_s3_raises_on_http_error():
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_cls.return_value = mock_http

        with pytest.raises(InvalidOLCredentialsError):
            await validate_patron_ia_s3("A", "B")


@pytest.mark.anyio
async def test_validate_patron_ia_s3_raises_when_no_email_or_username():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 1}  # No email, no username
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        with pytest.raises(InvalidOLCredentialsError, match="missing email"):
            await validate_patron_ia_s3("A", "B")


@pytest.mark.anyio
async def test_validate_patron_ia_s3_raises_on_non_json_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("not json")
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        with pytest.raises(InvalidOLCredentialsError):
            await validate_patron_ia_s3("A", "B")


@pytest.mark.anyio
async def test_validate_patron_ia_s3_sends_low_auth_header():
    """Verify the outbound request uses Authorization: LOW <access>:<secret>."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 1, "email": "p@ia.org"}
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        await validate_patron_ia_s3("MYACC", "MYSEC")

    call_kwargs = mock_http.get.call_args
    sent_headers = call_kwargs.kwargs.get("headers", {}) or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
    assert sent_headers.get("Authorization") == "LOW MYACC:MYSEC"


# ── Route tests: POST /oauth/ia-s3 ───────────────────────────────────────────
from fastapi.testclient import TestClient


@pytest.fixture
def ia_s3_client():
    """TestClient with DB init mocked so no PostgreSQL needed."""
    with patch("lenny.core.models.Base.metadata.create_all"):
        from lenny.app import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_ia_s3_route_returns_404_when_disabled(ia_s3_client):
    """Route returns 404 when IA_AUTH_ENABLED=False (default)."""
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = False
    try:
        resp = ia_s3_client.post(
            "/v1/api/oauth/ia-s3",
            headers={"Authorization": "LOW ACC:SEC"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "ia_auth_disabled"
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_returns_401_when_header_missing(ia_s3_client):
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        resp = ia_s3_client.post("/v1/api/oauth/ia-s3")
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "missing_auth_header"
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_returns_401_when_header_wrong_scheme(ia_s3_client):
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        resp = ia_s3_client.post(
            "/v1/api/oauth/ia-s3",
            headers={"Authorization": "Bearer sometoken"},
        )
        assert resp.status_code == 401
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_returns_400_when_no_colon_in_creds(ia_s3_client):
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        resp = ia_s3_client.post(
            "/v1/api/oauth/ia-s3",
            headers={"Authorization": "LOW nocredshere"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "malformed_auth_header"
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_sets_session_cookie_on_success(ia_s3_client):
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        with patch(
            "lenny.routes.oauth.validate_patron_ia_s3",
            return_value="patron@example.com",
        ):
            resp = ia_s3_client.post(
                "/v1/api/oauth/ia-s3",
                headers={"Authorization": "LOW GOODACC:GOODSEC"},
            )
        assert resp.status_code == 200
        assert "session" in resp.cookies
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_returns_401_on_invalid_creds(ia_s3_client):
    from lenny import configs
    from lenny.core.exceptions import InvalidOLCredentialsError
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        with patch(
            "lenny.routes.oauth.validate_patron_ia_s3",
            side_effect=InvalidOLCredentialsError("bad credentials"),
        ):
            resp = ia_s3_client.post(
                "/v1/api/oauth/ia-s3",
                headers={"Authorization": "LOW BADACC:BADSEC"},
            )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "invalid_credentials"
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_returns_503_on_ia_network_failure(ia_s3_client):
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        with patch(
            "lenny.routes.oauth.validate_patron_ia_s3",
            side_effect=RuntimeError("unexpected"),
        ):
            resp = ia_s3_client.post(
                "/v1/api/oauth/ia-s3",
                headers={"Authorization": "LOW ACC:SEC"},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "ia_unavailable"
    finally:
        configs.IA_AUTH_ENABLED = orig


@pytest.mark.anyio
async def test_validate_patron_ia_s3_screenname_fallback():
    """screenname field used when email and username both absent (matches PR #184 behavior)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"authorized": 1, "screenname": "archiveuser"}
    with patch("lenny.core.patron_auth.ia_s3.httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await validate_patron_ia_s3("A", "B")

    assert result == "archiveuser"


def test_ia_s3_route_accepts_lowercase_low_scheme(ia_s3_client):
    """Authorization: low <creds> (lowercase) must be accepted (case-insensitive)."""
    from lenny import configs
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        with patch(
            "lenny.routes.oauth.validate_patron_ia_s3",
            return_value="patron@example.com",
        ):
            resp = ia_s3_client.post(
                "/v1/api/oauth/ia-s3",
                headers={"Authorization": "low ACC:SEC"},
            )
        assert resp.status_code == 200
    finally:
        configs.IA_AUTH_ENABLED = orig


def test_ia_s3_route_session_cookie_is_valid_lenny_session(ia_s3_client):
    """Session cookie issued by /oauth/ia-s3 must be verifiable by auth.verify_session_cookie."""
    from lenny import configs
    from lenny.core import auth
    orig = configs.IA_AUTH_ENABLED
    configs.IA_AUTH_ENABLED = True
    try:
        with patch(
            "lenny.routes.oauth.validate_patron_ia_s3",
            return_value="patron@example.com",
        ):
            resp = ia_s3_client.post(
                "/v1/api/oauth/ia-s3",
                headers={"Authorization": "LOW ACC:SEC"},
            )
        assert resp.status_code == 200
        session_val = resp.cookies.get("session")
        assert session_val is not None
        data = auth.verify_session_cookie(session_val)
        assert isinstance(data, dict)
        assert data.get("email") == "patron@example.com"
    finally:
        configs.IA_AUTH_ENABLED = orig
