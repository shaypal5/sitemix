You are GPT-5.3-codex acting as a senior Python OSS maintainer. Bootstrap a new repo for a Python CLI tool named “sitemix”.

GOAL
Create a pip-installable and brew-installable CLI that turns a single webpage or a small website into a single LLM-oriented dump file (Markdown default; JSON/XML also supported). “sitemix” is an opinionated wrapper around trafilatura (core extraction), with only minimal new logic where truly required. It is NOT a massive scraper; it targets small sites (<= a few hundred pages).

KEY REQUIREMENTS
1) Two CLI commands:
   - `sitemix page "https://www.site.com/somepage"`
     Produces an LLM-oriented output file in one of: markdown (default), json, xml.
     Output must include keyed values: title, subtitle (if detectable), source URL, extraction timestamp (ISO 8601), language (if detectable), and extracted text content.
     If extraction is “too small” (< threshold chars, default ~400), retry with alternative strategies and provide metadata about attempts.
   - `sitemix site "https://www.site.com/"`
     Also accept:
       a) a list of URLs (via repeated flags or stdin),
       b) a path to a sitemap file (txt list of URLs; also support sitemap.xml if feasible),
     Crawls the site thoroughly but politely with limits:
       - max_pages default 200 (configurable, hard cap 500 unless user overrides with --i-know-what-im-doing)
       - stay within same hostname unless --include-external
       - delay between requests (default 1.0s) + jitter, concurrency default 2 (configurable)
       - respect robots.txt by default (allow override --ignore-robots)
     Produces a single file containing a site map + page sections with clear boundaries.
     Each page section must follow the same schema as `page`.
     Deduplicate URLs (canonicalize, drop fragments, normalize trailing slash).
     Basic heuristics to avoid junk: skip binary downloads, skip query-heavy URLs by default, allow user allowlist/denylist patterns.

2) Implementation constraints:
   - Use trafilatura as core extraction; do not reinvent extraction.
   - Use standard libs whenever possible; minimal deps beyond trafilatura.
   - Python 3.10+.
   - Use Typer for CLI.
   - Use Pydantic v2 for schemas and validation.
   - Use Rich for CLI progress/logging (optional but preferred).
   - Provide robust retry/fallback extraction strategies only when output is too small.

3) Output formats:
   - Markdown (default): LLM-readable with strict boundaries.
     Include a top “meta header” per page with fields and a delimiter line.
     Provide a global header with crawl parameters and sitemap.
   - JSON: single JSON object with run metadata + list of page objects.
   - XML: single XML root with run metadata + page entries.
   Ensure outputs are deterministic and stable for RAG ingestion.

4) Packaging & distribution:
   - MIT License for sitemix code.
   - README must clearly state: depends on trafilatura (Apache 2.0); sitemix is an opinionated wrapper; MIT applies only to sitemix.
   - pyproject.toml with console_script entrypoint `sitemix`.
   - Add Homebrew formula stub under `packaging/homebrew/sitemix.rb` and document release steps; also include `brew tap` guidance.
   - Provide `pipx install sitemix` friendly usage.

