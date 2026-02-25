from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

from sitemix import __version__
from sitemix.schemas import DumpEnvelope, PageDoc, SiteDump


def _none_to_empty(value: str | None) -> str:
    return value or ""


def _attempts_markdown(page: PageDoc) -> str:
    if not page.extraction_attempts:
        return "-"
    chunks = []
    for attempt in page.extraction_attempts:
        success = str(attempt.success).lower()
        chunks.append(
            f"  - strategy={attempt.strategy}; text_len={attempt.text_len}; success={success}"
        )
    return "\n".join(chunks)


def _warnings_markdown(page: PageDoc) -> str:
    if not page.warnings:
        return "-"
    return "\n".join(f"  - {warning}" for warning in page.warnings)


def page_to_markdown(page: PageDoc, include_top_header: bool = True) -> str:
    lines: list[str] = []
    if include_top_header:
        lines.extend(
            [
                "# sitemix page dump",
                f"Source URL: {page.url}",
                f"Extracted at: {page.extracted_at}",
                "",
            ]
        )

    lines.extend(
        [
            "--- SITEMIX_PAGE ---",
            f"URL: {_none_to_empty(page.url)}",
            f"Fetched-URL: {_none_to_empty(page.fetched_url)}",
            f"Title: {_none_to_empty(page.title)}",
            f"Subtitle: {_none_to_empty(page.subtitle)}",
            f"Language: {_none_to_empty(page.language)}",
            f"Published: {_none_to_empty(page.date_published)}",
            f"Extracted-At: {_none_to_empty(page.extracted_at)}",
            f"Text-Length: {len(page.text)}",
            "Attempts:",
            _attempts_markdown(page),
            "Warnings:",
            _warnings_markdown(page),
            "--- SITEMIX_TEXT ---",
            page.text,
            "--- END_SITEMIX_PAGE ---",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def site_to_markdown(site_dump: SiteDump) -> str:
    lines: list[str] = [
        "# sitemix site dump",
        f"Start URL: {site_dump.start_url}",
        f"Extracted at: {site_dump.finished_at}",
        "Params:",
        f"  max_pages: {site_dump.crawl_params.max_pages}",
        f"  delay: {site_dump.crawl_params.delay}",
        f"  jitter: {site_dump.crawl_params.jitter}",
        f"  concurrency: {site_dump.crawl_params.concurrency}",
        f"  respect_robots: {str(site_dump.crawl_params.respect_robots).lower()}",
        f"  include_external: {str(site_dump.crawl_params.include_external).lower()}",
        f"  query_filter: {str(site_dump.crawl_params.query_filter).lower()}",
        "## Sitemap",
    ]

    if not site_dump.sitemap:
        lines.append("- (empty)")
    else:
        for entry in site_dump.sitemap:
            lines.append(f"- [depth={entry.depth}] {entry.url}")

    lines.append("")
    for page in site_dump.pages:
        lines.append(page_to_markdown(page, include_top_header=False).rstrip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def envelope_to_json(run_data: dict[str, Any], pages: list[PageDoc]) -> str:
    envelope = DumpEnvelope(
        tool={"name": "sitemix", "version": __version__},
        run=run_data,
        pages=pages,
    )
    return json.dumps(envelope.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def site_to_json(site_dump: SiteDump) -> str:
    run_data = {
        "mode": "site",
        "start_url": site_dump.start_url,
        "started_at": site_dump.started_at,
        "finished_at": site_dump.finished_at,
        "crawl_params": site_dump.crawl_params.model_dump(mode="json"),
        "discovered_urls_count": site_dump.discovered_urls_count,
        "visited_urls_count": site_dump.visited_urls_count,
        "skipped_urls": [item.model_dump(mode="json") for item in site_dump.skipped_urls],
        "sitemap": [item.model_dump(mode="json") for item in site_dump.sitemap],
    }
    return envelope_to_json(run_data, site_dump.pages)


def page_to_json(page: PageDoc) -> str:
    run_data = {
        "mode": "page",
        "source_url": page.url,
        "extracted_at": page.extracted_at,
    }
    return envelope_to_json(run_data, [page])


def _append_text_element(parent: ET.Element, key: str, value: str | None) -> None:
    child = ET.SubElement(parent, key)
    child.text = value or ""


def page_to_xml(page: PageDoc) -> str:
    root = ET.Element("sitemixDump")
    tool = ET.SubElement(root, "tool")
    _append_text_element(tool, "name", "sitemix")
    _append_text_element(tool, "version", __version__)

    run = ET.SubElement(root, "run")
    _append_text_element(run, "mode", "page")
    _append_text_element(run, "source_url", page.url)
    _append_text_element(run, "extracted_at", page.extracted_at)

    pages_elem = ET.SubElement(root, "pages")
    pages_elem.append(_page_doc_to_xml(page))

    return ET.tostring(root, encoding="unicode") + "\n"


def _page_doc_to_xml(page: PageDoc) -> ET.Element:
    elem = ET.Element("page")
    _append_text_element(elem, "url", page.url)
    _append_text_element(elem, "fetched_url", page.fetched_url)
    _append_text_element(elem, "extracted_at", page.extracted_at)
    _append_text_element(elem, "title", page.title)
    _append_text_element(elem, "subtitle", page.subtitle)
    _append_text_element(elem, "author", page.author)
    _append_text_element(elem, "date_published", page.date_published)
    _append_text_element(elem, "language", page.language)
    _append_text_element(elem, "text", page.text)

    attempts_elem = ET.SubElement(elem, "extraction_attempts")
    for attempt in page.extraction_attempts:
        attempt_elem = ET.SubElement(attempts_elem, "attempt")
        _append_text_element(attempt_elem, "strategy", attempt.strategy)
        _append_text_element(attempt_elem, "text_len", str(attempt.text_len))
        _append_text_element(attempt_elem, "success", str(attempt.success).lower())

    warnings_elem = ET.SubElement(elem, "warnings")
    for warning in page.warnings:
        _append_text_element(warnings_elem, "warning", warning)

    return elem


def site_to_xml(site_dump: SiteDump) -> str:
    root = ET.Element("sitemixDump")

    tool = ET.SubElement(root, "tool")
    _append_text_element(tool, "name", "sitemix")
    _append_text_element(tool, "version", __version__)

    run = ET.SubElement(root, "run")
    _append_text_element(run, "mode", "site")
    _append_text_element(run, "start_url", site_dump.start_url)
    _append_text_element(run, "started_at", site_dump.started_at)
    _append_text_element(run, "finished_at", site_dump.finished_at)

    crawl = ET.SubElement(run, "crawl_params")
    for key, value in site_dump.crawl_params.model_dump(mode="json").items():
        _append_text_element(crawl, key, str(value))

    _append_text_element(run, "discovered_urls_count", str(site_dump.discovered_urls_count))
    _append_text_element(run, "visited_urls_count", str(site_dump.visited_urls_count))

    skipped_elem = ET.SubElement(run, "skipped_urls")
    for skipped in site_dump.skipped_urls:
        skipped_item = ET.SubElement(skipped_elem, "skipped")
        _append_text_element(skipped_item, "url", skipped.url)
        _append_text_element(skipped_item, "reason", skipped.reason)

    sitemap_elem = ET.SubElement(run, "sitemap")
    for entry in site_dump.sitemap:
        entry_elem = ET.SubElement(sitemap_elem, "entry")
        _append_text_element(entry_elem, "url", entry.url)
        _append_text_element(entry_elem, "depth", str(entry.depth))

    pages_elem = ET.SubElement(root, "pages")
    for page in site_dump.pages:
        pages_elem.append(_page_doc_to_xml(page))

    return ET.tostring(root, encoding="unicode") + "\n"
