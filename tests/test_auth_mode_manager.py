"""Tests for AuthModeManager — central auth-mode switcher."""
import os
os.environ["TESTING"] = "true"

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from lenny.core.patron_auth.manager import AuthModeManager
from lenny import configs as lenny_configs


@pytest.fixture
def mgr():
    return AuthModeManager()


# ── get_lending_mode ──────────────────────────────────────────────────────────

def test_get_lending_mode_returns_fresh_value(mgr):
    """Reads lending mode fresh (not from stale global)."""
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="ol"):
        assert mgr.get_lending_mode() == "ol"


# ── is_ol_ready ───────────────────────────────────────────────────────────────

def test_is_ol_ready_true_when_mode_ol_and_keys_present(mgr):
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="ol"), \
         patch.object(lenny_configs, "OL_S3_ACCESS_KEY", "ACC"), \
         patch.object(lenny_configs, "OL_S3_SECRET_KEY", "SEC"):
        assert mgr.is_ol_ready() is True


def test_is_ol_ready_false_when_mode_not_ol(mgr):
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="none"):
        assert mgr.is_ol_ready() is False


def test_is_ol_ready_false_when_keys_missing(mgr):
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="ol"), \
         patch.object(lenny_configs, "OL_S3_ACCESS_KEY", None), \
         patch.object(lenny_configs, "OL_S3_SECRET_KEY", None):
        assert mgr.is_ol_ready() is False


def test_is_ol_ready_false_when_only_one_key(mgr):
    """Both keys required — partial config must not pass."""
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="ol"), \
         patch.object(lenny_configs, "OL_S3_ACCESS_KEY", "ACC"), \
         patch.object(lenny_configs, "OL_S3_SECRET_KEY", None):
        assert mgr.is_ol_ready() is False


# ── is_external_ready ─────────────────────────────────────────────────────────

def _mock_oidc_cfg(enabled=True, configured=True):
    cfg = MagicMock()
    cfg.enabled = enabled
    cfg.is_configured.return_value = configured
    return cfg


def test_is_external_ready_true_when_enabled_and_configured(mgr):
    with patch("lenny.core.patron_auth.manager.OAuthConfig.from_auth_env",
               return_value=_mock_oidc_cfg(enabled=True, configured=True)):
        assert mgr.is_external_ready() is True


def test_is_external_ready_false_when_disabled(mgr):
    with patch("lenny.core.patron_auth.manager.OAuthConfig.from_auth_env",
               return_value=_mock_oidc_cfg(enabled=False, configured=True)):
        assert mgr.is_external_ready() is False


def test_is_external_ready_false_when_enabled_but_not_configured(mgr):
    """Enabled flag true but missing client_id/discovery_url/redirect_uri."""
    with patch("lenny.core.patron_auth.manager.OAuthConfig.from_auth_env",
               return_value=_mock_oidc_cfg(enabled=True, configured=False)):
        assert mgr.is_external_ready() is False


# ── is_ia_s3_enabled ──────────────────────────────────────────────────────────

def test_is_ia_s3_enabled_reads_config_flag(mgr):
    with patch.object(lenny_configs, "IA_AUTH_ENABLED", True):
        assert mgr.is_ia_s3_enabled() is True


def test_is_ia_s3_disabled_by_default(mgr):
    with patch.object(lenny_configs, "IA_AUTH_ENABLED", False):
        assert mgr.is_ia_s3_enabled() is False


# ── patron_auth_mode ──────────────────────────────────────────────────────────

def test_patron_auth_mode_returns_external_when_external_ready(mgr):
    with patch.object(mgr, "is_external_ready", return_value=True):
        assert mgr.patron_auth_mode() == "external"


def test_patron_auth_mode_returns_ol_when_ol_ready_and_external_not(mgr):
    with patch.object(mgr, "is_external_ready", return_value=False), \
         patch.object(mgr, "is_ol_ready", return_value=True):
        assert mgr.patron_auth_mode() == "ol"


def test_patron_auth_mode_returns_none_when_nothing_ready(mgr):
    with patch.object(mgr, "is_external_ready", return_value=False), \
         patch.object(mgr, "is_ol_ready", return_value=False):
        assert mgr.patron_auth_mode() == "none"


# ── require_patron_login_available ────────────────────────────────────────────

def test_require_patron_login_raises_503_when_mode_none(mgr):
    with patch.object(mgr, "patron_auth_mode", return_value="none"):
        with pytest.raises(HTTPException) as exc_info:
            mgr.require_patron_login_available()
        assert exc_info.value.status_code == 503


def test_require_patron_login_passes_when_ol_ready(mgr):
    with patch.object(mgr, "patron_auth_mode", return_value="ol"):
        mgr.require_patron_login_available()  # Should not raise


def test_require_patron_login_passes_when_external_ready(mgr):
    with patch.object(mgr, "patron_auth_mode", return_value="external"):
        mgr.require_patron_login_available()  # Should not raise


# ── get_patron_auth_redirect ──────────────────────────────────────────────────

def test_get_patron_auth_redirect_returns_url_when_external(mgr):
    with patch.object(mgr, "is_external_ready", return_value=True):
        url = mgr.get_patron_auth_redirect()
        assert url is not None
        assert "/oauth/external/start" in url


def test_get_patron_auth_redirect_returns_none_when_ol(mgr):
    with patch.object(mgr, "is_external_ready", return_value=False):
        assert mgr.get_patron_auth_redirect() is None


def test_get_patron_auth_redirect_passes_opds_params(mgr):
    with patch.object(mgr, "is_external_ready", return_value=True):
        url = mgr.get_patron_auth_redirect(
            opds_redirect_uri="opds://reader/shelf",
            opds_state="abc123",
        )
        assert "opds_redirect_uri=" in url
        assert "opds_state=" in url


# ── edge cases ────────────────────────────────────────────────────────────────

def test_is_ol_ready_mode_external_returns_false(mgr):
    """Mode=external means OTP is NOT the active patron auth path."""
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="external"):
        assert mgr.is_ol_ready() is False


def test_ia_s3_enabled_independent_of_lending_mode(mgr):
    """IA S3 can be enabled even when LENDING_MODE=none."""
    with patch("lenny.core.patron_auth.manager.configs.read_lending_mode", return_value="none"), \
         patch.object(lenny_configs, "IA_AUTH_ENABLED", True):
        assert mgr.is_ia_s3_enabled() is True
        assert mgr.is_ol_ready() is False
