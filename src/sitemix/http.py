from __future__ import annotations

import random
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sitemix import __version__

USER_AGENT = f"sitemix/{__version__} (+https://github.com/shaypal5/sitemix)"


@dataclass
class FetchResult:
    requested_url: str
    fetched_url: str
    status_code: int
    content_type: str
    text: str


class HttpClient:
    def __init__(
        self,
        *,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        retries: int = 2,
        user_agent: str = USER_AGENT,
    ) -> None:
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            allowed_methods=frozenset(["GET", "HEAD"]),
            status_forcelist=(429, 500, 502, 503, 504),
            backoff_factor=0.5,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def fetch_text(self, url: str) -> FetchResult:
        response = self.session.get(url, timeout=(self.connect_timeout, self.read_timeout))
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        return FetchResult(
            requested_url=url,
            fetched_url=response.url,
            status_code=response.status_code,
            content_type=content_type,
            text=response.text,
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()


class DelayController:
    def __init__(self, delay: float, jitter: float) -> None:
        self.delay = max(delay, 0.0)
        self.jitter = max(jitter, 0.0)

    def sleep(self) -> None:
        if self.delay <= 0 and self.jitter <= 0:
            return

        extra = random.uniform(0, self.jitter) if self.jitter > 0 else 0.0
        time.sleep(self.delay + extra)
