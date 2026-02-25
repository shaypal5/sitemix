from sitemix.formatters import page_to_markdown, site_to_markdown
from sitemix.schemas import CrawlParams, ExtractionAttempt, PageDoc, SiteDump, SiteMapEntry


def _sample_page() -> PageDoc:
    return PageDoc(
        url="https://example.com/a",
        fetched_url="https://example.com/a",
        extracted_at="2026-02-25T00:00:00Z",
        title="A title",
        subtitle=None,
        author=None,
        date_published="2025-10-01",
        language="en",
        text="Hello world\n\nSecond paragraph.",
        extraction_attempts=[ExtractionAttempt(strategy="default", text_len=30, success=True)],
        warnings=[],
    )


def test_page_markdown_has_required_delimiters() -> None:
    md = page_to_markdown(_sample_page())
    assert "--- SITEMIX_PAGE ---" in md
    assert "--- SITEMIX_TEXT ---" in md
    assert "--- END_SITEMIX_PAGE ---" in md
    assert "URL: https://example.com/a" in md
    assert "Text-Length: 30" in md


def test_site_markdown_has_header_and_sitemap() -> None:
    page = _sample_page()
    dump = SiteDump(
        start_url="https://example.com",
        started_at="2026-02-25T00:00:00Z",
        finished_at="2026-02-25T00:01:00Z",
        crawl_params=CrawlParams(
            max_pages=200,
            delay=1.0,
            jitter=0.3,
            concurrency=2,
            respect_robots=True,
            include_external=False,
            query_filter=True,
            allow_patterns=[],
            deny_patterns=[],
        ),
        discovered_urls_count=1,
        visited_urls_count=1,
        skipped_urls=[],
        sitemap=[SiteMapEntry(url="https://example.com/a", depth=0)],
        pages=[page],
    )

    md = site_to_markdown(dump)
    assert md.startswith("# sitemix site dump")
    assert "## Sitemap" in md
    assert "- [depth=0] https://example.com/a" in md
    assert md.count("--- SITEMIX_PAGE ---") == 1
