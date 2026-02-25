# sitemix CLI Spec

## Command: `sitemix page`

```bash
sitemix page URL [OPTIONS]
```

Core options:

- `--format md|json|xml` (default `md`)
- `-o, --out PATH`
- `--stdout`
- `--min-text-chars INTEGER` (default `400`)
- `--connect-timeout FLOAT` (default `10.0`)
- `--read-timeout FLOAT` (default `30.0`)
- `--network-retries INTEGER` (default `2`)
- `-v, --verbose`

Behavior:

- Fetch page HTML with stable user-agent.
- Extract via trafilatura with fallback attempts if short.
- Emit one `PageDoc` in selected format.

## Command: `sitemix site`

```bash
sitemix site START_URL [OPTIONS]
```

Input/discovery:

- `--url URL` (repeatable)
- stdin URL list (one URL per line)
- `--sitemap PATH_OR_URL`
- `--no-sitemap`

Politeness/scope:

- `--max-pages INTEGER` (default `200`, hard cap `500` unless `--i-know-what-im-doing`)
- `--i-know-what-im-doing`
- `--include-external`
- `--ignore-robots`
- `--delay FLOAT` (default `1.0`)
- `--jitter FLOAT` (default `0.3`)
- `--concurrency INTEGER` (default `2`)

Filtering:

- `--allow-pattern PATTERN` (repeatable `fnmatch`)
- `--deny-pattern PATTERN` (repeatable `fnmatch`)
- `--allow-query-heavy`

Output:

- `--format md|json|xml`
- `-o, --out PATH`
- `--stdout`

## Core schema: `PageDoc`

Fields:

- `url`
- `fetched_url`
- `extracted_at` (UTC ISO 8601)
- `title`
- `subtitle`
- `author`
- `date_published`
- `language`
- `text`
- `extraction_attempts[]` (`strategy`, `text_len`, `success`)
- `warnings[]`

## Core schema: `SiteDump`

Fields:

- `start_url`
- `started_at`
- `finished_at`
- `crawl_params`
- `discovered_urls_count`
- `visited_urls_count`
- `skipped_urls[]` (`url`, `reason`)
- `sitemap[]` (`url`, `depth`)
- `pages[]` (`PageDoc`)
