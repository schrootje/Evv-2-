from typing import Any

import httpx

from app.auth.oauth import get_current_division, get_valid_access_token
from app.config import settings


class ExactClient:
    """Thin wrapper around the Exact Online REST API."""

    def __init__(self) -> None:
        self.access_token = get_valid_access_token()
        self.division = get_current_division(self.access_token)
        self._base = f"{settings.exact_base_url}/api/v1/{self.division}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        results: list = []
        while url:
            with httpx.Client() as client:
                response = client.get(url, headers=self._headers(), params=params)
                response.raise_for_status()
                body = response.json()
            data = body.get("d", {})
            page = data.get("results", [])
            results.extend(page)
            url = data.get("__next")
            params = None  # __next already contains query params
        return results

    def post(self, path: str, payload: dict) -> Any:
        with httpx.Client() as client:
            response = client.post(
                f"{self._base}{path}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("d", {})

    def delete(self, path: str) -> None:
        with httpx.Client() as client:
            response = client.delete(f"{self._base}{path}", headers=self._headers())
            response.raise_for_status()
