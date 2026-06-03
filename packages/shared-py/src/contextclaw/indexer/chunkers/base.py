from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Chunk:
    """A single code chunk produced by a chunker."""

    content: str
    start_line: int
    end_line: int
    ordinal: int
    symbol: str | None = None
    language: str | None = None
    token_count: int | None = None


class Chunker:
    """Abstract base for all chunkers."""

    language: str

    def chunk(self, source: str, file_path: str = "") -> list[Chunk]:
        """Split *source* into a list of Chunks."""
        raise NotImplementedError

    def supported_extensions(self) -> frozenset[str]:
        """Return the file extensions this chunker handles."""
        return frozenset()
