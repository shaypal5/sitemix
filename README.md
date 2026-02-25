# sitemix

`sitemix` is a small, opinionated CLI that turns a webpage or a small website into a single LLM-oriented dump file.

Core extraction is powered by [trafilatura](https://github.com/adbar/trafilatura).

## License and dependency note

- `sitemix` code: MIT (see `LICENSE`)
- `trafilatura`: Apache 2.0
- `sitemix` is an opinionated wrapper around trafilatura; MIT applies only to the `sitemix` codebase.

## What it does

- `sitemix page URL`: extract one page into Markdown (default), JSON, or XML.
- `sitemix site URL`: crawl a small site politely and produce one unified dump file.
- Outputs are deterministic and structured for RAG/LLM ingestion.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
sitemix --help
```

`pipx` usage:

```bash
pipx install sitemix
```

## CLI examples

Single page:

```bash
sitemix page "https://example.com/post" \
  --format md \
  --min-text-chars 400
```

Site crawl:

```bash
sitemix site "https://example.com" \
  --max-pages 200 \
  --delay 1.0 \
  --concurrency 2 \
  --format md
```

URLs from stdin:

```bash
printf '%s\n' "https://example.com/a" "https://example.com/b" | sitemix site "https://example.com" --no-sitemap
```

Sitemap path or URL:

```bash
sitemix site "https://example.com" --sitemap ./urls.txt
sitemix site "https://example.com" --sitemap https://example.com/sitemap.xml
```

Write to stdout:

```bash
sitemix page "https://example.com" --stdout
```

## Politeness defaults

- Robots respected by default (`--ignore-robots` to override)
- Delay + jitter between requests
- Same-host crawl by default (`--include-external` to override)
- Query-heavy URLs skipped by default (`--allow-query-heavy` to override)
- Basic binary URL skipping

See [`docs/politeness.md`](docs/politeness.md).

## Output formats

- Markdown: strict delimiters for each page (`--- SITEMIX_PAGE ---`, `--- SITEMIX_TEXT ---`, `--- END_SITEMIX_PAGE ---`)
- JSON: single object with tool/run metadata and pages
- XML: single `<sitemixDump>` root

See [`docs/format.md`](docs/format.md).

## Development commands

```bash
pip install -e .[dev]
ruff check .
pytest
```

## Homebrew distribution

A formula stub is included at `packaging/homebrew/sitemix.rb`.

Typical release flow:

1. Tag and publish a GitHub release (`vX.Y.Z`) with source tarball.
2. Compute sha256 for the tarball.
3. Update formula `url`, `sha256`, and `version`.
4. Commit formula to your tap repository (`homebrew-<tap>`).
5. Users install with:

```bash
brew tap <org>/tap
brew install sitemix
```

## Limitations

- Not a massive web crawler; intended for small sites (hundreds of pages, not millions).
- Extraction quality depends on source HTML and trafilatura behavior.
- JS-heavy pages without server-rendered content may produce short output.

## Ethics

Use only where you have legal and ethical right to fetch and process content. Respect robots, rate limits, and site terms.
