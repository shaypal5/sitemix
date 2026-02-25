from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "sitemix"
    version: str


class ExtractionAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    text_len: int = 0
    success: bool = False


class PageDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    fetched_url: str | None = None
    extracted_at: str
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date_published: str | None = None
    language: str | None = None
    text: str
    extraction_attempts: list[ExtractionAttempt] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CrawlParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_pages: int
    delay: float
    jitter: float
    concurrency: int
    respect_robots: bool
    include_external: bool
    query_filter: bool
    allow_patterns: list[str] = Field(default_factory=list)
    deny_patterns: list[str] = Field(default_factory=list)


class SkippedUrl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    reason: str


class SiteMapEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    depth: int


class SiteDump(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_url: str
    started_at: str
    finished_at: str
    crawl_params: CrawlParams
    discovered_urls_count: int
    visited_urls_count: int
    skipped_urls: list[SkippedUrl] = Field(default_factory=list)
    sitemap: list[SiteMapEntry] = Field(default_factory=list)
    pages: list[PageDoc] = Field(default_factory=list)


class DumpEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolInfo
    run: dict[str, Any]
    pages: list[PageDoc]
