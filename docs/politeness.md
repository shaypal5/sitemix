# Politeness and Safety

## Default behavior

- Respect `robots.txt` unless `--ignore-robots` is set.
- Use low default concurrency (`2`).
- Delay requests (`1.0s`) with jitter (`0.3s`).
- Stay on same hostname unless `--include-external`.

## User-Agent

`requests` are sent with:

`sitemix/<version> (+https://github.com/<org>/sitemix)`

## URL filtering

- Skip likely binary/document links by extension.
- Skip query-heavy URLs by default.
- Support `--allow-pattern` and `--deny-pattern` to tune scope.

## Caching

Current MVP does not persist cache across runs.

Possible future behavior:

- Optional local HTTP cache with expiration.
- ETag/Last-Modified conditional requests.
