# MVP Development Plan (1-2 days)

1. Project scaffold and packaging (1.5h)
- Create src/docs/tests/github structure.
- Configure `pyproject.toml`, entrypoint, lint/test tooling.

2. Core models and formatters (2h)
- Define Pydantic schemas.
- Implement deterministic Markdown/JSON/XML serializers.

3. Page pipeline (3h)
- Build HTTP client with retries/timeouts/user-agent.
- Implement trafilatura extraction attempts + scoring.
- Add `sitemix page` command and output writer.

4. Site discovery and crawl (4h)
- URL canonicalization/dedupe/filtering.
- Sitemap XML/text support and BFS fallback.
- Robots and politeness controls.
- Add `sitemix site` command.

5. Tests and CI (2.5h)
- Unit tests for canonicalization, sitemap parsing, formatting.
- Add one HTTP mock test with `responses`.
- Add GitHub Actions workflow.

6. Docs and release stubs (2h)
- README + docs (`design/spec/format/politeness/roadmap/issues`).
- Homebrew formula stub and release instructions.
- Governance files (`CONTRIBUTING`, `SECURITY`, CoC, changelog).
