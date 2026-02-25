import pytest

from sitemix.http import HttpClient

responses = pytest.importorskip("responses")


@responses.activate
def test_fetch_text_uses_stable_user_agent_and_follows_redirects() -> None:
    responses.add(
        responses.GET,
        "https://example.com/start",
        status=302,
        headers={"Location": "https://example.com/final"},
    )
    responses.add(
        responses.GET,
        "https://example.com/final",
        status=200,
        body="<html><body>Hello</body></html>",
        headers={"Content-Type": "text/html"},
    )

    with HttpClient(retries=0) as client:
        result = client.fetch_text("https://example.com/start")

    assert result.fetched_url == "https://example.com/final"
    assert "sitemix/" in responses.calls[-1].request.headers.get("User-Agent", "")
    assert "Hello" in result.text
