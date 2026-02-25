# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Local checks

```bash
ruff check .
pytest
```

## Coding guidelines

- Python 3.10+
- Keep dependencies minimal
- Prefer stdlib where practical
- Add tests for behavior changes
- Keep CLI output and dump format stable

## Pull request checklist

- [ ] Tests added/updated
- [ ] `ruff check .` clean
- [ ] `pytest` passing
- [ ] Docs updated (`README` and relevant `docs/*.md`)
- [ ] Changelog entry in `Unreleased`