5) Repository bootstrap deliverables:
   Create the full repo structure with:
   - `README.md` (overview, quickstart, examples, limitations, ethics/politeness)
   - `LICENSE` (MIT)
   - `pyproject.toml` (packaging, deps, entrypoint)
   - `src/sitemix/...` implementation skeleton
   - `docs/` with design + spec docs
   - `tests/` with pytest scaffolding + a few unit tests (URL canonicalization, sitemap parsing, markdown formatting)
   - `.github/workflows/ci.yml` (lint + tests)
   - `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
   - `CHANGELOG.md` (Keep a Changelog)
   - Issue templates + a set of pre-created GitHub issues in `docs/issues.md` (since you can’t create issues directly)
   - A “task breakdown” document for an MVP within ~1–2 days of coding.

Also generate:
- `docs/design.md`: architecture, modules, key flows, decisions.
- `docs/spec.md`: CLI interface, flags, output schemas, examples.
- `docs/format.md`: exact Markdown format with delimiters and field names; JSON schema; XML schema.
- `docs/politeness.md`: robots, rate limiting, user agent, caching behavior.
- `docs/roadmap.md`: MVP vs v0.2+.

PRODUCT BEHAVIOR SPEC (MUST IMPLEMENT)
A) `sitemix page`:
- Fetch HTML (requests) with a stable User-Agent “sitemix/<version> (+https://github.com/<org>/sitemix)”.
- Run trafilatura extraction:
  1) try default extraction (`trafilatura.extract`)
  2) if too short:
     - try `favor_precision=False`/`favor_recall=True` toggles as available
     - try with/without `include_comments`, `include_tables`, `include_links` toggles as available
     - try `trafilatura.bare_extraction` if present and map fields
  3) Choose best candidate by score:
     - primary: length of clean text
     - secondary: presence of title
     - penalty: extremely repetitive/boilerplate-like text (simple heuristic)
- Return an object `PageDoc` with:
  - url
  - fetched_url (after redirects)
  - extracted_at (UTC ISO string)
  - title
  - subtitle (optional; if not reliable, leave null)
  - author (optional)
  - date_published (optional if trafilatura provides)
  - language (optional)
  - text
  - extraction_attempts: list of attempt metadata (strategy name, text_len, success bool)
  - warnings: list of strings
- Write output to:
  - default: `<slug>.md` in cwd unless `-o/--out` specified
  - Support `--format md|json|xml` (default md)
  - Support `--stdout`

B) `sitemix site`:
- URL discovery:
  - Prefer sitemap.xml if present at `/sitemap.xml` unless user provides `--no-sitemap`.
  - Accept `--sitemap PATH_OR_URL` for sitemap.xml or txt.
  - If no sitemap: do polite BFS crawl within domain:
    - fetch page, extract links (use `trafilatura.sitemaps` if helpful; otherwise lxml/bs4 ONLY if needed—prefer stdlib html parser if possible).
    - canonicalize and queue.
    - stop at max_pages.
- For each URL, run the same extraction pipeline as `page`.
- Build a site-level object `SiteDump` with:
  - start_url
  - started_at, finished_at
  - crawl_params (max_pages, delay, concurrency, respect_robots, include_external, etc.)
  - discovered_urls count + visited_urls count + skipped_urls list with reasons
  - sitemap: adjacency list or list of URLs with depth
  - pages: list[PageDoc]
- Output is a single file similarly named `site_<host>_<date>.md` unless specified.

MARKDOWN FORMAT (STRICT)
Global header:
- `# sitemix site dump`
- `Start URL: ...`
- `Extracted at: ...`
- `Params: ...` (YAML-ish block ok)
- `## Sitemap` (bulleted list of URLs, optionally with depth)
Then:
For each page, use a delimiter line exactly:
`--- SITEMIX_PAGE ---`
Then a metadata block:

URL: …
Fetched-URL: …
Title: …
Subtitle: …
Language: …
Published: …
Extracted-At: …
Text-Length: …
Attempts: 
Warnings: …

Then:
`--- SITEMIX_TEXT ---`
Then the extracted text as plain paragraphs.
End with:
`--- END_SITEMIX_PAGE ---`

For `sitemix page`, same format but without sitemap header.

JSON FORMAT
Single object:
{
  "tool": {"name":"sitemix","version":"x.y.z"},
  "run": {...},
  "pages": [PageDoc...]
}
XML FORMAT
Root `<sitemixDump>` with `<tool>`, `<run>`, `<pages>`.

ENGINEERING / QUALITY
- Provide clear error messages; nonzero exit codes on failure.
- Timeouts: connect/read default 10/30s; configurable.
- Retries: network retries separate from extraction retries.
- Logging: quiet by default, `-v/--verbose` adds detail.
- Tests: mock HTTP via `responses` or `pytest-httpserver` (pick minimal dependency).
- Lint/format: ruff.
- Provide `make`-like commands in README (or `justfile` optional).
- Keep code readable; type hints; minimal comments.

BOOTSTRAP TASK
Now produce:
1) Full repository tree (folders/files) you will create.
2) Contents of each required file (write the actual text/code for each file).
3) A set of “issues” written into `docs/issues.md` with titles + descriptions + acceptance criteria, grouped into MVP / Post-MVP.
4) A “development plan” in `docs/tasks.md` with ordered steps and rough time estimates (short bullets, no fluff).
5) Ensure `sitemix page` and `sitemix site` skeleton commands run (even if some TODOs remain), with minimal functional extraction for MVP.

IMPORTANT
- Do not implement advanced scraping; keep it minimal and polite.
- Do not add unnecessary dependencies.
- Ensure the tool can be installed with `pip install -e .` and `sitemix --help` works.
- Keep everything self-contained and ready for the next coding phase.

Proceed to generate the repo now.
