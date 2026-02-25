from sitemix.crawl import canonicalize_url, is_query_heavy, should_skip_url


def test_canonicalize_url_normalizes_scheme_host_path_query_and_fragment() -> None:
    got = canonicalize_url("HTTPS://Example.COM/a//b/?b=2&a=1#fragment")
    assert got == "https://example.com/a/b?a=1&b=2"


def test_canonicalize_url_resolves_relative() -> None:
    got = canonicalize_url("../docs/", base_url="https://example.com/blog/posts/")
    assert got == "https://example.com/blog/docs"


def test_query_heavy_detection() -> None:
    assert is_query_heavy("https://example.com/search?q=a&lang=en&page=2&sort=desc") is True
    assert is_query_heavy("https://example.com/about") is False


def test_should_skip_url_patterns_and_binary() -> None:
    assert (
        should_skip_url(
            "https://example.com/file.pdf",
            query_filter=True,
            allow_patterns=[],
            deny_patterns=[],
        )
        == "binary-extension"
    )
    assert (
        should_skip_url(
            "https://example.com/blog/post",
            query_filter=True,
            allow_patterns=["*example.com/blog/*"],
            deny_patterns=[],
        )
        is None
    )
    assert (
        should_skip_url(
            "https://example.com/private/post",
            query_filter=True,
            allow_patterns=[],
            deny_patterns=["*example.com/private/*"],
        )
        == "deny-pattern"
    )
