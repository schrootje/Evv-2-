import json
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.config import settings

_AUTH_PATH = "/api/oauth2/auth"
_TOKEN_PATH = "/api/oauth2/token"


def get_authorization_url() -> str:
    params = {
        "client_id": settings.exact_client_id,
        "redirect_uri": settings.exact_redirect_uri,
        "response_type": "code",
        "force_login": "0",
    }
    return f"{settings.exact_base_url}{_AUTH_PATH}?{urlencode(params)}"


def _save_tokens(data: dict) -> None:
    data["expires_at"] = time.time() + data.get("expires_in", 600) - 30
    Path(settings.token_file).write_text(json.dumps(data))


def _load_tokens() -> dict | None:
    p = Path(settings.token_file)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def exchange_code(code: str) -> dict:
    with httpx.Client() as client:
        response = client.post(
            f"{settings.exact_base_url}{_TOKEN_PATH}",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.exact_redirect_uri,
                "client_id": settings.exact_client_id,
                "client_secret": settings.exact_client_secret,
            },
        )
        response.raise_for_status()
        tokens = response.json()
        _save_tokens(tokens)
        return tokens


def refresh_tokens(refresh_token: str) -> dict:
    with httpx.Client() as client:
        response = client.post(
            f"{settings.exact_base_url}{_TOKEN_PATH}",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.exact_client_id,
                "client_secret": settings.exact_client_secret,
            },
        )
        response.raise_for_status()
        tokens = response.json()
        _save_tokens(tokens)
        return tokens


def get_valid_access_token() -> str:
    tokens = _load_tokens()
    if tokens is None:
        raise RuntimeError("Geen tokens gevonden. Autoriseer eerst via /auth/login.")

    if time.time() >= tokens.get("expires_at", 0):
        tokens = refresh_tokens(tokens["refresh_token"])

    return tokens["access_token"]


def get_current_division(access_token: str) -> int:
    with httpx.Client() as client:
        response = client.get(
            f"{settings.exact_base_url}/api/v1/current/Me",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["d"]["results"][0]["CurrentDivision"]
