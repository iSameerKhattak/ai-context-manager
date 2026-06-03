from __future__ import annotations

import sys
from typing import Any

from contextclaw.indexer.chunkers.base import Chunk, Chunker
from contextclaw.indexer.chunkers.line import LineChunker, _estimate_tokens

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".go": "go",
    ".java": "java",
}

_QUERIES: dict[str, list[str]] = {
    "python": [
        "(function_definition name: (_) @sym) @body",
        "(class_definition name: (_) @sym) @body",
        "(decorated_definition definition: (function_definition name: (_) @sym) @body)",
        "(decorated_definition definition: (class_definition name: (_) @sym) @body)",
    ],
    "typescript": [
        "(function_declaration name: (_) @sym) @body",
        "(method_definition name: (_) @sym) @body",
        "(class_declaration name: (_) @sym) @body",
        "(interface_declaration name: (_) @sym) @body",
        "(enum_declaration name: (_) @sym) @body",
        "(lexical_declaration (variable_declarator name: (_) @sym)) @body",
    ],
    "tsx": [
        "(function_declaration name: (_) @sym) @body",
        "(method_definition name: (_) @sym) @body",
        "(class_declaration name: (_) @sym) @body",
        "(interface_declaration name: (_) @sym) @body",
        "(enum_declaration name: (_) @sym) @body",
        "(lexical_declaration (variable_declarator name: (_) @sym)) @body",
    ],
    "javascript": [
        "(function_declaration name: (_) @sym) @body",
        "(method_definition name: (_) @sym) @body",
        "(class_declaration name: (_) @sym) @body",
        "(method_definition name: (_) @sym) @body",
        "(lexical_declaration (variable_declarator name: (_) @sym)) @body",
    ],
    "go": [
        "(function_declaration name: (_) @sym) @body",
        "(method_declaration name: (_) @sym) @body",
        "(type_declaration (type_spec name: (_) @sym)) @body",
    ],
    "java": [
        "(method_declaration name: (_) @sym) @body",
        "(class_declaration name: (_) @sym) @body",
        "(interface_declaration name: (_) @sym) @body",
        "(enum_declaration name: (_) @sym) @body",
        "(record_declaration name: (_) @sym) @body",
    ],
}


def _import_grammar(lang_name: str) -> Any:
    """Import a tree-sitter language grammar module."""
    import importlib
    mod = importlib.import_module(f"tree_sitter_{lang_name}")
    return mod.language()


def _node_start(n: Any) -> int:
    return n.start_point[0] + 1


def _node_end(n: Any) -> int:
    return n.end_point[0] + 1


def _node_text(source_bytes: bytes, n: Any) -> str:
    return source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace")


class TreeSitterChunker(Chunker):
    """AST-aware chunker using tree-sitter grammars.

    Extracts function/class/method definitions as individual chunks.
    Falls back to LineChunker for unparseable files or unknown languages.
    """

    def __init__(self, language: str) -> None:
        self.language = language
        self._fallback = LineChunker()

        # Map tsx/javascript to the typescript grammar module
        _grammar_pkg = language.replace("tsx", "typescript").replace(
            "javascript", "typescript"
        )
        # For tsx, use the tsx language function; for TS/JS, use typescript
        if language == "tsx":
            import tree_sitter_typescript as tsts
            lang_capsule = tsts.language_tsx()
        else:
            try:
                lang_capsule = _import_grammar(_grammar_pkg)
            except Exception:
                lang_capsule = None

        self._lang: Any = None
        self._parser: Any = None
        self._queries: list[Any] = []

        if lang_capsule is not None:
            import tree_sitter as ts
            self._lang = ts.Language(lang_capsule)
            self._parser = ts.Parser(self._lang)
            for qs in _QUERIES.get(language, []):
                try:
                    self._queries.append(ts.Query(self._lang, qs))
                except Exception:
                    pass

    def supported_extensions(self) -> frozenset[str]:
        return frozenset(k for k, v in _LANGUAGE_MAP.items() if v == self.language)

    def chunk(self, source: str, file_path: str = "") -> list[Chunk]:
        if self._parser is None or not self._queries:
            return self._fallback.chunk(source, file_path)

        source_bytes = source.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        root = tree.root_node

        if root is None or root.has_error:
            return self._fallback.chunk(source, file_path)

        raw: list[tuple[int, int, str | None]] = []
        import tree_sitter as ts

        for query in self._queries:
            cursor = ts.QueryCursor(query)
            for _pattern_index, captures_dict in cursor.matches(root):
                body_nodes = captures_dict.get("body", [])
                sym_nodes = captures_dict.get("sym", [])
                if not body_nodes:
                    continue
                body = body_nodes[0]
                symbol = _node_text(source_bytes, sym_nodes[0]) if sym_nodes else None
                raw.append((_node_start(body), _node_end(body), symbol))

        if not raw:
            return self._fallback.chunk(source, file_path)

        raw.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        deduped: list[tuple[int, int, str | None]] = []
        last_end = 0
        for start, end, sym in raw:
            if start >= last_end:
                deduped.append((start, end, sym))
                last_end = end

        lines = source.splitlines(keepends=True)
        chunks: list[Chunk] = []
        ordinal = 0

        for start, end, sym in deduped:
            content = "".join(lines[start - 1 : end])
            if not content.strip():
                continue
            token_count = _estimate_tokens(content)
            chunks.append(
                Chunk(
                    content=content,
                    start_line=start,
                    end_line=end,
                    ordinal=ordinal,
                    symbol=sym,
                    language=self.language,
                    token_count=token_count,
                )
            )
            ordinal += 1

        return chunks


def chunker_for_file(file_path: str) -> Chunker:
    """Return the best chunker for *file_path* based on its extension."""
    import os
    ext = os.path.splitext(file_path)[1].lower()
    lang = _LANGUAGE_MAP.get(ext)
    if lang:
        return TreeSitterChunker(lang)
    return LineChunker()


def chunker_for_language(language: str) -> Chunker:
    """Return the best chunker for a language name."""
    if language in {"python", "typescript", "tsx", "javascript", "go", "java"}:
        return TreeSitterChunker(language)
    return LineChunker()
