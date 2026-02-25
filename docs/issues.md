# Proposed GitHub Issues

## MVP

### 1) Stabilize extraction fallback scoring

Description:
Refine heuristics for selecting the best extraction candidate and reduce false positives on boilerplate-heavy pages.

Acceptance criteria:
- Candidate scoring documented with tests.
- At least 5 mixed-content fixtures validated.
- Repetitive-content penalty tuned with baseline snapshots.

### 2) Improve sitemap index handling

Description:
Support recursive sitemap index traversal with safe depth and URL limits.

Acceptance criteria:
- Sitemap index recursion implemented.
- Cycles and duplicates safely handled.
- Unit tests for nested sitemap indexes.

### 3) Add richer crawl skip reporting

Description:
Expand skip reasons and emit summary counts by reason.

Acceptance criteria:
- Skip reasons normalized in schema/docs.
- JSON/XML/Markdown include aggregated reason counts.
- Tests cover at least 6 skip categories.

### 4) Add CLI integration tests

Description:
Add command-level tests validating output files and exit codes.

Acceptance criteria:
- `sitemix page` and `sitemix site` integration tests added.
- HTTP mocked with `responses`.
- Tests verify deterministic output structure.

### 5) Release automation docs and scripts

Description:
Provide scripted release checklist for PyPI and Homebrew tap updates.

Acceptance criteria:
- Release script skeleton checked in.
- README links to release workflow docs.
- Dry-run command list validated by maintainers.

## Post-MVP

### 6) Optional HTTP cache

Description:
Add local cache support to reduce repeated fetches and improve crawl speed.

Acceptance criteria:
- Cache opt-in flag added.
- Cache TTL configurable.
- Tests verify cache hit/miss behavior.

### 7) Content-based duplicate suppression

Description:
Detect near-identical pages and collapse duplicates in site dump output.

Acceptance criteria:
- Configurable similarity threshold.
- Duplicate map emitted in run metadata.
- Tests for duplicate and near-duplicate pages.

### 8) Respect crawl-delay directive where present

Description:
Augment robots handling to account for crawl-delay hints when available.

Acceptance criteria:
- Crawl-delay parsed when present.
- Effective delay uses max(user_delay, robots_delay).
- Behavior documented in politeness docs.
