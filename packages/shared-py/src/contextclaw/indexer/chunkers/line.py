from __future__ import annotations

from contextclaw.indexer.chunkers.base import Chunk, Chunker


class LineChunker(Chunker):
    """Fallback chunker — splits by line count with no AST awareness."""

    language = "text"
    _max_lines: int = 80

    def __init__(self, max_lines: int = 80) -> None:
        self._max_lines = max_lines

    def supported_extensions(self) -> frozenset[str]:
        return frozenset()  # universal fallback

    def chunk(self, source: str, file_path: str = "") -> list[Chunk]:
        lines = source.splitlines(keepends=True)
        chunks: list[Chunk] = []
        ordinal = 0

        for i in range(0, len(lines), self._max_lines):
            block = lines[i : i + self._max_lines]
            content = "".join(block)
            start = i + 1
            end = min(i + self._max_lines, len(lines))
            token_count = _estimate_tokens(content)
            chunks.append(
                Chunk(
                    content=content,
                    start_line=start,
                    end_line=end,
                    ordinal=ordinal,
                    language="text",
                    token_count=token_count,
                )
            )
            ordinal += 1

        return chunks


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)
