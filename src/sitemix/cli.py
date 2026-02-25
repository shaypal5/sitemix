from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from rich.console import Console

from sitemix import __version__
from sitemix.crawl import (
    RobotsCache,
    canonicalize_url,
    discover_urls,
    load_sitemap_source,
    should_skip_url,
)
from sitemix.extract import build_page_doc
from sitemix.formatters import (
    page_to_json,
    page_to_markdown,
    page_to_xml,
    site_to_json,
    site_to_markdown,
    site_to_xml,
)
from sitemix.http import DelayController, HttpClient
from sitemix.schemas import CrawlParams, PageDoc, SiteDump, SiteMapEntry, SkippedUrl
from sitemix.utils import slugify, utc_now_iso

app = typer.Typer(
    help="sitemix: turn a page or small site into an LLM-oriented dump.", no_args_is_help=True
)
console = Console(stderr=True)

OutputFormat = Annotated[
    str,
    typer.Option(
        "--format",
        help="Output format",
        case_sensitive=False,
        show_default=True,
    ),
]


def _write_output(
    content: str, *, out: Path | None, use_stdout: bool, default_name: str
) -> Path | None:
    if use_stdout:
        typer.echo(content, nl=False)
        return None

    target = out or Path.cwd() / default_name
    target.write_text(content, encoding="utf-8")
    return target


def _render_page(page: PageDoc, fmt: str) -> str:
    fmt_norm = fmt.lower()
    if fmt_norm in {"md", "markdown"}:
        return page_to_markdown(page)
    if fmt_norm == "json":
        return page_to_json(page)
    if fmt_norm == "xml":
        return page_to_xml(page)
    raise typer.BadParameter(
        "format must be one of: md, markdown, json, xml",
        param_hint="--format",
    )


def _render_site(site_dump: SiteDump, fmt: str) -> str:
    fmt_norm = fmt.lower()
    if fmt_norm in {"md", "markdown"}:
        return site_to_markdown(site_dump)
    if fmt_norm == "json":
        return site_to_json(site_dump)
    if fmt_norm == "xml":
        return site_to_xml(site_dump)
    raise typer.BadParameter(
        "format must be one of: md, markdown, json, xml",
        param_hint="--format",
    )


def _collect_stdin_urls() -> list[str]:
    if sys.stdin.isatty():
        return []
    urls: list[str] = []
    for line in sys.stdin:
        value = line.strip()
        if value:
            urls.append(value)
    return urls


def _default_page_filename(url: str, fmt: str) -> str:
    fmt_norm = fmt.lower()
    ext = "md" if fmt_norm in {"md", "markdown"} else fmt_norm
    return f"{slugify(url)}.{ext}"


def _default_site_filename(start_url: str, finished_at: str, fmt: str) -> str:
    host = urlparse(start_url).hostname or "site"
    stamp = finished_at.replace(":", "").replace("-", "")
    fmt_norm = fmt.lower()
    ext = "md" if fmt_norm in {"md", "markdown"} else fmt_norm
    return f"site_{slugify(host)}_{stamp}.{ext}"


def _extract_one_url(
    *,
    url: str,
    min_text_chars: int,
    connect_timeout: float,
    read_timeout: float,
    retries: int,
    delay: float,
    jitter: float,
) -> PageDoc | tuple[str, str]:
    delay_controller = DelayController(delay, jitter)
    with HttpClient(
        connect_timeout=connect_timeout, read_timeout=read_timeout, retries=retries
    ) as client:
        delay_controller.sleep()
        try:
            fetched = client.fetch_text(url)
        except Exception as exc:
            return (url, f"fetch-error: {exc}")

        if "html" not in fetched.content_type.lower():
            return (url, f"non-html-content-type: {fetched.content_type}")

        page = build_page_doc(
            url=url,
            fetched_url=fetched.fetched_url,
            html=fetched.text,
            min_text_chars=min_text_chars,
        )
        return page


