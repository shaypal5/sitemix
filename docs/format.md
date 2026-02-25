# Output Format Contract

## Markdown

### Site dump

Header must include:

- `# sitemix site dump`
- `Start URL: ...`
- `Extracted at: ...`
- `Params:` block (YAML-ish key/value lines)
- `## Sitemap` with bullet URLs (`- [depth=N] URL`)

Then each page block:

```text
--- SITEMIX_PAGE ---
URL: ...
Fetched-URL: ...
Title: ...
Subtitle: ...
Language: ...
Published: ...
Extracted-At: ...
Text-Length: ...
Attempts:
  - strategy=...; text_len=...; success=true|false
Warnings:
  - ...
--- SITEMIX_TEXT ---
<plain extracted text>
--- END_SITEMIX_PAGE ---
```

### Page dump

Same page block format, prefixed with:

- `# sitemix page dump`
- `Source URL: ...`
- `Extracted at: ...`

## JSON

Single object:

```json
{
  "tool": {"name": "sitemix", "version": "x.y.z"},
  "run": {...},
  "pages": [PageDoc...]
}
```

Constraints:

- Stable key ordering (`sort_keys=true`)
- UTF-8 text
- One trailing newline

## XML

Single root:

```xml
<sitemixDump>
  <tool>...</tool>
  <run>...</run>
  <pages>
    <page>...</page>
  </pages>
</sitemixDump>
```

Each `<page>` includes metadata fields, `extraction_attempts`, `warnings`, and `text`.
