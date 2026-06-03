"""
GitHub API client — wraps the GitHub REST API for ContextClaw.

Handles:
- Installing/uninstalling GitHub App
- Listing repos for an installation
- Fetching file content, PRs, commits
"""

from __future__ import annotations

import hmac
import os
from hashlib import sha256
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
GITHUB_APP_URL = "https://github.com/apps"


def _get_app_credentials() -> tuple[str, str]:
    app_id = os.environ.get("GITHUB_APP_ID", "")
    private_key = os.environ.get("GITHUB_PRIVATE_KEY", "")
    return app_id, private_key


def get_install_url(org_slug: str | None = None) -> str:
    """Generate the GitHub App install URL, optionally scoped to an org."""
    app_id = os.environ.get("GITHUB_APP_ID", "")
    base = f"{GITHUB_APP_URL}/contextclaw-app"
    if org_slug:
        return f"{base}/installations/new/permissions?suggested_target_id={org_slug}"
    return f"{base}/installations/new"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange OAuth code for an installation access token."""
    app_id, private_key = _get_app_credentials()
    if not app_id or not private_key:
        return {"error": "GitHub App not configured"}

    # Generate JWT for app auth
    import jwt as pyjwt
    import time

    payload = {
        "iat": int(time.time()) - 60,
        "exp": int(time.time()) + 600,
        "iss": app_id,
    }
    app_token = pyjwt.encode(payload, private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{code}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def list_installation_repos(
    installation_id: int,
) -> list[dict[str, Any]]:
    """List all repos accessible to a GitHub App installation."""
    app_id, private_key = _get_app_credentials()
    import time
    import jwt as pyjwt

    payload = {
        "iat": int(time.time()) - 60,
        "exp": int(time.time()) + 600,
        "iss": app_id,
    }
    app_token = pyjwt.encode(payload, private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()
        token = token_data["token"]

        repo_resp = await client.get(
            f"{GITHUB_API}/installation/repositories",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        repo_resp.raise_for_status()
        return repo_resp.json().get("repositories", [])


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
