from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

import trafilatura

from sitemix.schemas import ExtractionAttempt, PageDoc
from sitemix.utils import utc_now_iso


@dataclass
class ExtractionCandidate:
    strategy: str
    text: str
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date_published: str | None = None
    language: str | None = None


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _repetition_penalty(text: str) -> int:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 4:
        return 0
    unique = len(set(lines))
    ratio = unique / len(lines)
    if ratio > 0.85:
        return 0
    return int((1 - ratio) * min(len(text), 1200))


def _score(candidate: ExtractionCandidate) -> int:
    text_len = len(candidate.text)
    title_bonus = 200 if candidate.title else 0
    return text_len + title_bonus - _repetition_penalty(candidate.text)


def _signature_filtered_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    sig = inspect.signature(func)
    return {k: v for k, v in kwargs.items() if k in sig.parameters}


def _call_extract(html: str, url: str, strategy_kwargs: dict[str, Any]) -> str:
    kwargs = {
        "url": url,
        "output_format": "txt",
        **strategy_kwargs,
    }
    call_kwargs = _signature_filtered_kwargs(trafilatura.extract, kwargs)
    text = trafilatura.extract(html, **call_kwargs)
    return _normalize_text(text)


def _call_bare_extraction(
    html: str, url: str, strategy_kwargs: dict[str, Any]
) -> dict[str, Any] | None:
    bare = getattr(trafilatura, "bare_extraction", None)
    if bare is None:
        return None
    kwargs = {
        "url": url,
        **strategy_kwargs,
    }
    call_kwargs = _signature_filtered_kwargs(bare, kwargs)
    result = bare(html, **call_kwargs)
    if result is None:
        return None
    if isinstance(result, dict):
        return result
    try:
        return dict(result)
    except Exception:
        return None


def _candidate_from_bare(strategy: str, data: dict[str, Any]) -> ExtractionCandidate:
    text = _normalize_text(str(data.get("text") or data.get("raw_text") or ""))
    title = data.get("title")
    subtitle = data.get("description") or data.get("excerpt")
    author = data.get("author")
    date_published = data.get("date")
    language = data.get("language")
    return ExtractionCandidate(
        strategy=strategy,
        text=text,
        title=title,
        subtitle=subtitle,
        author=author,
        date_published=date_published,
        language=language,
    )


def run_extraction_pipeline(
    html: str,
    *,
    url: str,
    min_text_chars: int = 400,
) -> tuple[ExtractionCandidate, list[ExtractionAttempt], list[str]]:
    strategies: list[tuple[str, dict[str, Any]]] = [
        ("default", {}),
        ("favor_recall", {"favor_precision": False, "favor_recall": True}),
        ("include_tables", {"include_tables": True}),
        ("include_links", {"include_links": True}),
        ("include_comments", {"include_comments": True}),
        (
            "relaxed_combo",
            {
                "favor_precision": False,
                "favor_recall": True,
                "include_comments": True,
                "include_links": True,
                "include_tables": True,
            },
        ),
    ]

    attempts: list[ExtractionAttempt] = []
    candidates: list[ExtractionCandidate] = []
    bare_candidate: ExtractionCandidate | None = None

    for strategy, kwargs in strategies:
        text = ""
        try:
            text = _call_extract(html, url, kwargs)
        except Exception:
            text = ""

        attempt = ExtractionAttempt(strategy=strategy, text_len=len(text), success=bool(text))
        attempts.append(attempt)
        if text:
            candidates.append(ExtractionCandidate(strategy=strategy, text=text))

        if len(text) >= min_text_chars and strategy == "default":
            break

    try:
        bare_result = _call_bare_extraction(
            html, url, {"favor_precision": False, "favor_recall": True}
        )
    except Exception:
        bare_result = None
    if bare_result:
        bare_candidate = _candidate_from_bare("bare_extraction", bare_result)
        attempts.append(
            ExtractionAttempt(
                strategy="bare_extraction",
                text_len=len(bare_candidate.text),
                success=bool(bare_candidate.text),
            )
        )
        if bare_candidate.text:
            candidates.append(bare_candidate)

    if not candidates:
        return (
            ExtractionCandidate(strategy="none", text=""),
            attempts,
            ["No extraction strategy returned text."],
        )

    best = max(candidates, key=_score)
    if bare_candidate:
        if not best.title and bare_candidate.title:
            best.title = bare_candidate.title
        if not best.subtitle and bare_candidate.subtitle:
            best.subtitle = bare_candidate.subtitle
        if not best.author and bare_candidate.author:
            best.author = bare_candidate.author
        if not best.date_published and bare_candidate.date_published:
            best.date_published = bare_candidate.date_published
        if not best.language and bare_candidate.language:
            best.language = bare_candidate.language
    warnings: list[str] = []
    if len(best.text) < min_text_chars:
        warnings.append(
            f"Extracted text length ({len(best.text)}) is below threshold ({min_text_chars})."
        )

    return best, attempts, warnings


def build_page_doc(
    *,
    url: str,
    fetched_url: str,
    html: str,
    min_text_chars: int,
) -> PageDoc:
    best, attempts, warnings = run_extraction_pipeline(
        html, url=fetched_url or url, min_text_chars=min_text_chars
    )
    return PageDoc(
        url=url,
        fetched_url=fetched_url,
        extracted_at=utc_now_iso(),
        title=best.title,
        subtitle=best.subtitle,
        author=best.author,
        date_published=best.date_published,
        language=best.language,
        text=best.text,
        extraction_attempts=attempts,
        warnings=warnings,
    )
