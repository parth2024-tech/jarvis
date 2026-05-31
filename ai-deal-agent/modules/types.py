"""Shared types passed between layers."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class RawChunk:
    """A unit of raw text from any source, ready for dedup + extraction."""
    source_url: str
    source_type: str  # official / community / newsletter / search / partner
    text: str
    fetched_at: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
