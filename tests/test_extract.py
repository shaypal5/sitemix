from sitemix.extract import (
    _candidate_from_apiary_payload,
    _find_apiary_subdomain,
    run_extraction_pipeline,
)


def test_find_apiary_subdomain_from_embed_config() -> None:
    html = """
    <div id="api-container"></div>
    <script>
    var embed = new Apiary.Embed({
      "subdomain": "greeninvoice",
      "preferences": {"permalinks": true},
      "element": "#api-container"
    });
    </script>
    """

    assert _find_apiary_subdomain(html) == "greeninvoice"


def test_apiary_payload_candidate_includes_endpoints_and_examples() -> None:
    candidate = _candidate_from_apiary_payload(
        {
            "name": "Example API",
            "urls": {"production": "https://api.example.test/v1/"},
            "description": "<h2>Overview</h2><p>API introduction.</p>",
            "resourceGroups": [
                {
                    "name": "Documents",
                    "description": "<p>Document operations.</p>",
                    "resources": [
                        {
                            "name": "Get Document Types",
                            "uriTemplate": "/documents/types",
                            "actions": [
                                {
                                    "name": "Get Document Types",
                                    "method": "GET",
                                    "uriTemplate": "",
                                    "description": "<p>Returns all document types.</p>",
                                    "examples": [
                                        {
                                            "responses": [
                                                {
                                                    "body": '[{"id": 300, "name": "Invoice"}]'
                                                }
                                            ]
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert candidate.strategy == "apiary_embed_json"
    assert "Example API" in candidate.text
    assert "production: https://api.example.test/v1/" in candidate.text
    assert "GET /documents/types" in candidate.text
    assert "Returns all document types." in candidate.text
    assert '"Invoice"' in candidate.text


def test_apiary_fallback_replaces_short_cookie_text(monkeypatch) -> None:
    html = """
    <p>We use cookies for personalization.</p>
    <script>
    var embed = new Apiary.Embed({"subdomain": "exampleapi"});
    </script>
    """

    monkeypatch.setattr(
        "sitemix.extract._candidate_from_apiary_embed",
        lambda _: _candidate_from_apiary_payload(
            {
                "name": "Embedded API",
                "description": (
                    "<p>Full embedded API documentation with enough detail "
                    "to replace a short cookie notice.</p>"
                ),
                "resourceGroups": [],
            }
        ),
    )

    best, attempts, warnings = run_extraction_pipeline(
        html,
        url="https://example.test/docs",
        min_text_chars=80,
    )

    assert best.strategy == "apiary_embed_json"
    assert "Full embedded API documentation with enough detail" in best.text
    assert any(attempt.strategy == "apiary_embed_json" for attempt in attempts)
    assert not warnings
