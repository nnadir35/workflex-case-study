"""
API clients for the three upstream systems exposed by the mock server:
    - Jira Cloud REST API v3 (HTTP Basic auth)
    - HubSpot CRM v3        (Bearer token)
    - Microsoft Graph / Teams (OAuth2 client credentials -> Bearer token)

Each client wraps the thin set of endpoints the Bridge Agent actually needs.
"""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx


# --------------------------------------------------------------------------- #
# Atlassian Document Format helpers                                            #
# --------------------------------------------------------------------------- #

def to_adf(text: str) -> dict:
    """Minimal text -> ADF converter. Jira description & comment bodies need ADF."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()] or [""]
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": p}]}
            for p in paragraphs
        ],
    }


def adf_to_text(node: Any) -> str:
    """Flatten an ADF document back to plain text (best-effort)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(filter(None, (adf_to_text(n) for n in node)))
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return adf_to_text(node.get("content"))
    return ""


# --------------------------------------------------------------------------- #
# Jira                                                                         #
# --------------------------------------------------------------------------- #

class JiraClient:
    def __init__(self, base_url: str, email: str, token: str, project_key: str = "JIRA"):
        self.root_base = base_url.rstrip("/")
        self.base = f"{base_url.rstrip('/')}/jira/rest/api/3"
        self.project_key = project_key
        self.email = email
        self.token = token
        self._headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        creds = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        return {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> None:
        r = httpx.get(f"{self.root_base}/auth/tokens", timeout=10)
        r.raise_for_status()
        tokens = r.json()
        jira = tokens.get("jira")
        if not jira or not jira.get("token"):
            create = httpx.post(
                f"{self.root_base}/auth/tokens/jira",
                json={"email": self.email},
                timeout=10,
            )
            create.raise_for_status()
            jira = create.json()
        self.email = jira.get("email", self.email)
        self.token = jira["token"]
        self._headers = self._build_headers()

    def search_issues(self, max_results: int = 100) -> list[dict]:
        r = httpx.get(
            f"{self.base}/search",
            headers=self._headers,
            params={"maxResults": max_results},
            timeout=30,
        )
        if r.status_code == 401:
            self._refresh_token()
            r = httpx.get(
                f"{self.base}/search",
                headers=self._headers,
                params={"maxResults": max_results},
                timeout=30,
            )
        r.raise_for_status()
        return r.json().get("issues", [])

    def create_issue(self, summary: str, description: str, labels: list[str] | None = None) -> dict:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": to_adf(description),
                "issuetype": {"name": "Story"},
                "labels": labels or [],
            }
        }
        r = httpx.post(f"{self.base}/issue", headers=self._headers, json=payload, timeout=30)
        if r.status_code == 401:
            self._refresh_token()
            r = httpx.post(f"{self.base}/issue", headers=self._headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def add_comment(self, issue_key: str, body: str) -> dict:
        r = httpx.post(
            f"{self.base}/issue/{issue_key}/comment",
            headers=self._headers,
            json={"body": to_adf(body)},
            timeout=30,
        )
        if r.status_code == 401:
            self._refresh_token()
            r = httpx.post(
                f"{self.base}/issue/{issue_key}/comment",
                headers=self._headers,
                json={"body": to_adf(body)},
                timeout=30,
            )
        r.raise_for_status()
        return r.json()


# --------------------------------------------------------------------------- #
# HubSpot                                                                      #
# --------------------------------------------------------------------------- #

class HubSpotClient:
    def __init__(self, base_url: str, token: str):
        self.root_base = base_url.rstrip("/")
        self.base = f"{base_url.rstrip('/')}/hubspot/crm/v3"
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> None:
        r = httpx.get(f"{self.root_base}/auth/tokens", timeout=10)
        r.raise_for_status()
        tokens = r.json()
        hubspot = tokens.get("hubspot")
        if not hubspot or not hubspot.get("token"):
            create = httpx.post(f"{self.root_base}/auth/tokens/hubspot", timeout=10)
            create.raise_for_status()
            hubspot = create.json()
        self.token = hubspot["token"]
        self._headers["Authorization"] = f"Bearer {self.token}"

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase, drop punctuation/legal suffixes — so 'Weyland-Yutani' matches 'Weyland Yutani Corp'."""
        import re as _re
        s = s.lower()
        s = _re.sub(r"[^a-z0-9]+", " ", s)
        for suffix in (" inc", " corp", " corporation", " ltd", " llc", " gmbh",
                       " company", " co", " international"):
            if s.endswith(suffix):
                s = s[: -len(suffix)]
        return s.strip()

    def _search(self, query: str) -> list[dict]:
        payload = {
            "query": query,
            "properties": ["name", "domain", "annual_recurring_revenue", "annualrevenue"],
            "limit": 20,
        }
        r = httpx.post(
            f"{self.base}/objects/companies/search",
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        if r.status_code == 401:
            self._refresh_token()
            r = httpx.post(
                f"{self.base}/objects/companies/search",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
        r.raise_for_status()
        return r.json().get("results", [])

    def search_company(self, name: str) -> dict | None:
        """Return the best-matching company record for a loose/fuzzy name, or None."""
        q_norm = self._normalize(name)

        # Try the raw query first, then fall back to the first word (handles
        # 'Weyland-Yutani' → 'Weyland' when HubSpot's full-text search is picky).
        candidates = self._search(name)
        if not candidates and q_norm:
            candidates = self._search(q_norm.split()[0])
        if not candidates:
            return None

        def score(c: dict) -> tuple[int, int]:
            cname_norm = self._normalize(c.get("properties", {}).get("name") or "")
            if cname_norm == q_norm:
                return (4, -len(cname_norm))
            if cname_norm.startswith(q_norm) or q_norm.startswith(cname_norm):
                return (3, -len(cname_norm))
            # Token overlap
            q_tokens = set(q_norm.split())
            c_tokens = set(cname_norm.split())
            overlap = len(q_tokens & c_tokens)
            if overlap and q_tokens.issubset(c_tokens):
                return (2, -len(cname_norm))
            if overlap:
                return (1, overlap)
            return (0, 0)

        candidates.sort(key=score, reverse=True)
        best = candidates[0]
        return best if score(best)[0] > 0 else None

    @staticmethod
    def get_arr(company: dict | None) -> int | None:
        if not company:
            return None
        props = company.get("properties", {})
        for key in ("annual_recurring_revenue", "annualrevenue"):
            v = props.get(key)
            if v not in (None, ""):
                try:
                    return int(float(v))
                except ValueError:
                    continue
        return None


# --------------------------------------------------------------------------- #
# Microsoft Teams (Graph)                                                      #
# --------------------------------------------------------------------------- #

class TeamsClient:
    """
    Uses OAuth2 client-credentials to fetch a Bearer access token, then calls
    the Graph-style endpoints exposed by the mock server.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        team_id: str | None = None,
        channel_id: str | None = None,
    ):
        self.base = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.team_id = team_id
        self.channel_id = channel_id
        self._access_token: str | None = None

    def _auth_headers(self) -> dict[str, str]:
        if self._access_token is None:
            self._authenticate()
        return {"Authorization": f"Bearer {self._access_token}"}

    def _refresh_client_secret(self) -> None:
        """
        Self-heal when the stored Teams client secret is stale by asking the
        mock server for the currently active token.
        """
        r = httpx.get(f"{self.base}/auth/tokens", timeout=10)
        r.raise_for_status()
        tokens = r.json()
        teams = tokens.get("teams")
        if not teams or not teams.get("token"):
            create = httpx.post(f"{self.base}/auth/tokens/teams", timeout=10)
            create.raise_for_status()
            teams = create.json()
        self.client_secret = teams["token"]

    def _authenticate(self) -> None:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        r = httpx.post(f"{self.base}/auth/teams/token", data=payload, timeout=30)
        if r.status_code == 401:
            # If the saved secret no longer matches the running mock-server
            # state (e.g. server restart), fetch a fresh one and retry once.
            self._refresh_client_secret()
            payload["client_secret"] = self.client_secret
            r = httpx.post(f"{self.base}/auth/teams/token", data=payload, timeout=30)
        r.raise_for_status()
        self._access_token = r.json()["access_token"]

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base}{path}"
        r = httpx.request(method, url, headers=self._auth_headers(), timeout=30, **kwargs)
        if r.status_code == 401:
            self._access_token = None
            r = httpx.request(method, url, headers=self._auth_headers(), timeout=30, **kwargs)
        r.raise_for_status()
        return r

    def _discover_channel(self) -> None:
        """If team/channel IDs weren't provided, discover #feature-requests."""
        if self.team_id and self.channel_id:
            return
        teams = self._request("GET", "/graph/v1.0/teams").json()["value"]
        self.team_id = teams[0]["id"]
        channels = self._request(
            "GET", f"/graph/v1.0/teams/{self.team_id}/channels"
        ).json()["value"]
        match = next(
            (c for c in channels if "feature-requests" in c.get("displayName", "").lower()),
            channels[0],
        )
        self.channel_id = match["id"]

    def list_messages(self, top: int = 50) -> list[dict]:
        self._discover_channel()
        r = self._request(
            "GET",
            f"/graph/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages",
            params={"$top": top},
        )
        return r.json().get("value", [])

    def post_message(self, text: str) -> dict:
        self._discover_channel()
        r = self._request(
            "POST",
            f"/graph/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages",
            json={"body": {"contentType": "text", "content": text}},
        )
        return r.json()

    def reply_to_message(self, message_id: str, text: str) -> dict:
        self._discover_channel()
        r = self._request(
            "POST",
            f"/graph/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages/{message_id}/replies",
            json={"body": {"contentType": "text", "content": text}},
        )
        return r.json()