@app.command()
def page(
    url: str,
    out: Annotated[Path | None, typer.Option("-o", "--out", help="Output file path")] = None,
    output_format: OutputFormat = "md",
    stdout: Annotated[bool, typer.Option("--stdout", help="Write result to stdout")] = False,
    min_text_chars: Annotated[
        int, typer.Option(help="Extraction threshold before trying fallbacks")
    ] = 400,
    connect_timeout: Annotated[float, typer.Option(help="Connect timeout in seconds")] = 10.0,
    read_timeout: Annotated[float, typer.Option(help="Read timeout in seconds")] = 30.0,
    network_retries: Annotated[int, typer.Option(help="Network retries for fetch requests")] = 2,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Verbose logging")] = False,
) -> None:
    """Extract one page into markdown/json/xml for LLM ingestion."""
    canonical_url = canonicalize_url(url)
    if not canonical_url:
        raise typer.BadParameter("URL is invalid or missing hostname.", param_hint="url")

    if verbose:
        console.print(f"[cyan]Fetching:[/cyan] {canonical_url}")

    try:
        result = _extract_one_url(
            url=canonical_url,
            min_text_chars=min_text_chars,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries=network_retries,
            delay=0,
            jitter=0,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if isinstance(result, tuple):
        failed_url, reason = result
        console.print(f"[red]Failed:[/red] {failed_url} ({reason})")
        raise typer.Exit(code=1)

    rendered = _render_page(result, output_format)
    written = _write_output(
        rendered,
        out=out,
        use_stdout=stdout,
        default_name=_default_page_filename(canonical_url, output_format.lower()),
    )
    if written and verbose:
        console.print(f"[green]Wrote:[/green] {written}")


@app.command()
def site(
    start_url: str,
    url: Annotated[
        list[str] | None,
        typer.Option("--url", help="Additional URL(s) to include"),
    ] = None,
    sitemap: Annotated[
        str | None, typer.Option("--sitemap", help="Sitemap XML/TXT path or URL")
    ] = None,
    no_sitemap: Annotated[
        bool, typer.Option("--no-sitemap", help="Skip automatic /sitemap.xml probe")
    ] = False,
    include_external: Annotated[
        bool, typer.Option("--include-external", help="Allow off-host links")
    ] = False,
    ignore_robots: Annotated[
        bool, typer.Option("--ignore-robots", help="Ignore robots.txt")
    ] = False,
    max_pages: Annotated[int, typer.Option(help="Maximum pages to include (default 200)")] = 200,
    i_know_what_im_doing: Annotated[
        bool, typer.Option("--i-know-what-im-doing", help="Override hard cap of 500 pages")
    ] = False,
    delay: Annotated[float, typer.Option(help="Delay between requests in seconds")] = 1.0,
    jitter: Annotated[float, typer.Option(help="Random jitter in seconds")] = 0.3,
    concurrency: Annotated[int, typer.Option(help="Concurrent extraction workers")] = 2,
    allow_pattern: Annotated[
        list[str] | None,
        typer.Option("--allow-pattern", help="fnmatch allowlist"),
    ] = None,
    deny_pattern: Annotated[
        list[str] | None,
        typer.Option("--deny-pattern", help="fnmatch denylist"),
    ] = None,
    allow_query_heavy: Annotated[
        bool,
        typer.Option("--allow-query-heavy", help="Do not skip query-heavy URLs"),
    ] = False,
    out: Annotated[Path | None, typer.Option("-o", "--out", help="Output file path")] = None,
    output_format: OutputFormat = "md",
    stdout: Annotated[bool, typer.Option("--stdout", help="Write result to stdout")] = False,
    min_text_chars: Annotated[
        int, typer.Option(help="Extraction threshold before trying fallbacks")
    ] = 400,
    connect_timeout: Annotated[float, typer.Option(help="Connect timeout in seconds")] = 10.0,
    read_timeout: Annotated[float, typer.Option(help="Read timeout in seconds")] = 30.0,
    network_retries: Annotated[int, typer.Option(help="Network retries for fetch requests")] = 2,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Verbose logging")] = False,
) -> None:
    """Extract a small website into one LLM-oriented dump file."""
    started_at = utc_now_iso()

    start = canonicalize_url(start_url)
    if not start:
        raise typer.BadParameter(
            "start_url is invalid or missing hostname.", param_hint="start_url"
        )

    if max_pages > 500 and not i_know_what_im_doing:
        raise typer.BadParameter(
            "max_pages above 500 requires --i-know-what-im-doing.",
            param_hint="--max-pages",
        )

    if max_pages <= 0:
        raise typer.BadParameter("max_pages must be positive", param_hint="--max-pages")

    if concurrency <= 0:
        raise typer.BadParameter("concurrency must be positive", param_hint="--concurrency")

    query_filter = not allow_query_heavy
    respect_robots = not ignore_robots
    allow_patterns = allow_pattern or []
    deny_patterns = deny_pattern or []
    extra_urls = url or []

    initial_urls = [start]
    initial_urls.extend(_collect_stdin_urls())
    initial_urls.extend(extra_urls)
    start_host = urlparse(start).hostname

    skipped_urls: list[SkippedUrl] = []
    sitemap_entries: list[SiteMapEntry] = []

    with HttpClient(
        connect_timeout=connect_timeout, read_timeout=read_timeout, retries=network_retries
    ) as client:
        # User provided sitemap source has first priority.
        if sitemap:
            if verbose:
                console.print(f"[cyan]Loading sitemap source:[/cyan] {sitemap}")
            try:
                sitemap_urls = load_sitemap_source(sitemap, client)
            except Exception as exc:
                console.print(f"[red]Failed to load sitemap source:[/red] {exc}")
                raise typer.Exit(code=1) from exc
            for found in sitemap_urls:
                canon = canonicalize_url(found, base_url=start)
                if not canon:
                    continue
                if not include_external and urlparse(canon).hostname != start_host:
                    skipped_urls.append(SkippedUrl(url=canon, reason="external-host"))
                    continue
                if canon:
                    sitemap_entries.append(SiteMapEntry(url=canon, depth=0))

        # Auto-probe /sitemap.xml if not disabled and no manual sitemap provided.
        if not sitemap and not no_sitemap:
            sitemap_probe = canonicalize_url("/sitemap.xml", base_url=start)
            if verbose:
                console.print(f"[cyan]Probing sitemap:[/cyan] {sitemap_probe}")
            try:
                probe_urls = load_sitemap_source(sitemap_probe, client)
            except Exception:
                probe_urls = []
            for found in probe_urls:
                canon = canonicalize_url(found, base_url=start)
                if not canon:
                    continue
                if not include_external and urlparse(canon).hostname != start_host:
                    skipped_urls.append(SkippedUrl(url=canon, reason="external-host"))
                    continue
                if canon:
                    sitemap_entries.append(SiteMapEntry(url=canon, depth=0))

        if sitemap_entries:
            dedup: dict[str, SiteMapEntry] = {}
            for entry in sitemap_entries:
                dedup[entry.url] = entry
            sitemap_entries = list(dedup.values())
            sitemap_entries.sort(key=lambda item: item.url)
            if len(sitemap_entries) > max_pages:
                sitemap_entries = sitemap_entries[:max_pages]
        else:
            delay_controller = DelayController(delay, jitter)
            if verbose:
                console.print("[cyan]Running BFS discovery crawl[/cyan]")
            discovery = discover_urls(
                start_url=start,
                client=client,
                max_pages=max_pages,
                include_external=include_external,
                respect_robots=respect_robots,
                delay_controller=delay_controller,
                query_filter=query_filter,
                allow_patterns=allow_patterns,
                deny_patterns=deny_patterns,
            )
            sitemap_entries = discovery.discovered
            skipped_urls.extend(discovery.skipped)

    # Add explicit URLs (flags/stdin/start), respecting dedupe and filters.
    dedup_map: dict[str, SiteMapEntry] = {entry.url: entry for entry in sitemap_entries}
    for raw_url in initial_urls:
        canon = canonicalize_url(raw_url, base_url=start)
        if not canon:
            skipped_urls.append(SkippedUrl(url=raw_url, reason="invalid-url"))
            continue
        if not include_external and urlparse(canon).hostname != start_host:
            skipped_urls.append(SkippedUrl(url=canon, reason="external-host"))
            continue
        reason = should_skip_url(
            canon,
            query_filter=query_filter,
            allow_patterns=allow_patterns,
            deny_patterns=deny_patterns,
        )
        if reason:
            skipped_urls.append(SkippedUrl(url=canon, reason=reason))
            continue
        dedup_map.setdefault(canon, SiteMapEntry(url=canon, depth=0))

    urls_to_visit = sorted(dedup_map)
    if len(urls_to_visit) > max_pages:
        urls_to_visit = urls_to_visit[:max_pages]
    if respect_robots:
        robots = RobotsCache()
        allowed_urls: list[str] = []
        for candidate in urls_to_visit:
            if robots.allowed(candidate):
                allowed_urls.append(candidate)
            else:
                skipped_urls.append(SkippedUrl(url=candidate, reason="robots-disallow"))
        urls_to_visit = allowed_urls

    if verbose:
        console.print(f"[cyan]Extracting pages:[/cyan] {len(urls_to_visit)} URL(s)")

    pages: list[PageDoc] = []
    extraction_skips: list[SkippedUrl] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _extract_one_url,
                url=target_url,
                min_text_chars=min_text_chars,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries=network_retries,
                delay=delay,
                jitter=jitter,
            )
            for target_url in urls_to_visit
        ]
        for fut in as_completed(futures):
            result = fut.result()
            if isinstance(result, tuple):
                failed_url, reason = result
                extraction_skips.append(SkippedUrl(url=failed_url, reason=reason))
                if verbose:
                    console.print(f"[yellow]Skipped:[/yellow] {failed_url} ({reason})")
                continue
            pages.append(result)

    pages.sort(key=lambda item: item.url)
    skipped_urls.extend(extraction_skips)
    sitemap_for_dump = [SiteMapEntry(url=url, depth=dedup_map[url].depth) for url in urls_to_visit]
    sitemap_for_dump.sort(key=lambda item: item.url)

    finished_at = utc_now_iso()
    site_dump = SiteDump(
        start_url=start,
        started_at=started_at,
        finished_at=finished_at,
        crawl_params=CrawlParams(
            max_pages=max_pages,
            delay=delay,
            jitter=jitter,
            concurrency=concurrency,
            respect_robots=respect_robots,
            include_external=include_external,
            query_filter=query_filter,
            allow_patterns=allow_patterns,
            deny_patterns=deny_patterns,
        ),
        discovered_urls_count=len(urls_to_visit),
        visited_urls_count=len(pages),
        skipped_urls=skipped_urls,
        sitemap=sitemap_for_dump,
        pages=pages,
    )

    rendered = _render_site(site_dump, output_format)
    written = _write_output(
        rendered,
        out=out,
        use_stdout=stdout,
        default_name=_default_site_filename(start, finished_at, output_format.lower()),
    )

    if written and verbose:
        console.print(f"[green]Wrote:[/green] {written}")


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
