from typer.testing import CliRunner

from sitemix import __version__, cli
from sitemix.cli import app


class _FakeConsole:
    def __init__(self, *, is_terminal: bool) -> None:
        self.is_terminal = is_terminal


def test_version_option_prints_version_without_command() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_site_accepts_no_progress_toggle() -> None:
    result = CliRunner().invoke(
        app,
        ["site", "https://example.com/", "--no-progress", "--max-pages", "0"],
    )

    assert result.exit_code != 0
    assert "max_pages must be positive" in result.output


def test_progress_requires_terminal_and_urls(monkeypatch) -> None:
    monkeypatch.setattr(cli, "console", _FakeConsole(is_terminal=True))
    assert cli._should_show_progress(requested=True, total=1)
    assert not cli._should_show_progress(requested=False, total=1)
    assert not cli._should_show_progress(requested=True, total=0)

    monkeypatch.setattr(cli, "console", _FakeConsole(is_terminal=False))
    assert not cli._should_show_progress(requested=True, total=1)
