"""A polite HTTP client for the source adapters: an identifying User-Agent, a pause between calls, retries.

Wikimedia asks API clients to identify themselves and to back off when told to (HTTP 429, ``maxlag``); the NHM and
GBIF APIs are shared public services too. Every adapter goes through ``Polite`` so the harvest never hammers them.
"""

from __future__ import annotations

import time

import httpx2

USER_AGENT = "Laminario base-collection harvester (https://github.com/fsantibanezleal/CAOS_Laminario)"


class SourceError(RuntimeError):
    pass


class Polite:
    def __init__(self, pause_s: float = 1.0, retries: int = 5, timeout_s: float = 60.0) -> None:
        self.pause_s = pause_s
        self.retries = retries
        self.client = httpx2.Client(timeout=timeout_s, follow_redirects=True, headers={"User-Agent": USER_AGENT})
        self._last = 0.0

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> Polite:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _wait(self) -> None:
        delay = self.pause_s - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def get(self, url: str, params: dict | None = None) -> httpx2.Response:
        """GET with the pause, retrying on 429, 5xx and network errors with a growing backoff."""
        backoff = 2.0
        for attempt in range(self.retries):
            self._wait()
            try:
                response = self.client.get(url, params=params)
            except httpx2.HTTPError as exc:
                error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return response
                if response.status_code not in (429, 500, 502, 503, 504):
                    raise SourceError(f"{url} answered {response.status_code}")
                error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("retry-after")
                if retry_after and retry_after.isdigit():
                    backoff = max(backoff, float(retry_after))
            if attempt == self.retries - 1:
                raise SourceError(f"{url}: {error} after {self.retries} attempts")
            time.sleep(backoff)
            backoff *= 2
        raise SourceError(url)

    def json(self, url: str, params: dict | None = None):
        return self.get(url, params).json()