# --------------------------------------------------------------------------- #
# Bootstrap                                                                    #
# --------------------------------------------------------------------------- #

def _auto_provision_tokens(base_url: str) -> dict[str, str]:
    """
    Demo convenience: if tokens aren't in .env, generate fresh ones via the
    mock server's dashboard endpoints. Returns a dict of token values.
    """
    base = base_url.rstrip("/")
    out: dict[str, str] = {}

    existing = httpx.get(f"{base}/auth/tokens", timeout=10).json()

    jira = existing.get("jira") or httpx.post(
        f"{base}/auth/tokens/jira",
        json={"email": os.getenv("JIRA_EMAIL", "candidate@workflex.com")},
        timeout=10,
    ).json()
    hubspot = existing.get("hubspot") or httpx.post(f"{base}/auth/tokens/hubspot", timeout=10).json()
    teams = existing.get("teams") or httpx.post(f"{base}/auth/tokens/teams", timeout=10).json()

    out["JIRA_EMAIL"] = jira["email"]
    out["JIRA_TOKEN"] = jira["token"]
    out["HUBSPOT_TOKEN"] = hubspot["token"]
    out["TEAMS_CLIENT_SECRET"] = teams["token"]
    return out


def build_clients() -> tuple[JiraClient, HubSpotClient, TeamsClient]:
    """Construct all three clients from environment variables, auto-provisioning if needed."""
    base_url = os.getenv("MOCK_API_BASE_URL", "http://localhost:8080")

    required = ("JIRA_TOKEN", "HUBSPOT_TOKEN", "TEAMS_CLIENT_SECRET")
    if not all(os.getenv(k) for k in required):
        for k, v in _auto_provision_tokens(base_url).items():
            # Unconditionally write so empty ("") values in .env get overridden.
            os.environ[k] = v

    jira = JiraClient(
        base_url=base_url,
        email=os.getenv("JIRA_EMAIL", "candidate@workflex.com"),
        token=os.environ["JIRA_TOKEN"],
    )
    hubspot = HubSpotClient(base_url=base_url, token=os.environ["HUBSPOT_TOKEN"])
    teams = TeamsClient(
        base_url=base_url,
        client_id=os.getenv("TEAMS_CLIENT_ID", "bridge-agent"),
        client_secret=os.environ["TEAMS_CLIENT_SECRET"],
    )
    return jira, hubspot, teams
