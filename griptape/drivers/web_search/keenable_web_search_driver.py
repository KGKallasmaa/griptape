from __future__ import annotations

import json
from typing import Any

import requests
from attrs import define, field

from griptape.artifacts import ListArtifact, TextArtifact
from griptape.drivers.web_search import BaseWebSearchDriver


@define
class KeenableWebSearchDriver(BaseWebSearchDriver):
    """Web search through the Keenable Search API (https://docs.keenable.ai/api-reference/search).

    The API key is optional. Without one, requests go to the keyless public endpoint, which Keenable
    rate-limits per IP address. With a key, requests go to the keyed endpoint with the `X-API-Key` header.
    Both send `X-Keenable-Title` (required by the public endpoint) so the traffic is labelled.

    Attributes:
        api_key: Keenable API key. Optional.
        app_title: Value of the `X-Keenable-Title` header.
        mode: `"pro"` (Keenable's default) or `"realtime"` (lower latency). Left out when not set.
        params: Extra fields for the request body, e.g. `{"exclude_domains": ["pinterest.com"]}`.
        timeout: Request timeout in seconds.
    """

    api_key: str | None = field(default=None, kw_only=True, metadata={"serializable": False})
    app_title: str = field(default="griptape", kw_only=True, metadata={"serializable": True})
    mode: str | None = field(default=None, kw_only=True, metadata={"serializable": True})
    base_url: str = field(default="https://api.keenable.ai/v1", kw_only=True, metadata={"serializable": True})
    params: dict[str, Any] = field(factory=dict, kw_only=True, metadata={"serializable": True})
    timeout: float = field(default=30.0, kw_only=True, metadata={"serializable": True})

    def search(self, query: str, **kwargs) -> ListArtifact:
        return ListArtifact([TextArtifact(json.dumps(result)) for result in self._search_keenable(query, **kwargs)])

    def _search_keenable(self, query: str, **kwargs) -> list[dict]:
        headers = {"Content-Type": "application/json", "X-Keenable-Title": self.app_title}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            url = f"{self.base_url}/search"
        else:
            url = f"{self.base_url}/search/public"

        body: dict[str, Any] = {
            "query": query,
            # Keenable accepts 1-50 results per request.
            "max_results": max(1, min(self.results_count, 50)),
            # Instant-answer cards use cards.keenable.ai URLs that expire after a day.
            "disable_cards": True,
            **self.params,
            **kwargs,
        }
        if self.mode is not None:
            body.setdefault("mode", self.mode)

        response = requests.post(url, headers=headers, json=body, timeout=self.timeout)

        if response.status_code == 200:
            data = response.json()

            return [
                {
                    "url": r["url"],
                    "title": r.get("title", ""),
                    "description": r.get("snippet") or r.get("description", ""),
                }
                for r in data.get("results", [])
                if r.get("url")
            ]

        raise Exception(
            f"Keenable Search API returned an error with status code "
            f"{response.status_code} and reason '{response.reason}'",
        )
