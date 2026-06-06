from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

import requests
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


class _TextHTMLParser(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    SKIP_TAGS = {"script", "style", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return _normalize_text(" ".join(self._parts))


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _html_to_text(html: str | None) -> str:
    if not html:
        return ""
    parser = _TextHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return _normalize_text(re.sub(r"<[^>]+>", " ", html))
    return parser.text()


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


def _extract_balanced_object(text: str, start_index: int) -> str | None:
    object_start = text.find("{", start_index)
    if object_start == -1:
        return None

    depth = 0
    quote: str | None = None
    escape = False
    for index in range(object_start, len(text)):
        char = text[index]
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[object_start : index + 1]

    return None


def _find_apiary_subdomain(html: str) -> str | None:
    embed_index = html.find("Apiary.Embed")
    if embed_index == -1:
        return None

    config = _extract_balanced_object(html, embed_index)
    if config:
        try:
            payload = json.loads(config)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("subdomain"), str):
            return payload["subdomain"]

        match = re.search(r"""["']?subdomain["']?\s*:\s*["']([^"']+)["']""", config)
        if match:
            return match.group(1)

    return None


def _first_string(value: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(value, dict):
        return ""
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""


def _append_text_block(lines: list[str], html: str | None) -> None:
    text = _html_to_text(html)
    if text:
        lines.append(text)


def _append_example_blocks(lines: list[str], examples: Any) -> None:
    if not isinstance(examples, list):
        return
    for example in examples:
        if not isinstance(example, dict):
            continue
        for label, key in (("Request", "requests"), ("Response", "responses")):
            entries = example.get(key)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                body = _first_string(entry, ("body", "schema"))
                if body:
                    lines.append(f"{label} example:")
                    lines.append(body)


def _candidate_from_apiary_payload(payload: dict[str, Any]) -> ExtractionCandidate:
    lines: list[str] = []
    title = _first_string(payload, ("name", "subdomain"))
    if title:
        lines.append(title)

    urls = payload.get("urls")
    if isinstance(urls, dict):
        for label, url in urls.items():
            if isinstance(url, str) and url:
                lines.append(f"{label}: {url}")

    _append_text_block(lines, _first_string(payload, ("description",)))

    resource_groups = payload.get("resourceGroups")
    if isinstance(resource_groups, list):
        for group in resource_groups:
            if not isinstance(group, dict):
                continue
            group_name = _first_string(group, ("name",))
            if group_name:
                lines.append(f"\n# {group_name}")
            _append_text_block(lines, _first_string(group, ("description",)))

            resources = group.get("resources")
            if not isinstance(resources, list):
                continue
            for resource in resources:
                if not isinstance(resource, dict):
                    continue
                resource_name = _first_string(resource, ("name",))
                resource_uri = _first_string(resource, ("uriTemplate",))
                if resource_name or resource_uri:
                    lines.append(f"\n## {resource_name}".rstrip())
                    if resource_uri:
                        lines.append(resource_uri)
                _append_text_block(lines, _first_string(resource, ("description",)))

                actions = resource.get("actions")
                if not isinstance(actions, list):
                    continue
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    method = _first_string(action, ("method",))
                    action_uri = _first_string(action, ("uriTemplate",))
                    action_name = _first_string(action, ("name",))
                    endpoint = " ".join(
                        part for part in (method, resource_uri + action_uri) if part
                    )
                    if action_name or endpoint:
                        lines.append(f"\n### {action_name}".rstrip())
                        if endpoint:
                            lines.append(endpoint)
                    _append_text_block(lines, _first_string(action, ("description",)))
                    _append_example_blocks(lines, action.get("examples"))

    return ExtractionCandidate(
        strategy="apiary_embed_json",
        text=_normalize_text("\n".join(lines)),
        title=title or None,
        subtitle=None,
    )


def _candidate_from_apiary_embed(html: str) -> ExtractionCandidate | None:
    subdomain = _find_apiary_subdomain(html)
    if not subdomain:
        return None

    url = f"https://jsapi.apiary.io/apis/{subdomain}/"
    response = requests.get(url, timeout=20, headers={"User-Agent": "sitemix/apiary-fallback"})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    return _candidate_from_apiary_payload(payload)


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

    best_before_apiary = max(candidates, key=_score) if candidates else None
    if best_before_apiary is None or len(best_before_apiary.text) < min_text_chars:
        try:
            apiary_candidate = _candidate_from_apiary_embed(html)
        except Exception:
            apiary_candidate = None
        if apiary_candidate:
            attempts.append(
                ExtractionAttempt(
                    strategy=apiary_candidate.strategy,
                    text_len=len(apiary_candidate.text),
                    success=bool(apiary_candidate.text),
                )
            )
            if apiary_candidate.text:
                candidates.append(apiary_candidate)

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
