"""เลือกตัวสกัดตาม LLM_PROVIDER — สลับได้โดยไม่แตะ logic ที่ไหน"""

from __future__ import annotations

from app.config import settings
from app.llm.base import ExtractedSpan, SkillExtractor, enforce_span_guard
from app.llm.keyword import KeywordExtractor

__all__ = ["ExtractedSpan", "SkillExtractor", "enforce_span_guard", "get_extractor"]


def get_extractor() -> SkillExtractor:
    provider = settings.llm_provider.lower()
    if provider in {"keyword", "mock"}:
        return KeywordExtractor()
    if provider == "anthropic":
        from app.llm.anthropic import AnthropicExtractor
        return AnthropicExtractor()
    if provider == "local":
        from app.llm.local import LocalExtractor
        return LocalExtractor()
    if provider in {"gemini", "google"}:
        from app.llm.google import GeminiExtractor
        return GeminiExtractor()
    raise ValueError(
        f"ไม่รู้จัก LLM_PROVIDER={settings.llm_provider!r} — "
        "ใช้ keyword · local · anthropic · gemini"
    )
