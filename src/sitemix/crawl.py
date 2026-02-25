from __future__ import annotations

import fnmatch
import os
import posixpath
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from defusedxml import ElementTree as ET

from sitemix.http import DelayController, HttpClient
from sitemix.schemas import SiteMapEntry, SkippedUrl

BINARY_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bin",
    ".bz2",
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".json",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".rss",
    ".svg",
    ".tar",
    ".tgz",
    ".tif",
    ".tiff",
    ".tsv",
    ".wav",
    ".webm",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)


def canonicalize_url(url: str, base_url: str | None = None) -> str:
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower()

    if not hostname:
        return ""

    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    norm_path = posixpath.normpath(path)
    if not norm_path.startswith("/"):
        norm_path = f"/{norm_path}"
    if norm_path != "/" and norm_path.endswith("/"):
        norm_path = norm_path[:-1]

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query = urlencode(sorted(query_pairs)) if query_pairs else ""

    canonical = urlunparse((scheme, netloc, norm_path, "", query, ""))
    return canonical


def is_binary_url(url: str) -> bool:
    parsed = urlparse(url)
    _, ext = os.path.splitext(parsed.path.lower())
    return ext in BINARY_EXTENSIONS


def is_query_heavy(url: str, max_params: int = 3, max_query_len: int = 80) -> bool:
    parsed = urlparse(url)
    if not parsed.query:
        return False
    params = parse_qsl(parsed.query, keep_blank_values=True)
    return len(params) > max_params or len(parsed.query) > max_query_len


def _matches_patterns(url: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(url, pattern):
            return True
    return False


def should_skip_url(
    url: str,
    *,
    query_filter: bool,
    allow_patterns: list[str],
    deny_patterns: list[str],
) -> str | None:
    if is_binary_url(url):
        return "binary-extension"
    if query_filter and is_query_heavy(url):
        return "query-heavy"
    if deny_patterns and _matches_patterns(url, deny_patterns):
        return "deny-pattern"
    if allow_patterns and not _matches_patterns(url, allow_patterns):
        return "allow-pattern-miss"
    return None


def extract_links(html: str, base_url: str) -> list[str]:
    parser = LinkExtractor()
    parser.feed(html)
    links: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        canon = canonicalize_url(href, base_url=base_url)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        links.append(canon)
    links.sort()
    return links


def parse_sitemap_xml_entries(xml_text: str) -> tuple[list[str], list[str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []

    ns_match = re.match(r"\{(.+)\}", root.tag)
    namespace = ns_match.group(1) if ns_match else None

    def qname(tag: str) -> str:
        if not namespace:
            return tag
        return f"{{{namespace}}}{tag}"

    urls: list[str] = []
    for loc in root.findall(f".//{qname('url')}/{qname('loc')}"):
        if loc.text:
            urls.append(loc.text.strip())

    # Sitemap index fallback.
    sitemap_locs: list[str] = []
    for loc in root.findall(f".//{qname('sitemap')}/{qname('loc')}"):
        if loc.text:
            sitemap_locs.append(loc.text.strip())
    return urls, sitemap_locs


def parse_sitemap_xml(xml_text: str) -> list[str]:
    urls, sitemap_locs = parse_sitemap_xml_entries(xml_text)
    return urls or sitemap_locs


def parse_url_list_text(text: str) -> list[str]:
    urls: list[str] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        urls.append(candidate)
    return urls


def load_sitemap_source(path_or_url: str, client: HttpClient, max_depth: int = 2) -> list[str]:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        body = client.fetch_text(path_or_url).text
    else:
        with open(path_or_url, encoding="utf-8") as f:
            body = f.read()

    stripped = body.lstrip()
    if stripped.startswith("<"):
        urls, sitemap_locs = parse_sitemap_xml_entries(body)
        if urls:
            return urls
        if max_depth <= 0 or not sitemap_locs:
            return sitemap_locs
        aggregated: list[str] = []
        seen: set[str] = set()
        for location in sitemap_locs:
            if location in seen:
                continue
            seen.add(location)
            try:
                child_urls = load_sitemap_source(location, client, max_depth=max_depth - 1)
            except Exception:
                continue
            for child_url in child_urls:
                if child_url not in seen:
                    seen.add(child_url)
                    aggregated.append(child_url)
        return aggregated
    return parse_url_list_text(body)


@dataclass
class CrawlDiscovery:
    discovered: list[SiteMapEntry]
    skipped: list[SkippedUrl]


class RobotsCache:
    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str, user_agent: str = "sitemix") -> bool:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False

        key = f"{parsed.scheme}://{host}:{parsed.port or ''}"
        parser = self._cache.get(key)
        if parser is None:
            robots_url = f"{parsed.scheme}://{host}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                # Fail open: if robots cannot be fetched, allow crawl.
                return True
            self._cache[key] = parser
        return parser.can_fetch(user_agent, url)


def discover_urls(
    *,
    start_url: str,
    client: HttpClient,
    max_pages: int,
    include_external: bool,
    respect_robots: bool,
    delay_controller: DelayController,
    query_filter: bool,
    allow_patterns: list[str],
    deny_patterns: list[str],
) -> CrawlDiscovery:
    start = canonicalize_url(start_url)
    if not start:
        return CrawlDiscovery(
            discovered=[], skipped=[SkippedUrl(url=start_url, reason="invalid-start-url")]
        )

    start_host = urlparse(start).hostname
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    seen: set[str] = set()
    discovered: list[SiteMapEntry] = []
    skipped: list[SkippedUrl] = []
    robots = RobotsCache()

    while queue and len(discovered) < max_pages:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        if not include_external and urlparse(url).hostname != start_host:
            skipped.append(SkippedUrl(url=url, reason="external-host"))
            continue

        reason = should_skip_url(
            url,
            query_filter=query_filter,
            allow_patterns=allow_patterns,
            deny_patterns=deny_patterns,
        )
        if reason:
            skipped.append(SkippedUrl(url=url, reason=reason))
            continue

        if respect_robots and not robots.allowed(url):
            skipped.append(SkippedUrl(url=url, reason="robots-disallow"))
            continue

        delay_controller.sleep()
        try:
            fetched = client.fetch_text(url)
        except Exception:
            skipped.append(SkippedUrl(url=url, reason="fetch-failed"))
            continue

        if "html" not in fetched.content_type.lower():
            skipped.append(SkippedUrl(url=url, reason="non-html"))
            continue
        discovered.append(SiteMapEntry(url=url, depth=depth))

        for child in extract_links(fetched.text, fetched.fetched_url):
            if child not in seen:
                queue.append((child, depth + 1))

    return CrawlDiscovery(discovered=discovered, skipped=skipped)
