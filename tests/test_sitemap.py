from sitemix.crawl import parse_sitemap_xml, parse_url_list_text

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/docs</loc></url>
</urlset>
"""


SITEMAP_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-a.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-b.xml</loc></sitemap>
</sitemapindex>
"""


def test_parse_sitemap_xml_urlset() -> None:
    urls = parse_sitemap_xml(SITEMAP_XML)
    assert urls == ["https://example.com/", "https://example.com/docs"]


def test_parse_sitemap_xml_index_fallback() -> None:
    urls = parse_sitemap_xml(SITEMAP_INDEX_XML)
    assert urls == [
        "https://example.com/sitemap-a.xml",
        "https://example.com/sitemap-b.xml",
    ]


def test_parse_url_list_text() -> None:
    text = """
# comment
https://example.com/a

https://example.com/b
"""
    urls = parse_url_list_text(text)
    assert urls == ["https://example.com/a", "https://example.com/b"]
