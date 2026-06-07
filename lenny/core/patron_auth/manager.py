"""Central auth-mode switcher for patron authentication paths.

AuthModeManager is stateless — every method reads config fresh to stay
consistent across workers (same pattern as OAuthConfig.from_auth_env() and
configs.read_lending_mode()).
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from fastapi import HTTPException

from lenny import configs
from lenny.core.external_auth import OAuthConfig

_AUTH_ENV_PATH = "/app/auth.env"


class AuthModeManager:
    """Single source of truth for which patron auth paths are active.

    Replaces the duplicated _require_lending() and _external_auth_ready()
    helpers that previously lived independently in routes/oauth.py and routes/api.py.
    """

    def get_lending_mode(self) -> str:
        """Return current lending mode, read fresh from /app/ol.env."""
        return configs.read_lending_mode()

    def is_ol_ready(self) -> bool:
        """True when OL/OTP mode is active AND both S3 keys are present."""
        if self.get_lending_mode() != "ol":
            return False
        return bool(configs.OL_S3_ACCESS_KEY and configs.OL_S3_SECRET_KEY)

    def is_external_ready(self) -> bool:
        """True when OIDC external auth is enabled AND fully configured."""
        cfg = OAuthConfig.from_auth_env(_AUTH_ENV_PATH)
        return cfg.enabled and cfg.is_configured()

    def is_ia_s3_enabled(self) -> bool:
        """True when IA_AUTH_ENABLED flag is set."""
        return bool(configs.IA_AUTH_ENABLED)

    def get_oidc_config(self) -> OAuthConfig:
        """Return a fresh OAuthConfig from auth.env."""
        return OAuthConfig.from_auth_env(_AUTH_ENV_PATH)

    def patron_auth_mode(self) -> str:
        """Return the active patron auth mode: 'external' | 'ol' | 'none'.

        Priority: external > ol > none.
        """
        if self.is_external_ready():
            return "external"
        if self.is_ol_ready():
            return "ol"
        return "none"

    def require_patron_login_available(self) -> None:
        """Raise HTTPException(503) if no patron auth path is available."""
        if self.patron_auth_mode() == "none":
            raise HTTPException(
                status_code=503,
                detail={"error": "lending_not_configured",
                        "message": "Lending is not configured on this instance."},
            )

    def get_patron_auth_redirect(
        self,
        opds_redirect_uri: Optional[str] = None,
        opds_state: Optional[str] = None,
        redirect_to: Optional[str] = None,
    ) -> Optional[str]:
        """Return URL for patron login redirect, or None for OTP form."""
        if not self.is_external_ready():
            return None

        params: dict[str, str] = {}
        if opds_redirect_uri:
            params["opds_redirect_uri"] = opds_redirect_uri
        if opds_state:
            params["opds_state"] = opds_state
        if redirect_to:
            params["redirect_to"] = redirect_to

        base = "/v1/api/oauth/external/start"
        return f"{base}?{urlencode(params)}" if params else base
