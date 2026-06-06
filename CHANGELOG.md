# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.5] - 2026-06-06

### Fixed
- Use non-boolean release guard output values for GitHub Actions publish
  conditions.

## [0.2.4] - 2026-06-06

### Fixed
- Compare release guard outputs inside GitHub Actions expressions so publish
  steps are not skipped on version-change commits.

## [0.2.3] - 2026-06-06

### Fixed
- Persist release workflow decisions through GitHub Actions environment values
  so publish steps run reliably on version-change commits.

## [0.2.2] - 2026-06-06

### Fixed
- Use explicit release guard strings in PyPI and Homebrew workflows so GitHub
  Actions does not coerce boolean-like outputs before publish steps run.

## [0.2.1] - 2026-06-06

### Fixed
- Fix release workflow guards so version-change commits publish instead of incorrectly running the skip path.

## [0.2.0] - 2026-06-06

### Added
- Add automated PyPI trusted publishing and Homebrew tap update workflows.
- Add a `sitemix site` extraction progress bar with `--progress/--no-progress`.

### Fixed
- Recover documentation from pages that embed Apiary API docs when normal extraction returns only short boilerplate.
- Make `sitemix --version` work without requiring a subcommand.

## [0.1.0] - 2026-02-25

### Added
- Initial repository bootstrap.
- `sitemix page` and `sitemix site` CLI skeleton commands.
- Markdown/JSON/XML formatters for deterministic dump output.
- Basic sitemap parsing, BFS discovery, URL normalization, and politeness controls.
- Test scaffolding and CI workflow.
- Project docs for design/spec/format/politeness/roadmap/tasks.
