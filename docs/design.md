# sitemix Design

## Goals

- Wrap trafilatura for extraction, with minimal custom logic.
- Provide two CLI entry points: `page` and `site`.
- Produce deterministic outputs for downstream RAG ingestion.
- Stay polite by default (robots, delay, low concurrency).

## Architecture

Modules under `src/sitemix`:

- `cli.py`: Typer app and command orchestration.
- `http.py`: network client with user-agent, timeouts, retries, delay+jitter helper.
- `extract.py`: extraction fallback pipeline and strategy scoring.
- `crawl.py`: URL canonicalization, sitemap parsing, BFS discovery, robots checks, skip heuristics.
- `formatters.py`: Markdown/JSON/XML deterministic rendering.
- `schemas.py`: Pydantic v2 models (`PageDoc`, `SiteDump`, metadata models).
- `utils.py`: timestamps and filename slugs.

## Key flows

### `sitemix page`

1. Canonicalize URL.
2. Fetch with `requests` using stable user-agent.
3. Run extraction pipeline:
   - trafilatura default extract
   - fallback toggle variants when short
   - optional `bare_extraction` fallback when available
   - score and select best candidate
4. Build `PageDoc` and render to selected format.
5. Write to file or stdout.

### `sitemix site`

1. Build URL seed set from: start URL, optional `--url`, stdin lines.
2. Discovery preference:
   - user-provided `--sitemap`
   - probe `/sitemap.xml` unless `--no-sitemap`
   - fallback to BFS crawl
3. Canonicalize + dedupe + filter by heuristics/patterns.
4. Extract pages concurrently (`ThreadPoolExecutor`, default 2 workers).
5. Build `SiteDump` and render to selected format.

## Decisions

- Minimal dependencies (requests, typer, pydantic, rich, trafilatura).
- Stdlib XML and HTML parsing for sitemap/link discovery.
- Deterministic output via sorted URL sets and stable serialization.
- Fail-open behavior for robots fetch failures (but enforce robots rules when readable).
