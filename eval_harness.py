"""
ContextClaw Retrieval Eval Harness.

Evaluates search quality using standard IR metrics:
  - Recall@k
  - Precision@k
  - MRR (Mean Reciprocal Rank)
  - NDCG@k (Normalized Discounted Cumulative Gain)

Usage:
    python -m eval_harness run --queries eval_queries.json
    python -m eval_harness compare --baseline hybrid --candidate vector
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ── Data structures ────────────────────────────────────────────────


@dataclass
class QueryExample:
    """A single eval query with expected relevant chunk IDs."""

    query: str
    relevant_chunk_ids: list[str]
    project_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Results for a single query."""

    query: str
    retrieved_ids: list[str]
    relevant_ids: set[str]
    relevant_retrieved: list[str]
    scores: list[float]
    took_ms: int

    @property
    def num_relevant(self) -> int:
        return len(self.relevant_ids)

    @property
    def num_retrieved(self) -> int:
        return len(self.retrieved_ids)

    def recall_at(self, k: int) -> float:
        if self.num_relevant == 0:
            return 0.0
        retrieved = set(self.retrieved_ids[:k])
        hits = len(retrieved & self.relevant_ids)
        return hits / self.num_relevant

    def precision_at(self, k: int) -> float:
        if k == 0:
            return 0.0
        retrieved = set(self.retrieved_ids[:k])
        hits = len(retrieved & self.relevant_ids)
        return hits / k

    def reciprocal_rank(self) -> float:
        for i, cid in enumerate(self.retrieved_ids):
            if cid in self.relevant_ids:
                return 1.0 / (i + 1)
        return 0.0

    def ndcg_at(self, k: int) -> float:
        """NDCG@k — binary relevance (1 if relevant, 0 otherwise)."""
        retrieved = self.retrieved_ids[:k]
        dcg = 0.0
        for i, cid in enumerate(retrieved):
            if cid in self.relevant_ids:
                dcg += 1.0 / math.log2(i + 2)

        # Ideal DCG: all relevant docs at top
        ideal_hits = min(len(retrieved), self.num_relevant)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))

        return dcg / idcg if idcg > 0 else 0.0


@dataclass
class EvalSummary:
    """Aggregated metrics across all queries."""

    num_queries: int
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    precision_at_5: float
    precision_at_10: float
    mrr: float
    ndcg_at_5: float
    ndcg_at_10: float
    avg_took_ms: float
    per_query: list[EvalResult] = field(default_factory=list)


# ── Runner ─────────────────────────────────────────────────────────


SearchMode = Literal["hybrid", "vector", "fts"]


def run_eval(
    queries: list[QueryExample],
    mode: SearchMode = "hybrid",
    k: int = 10,
    verbose: bool = False,
) -> EvalSummary:
    """Run evaluation for a list of queries using the specified search mode.

    Calls the hybrid/vector/fts search functions directly (not via API).
    """
    from contextclaw.embeddings.router import get_embedding_provider
    from contextclaw.search.hybrid import hybrid_search, HybridSearchConfig

    results: list[EvalResult] = []

    for q in queries:
        t0 = time.time()

        if mode == "vector":
            from contextclaw.search.vector import embed_and_search

            raw = embed_and_search(
                project_id=q.project_id, query_text=q.query, k=k
            )
        elif mode == "fts":
            from contextclaw.search.fts import fts_search

            raw = fts_search(
                project_id=q.project_id, query_text=q.query, k=k
            )
        else:
            provider = get_embedding_provider()
            query_vector = provider.embed_one(q.query)
            raw = hybrid_search(
                project_id=q.project_id,
                query_text=q.query,
                query_vector=query_vector,
                config=HybridSearchConfig(final_k=k),
            )

        took_ms = int((time.time() - t0) * 1000)

        retrieved_ids = [str(r.chunk_id) for r in raw]
        scores = [r.score for r in raw]
        relevant_set = set(q.relevant_chunk_ids)
        relevant_retrieved = [cid for cid in retrieved_ids if cid in relevant_set]

        result = EvalResult(
            query=q.query,
            retrieved_ids=retrieved_ids,
            relevant_ids=relevant_set,
            relevant_retrieved=relevant_retrieved,
            scores=scores,
            took_ms=took_ms,
        )
        results.append(result)

        if verbose:
            rr = result.reciprocal_rank()
            r10 = result.recall_at(10)
            print(f"  [{mode}] {q.query[:50]:50s}  RR={rr:.3f}  R@10={r10:.3f}  ({took_ms}ms)")

    return _aggregate(results)


def _aggregate(results: list[EvalResult]) -> EvalSummary:
    n = len(results)
    if n == 0:
        return EvalSummary(
            num_queries=0, recall_at_1=0, recall_at_5=0, recall_at_10=0,
            precision_at_5=0, precision_at_10=0, mrr=0, ndcg_at_5=0,
            ndcg_at_10=0, avg_took_ms=0,
        )

    return EvalSummary(
        num_queries=n,
        recall_at_1=sum(r.recall_at(1) for r in results) / n,
        recall_at_5=sum(r.recall_at(5) for r in results) / n,
        recall_at_10=sum(r.recall_at(10) for r in results) / n,
        precision_at_5=sum(r.precision_at(5) for r in results) / n,
        precision_at_10=sum(r.precision_at(10) for r in results) / n,
        mrr=sum(r.reciprocal_rank() for r in results) / n,
        ndcg_at_5=sum(r.ndcg_at(5) for r in results) / n,
        ndcg_at_10=sum(r.ndcg_at(10) for r in results) / n,
        avg_took_ms=sum(r.took_ms for r in results) / n,
        per_query=results,
    )


# ── Compare modes ──────────────────────────────────────────────────


def compare_modes(
    queries: list[QueryExample],
    modes: list[SearchMode] | None = None,
    k: int = 10,
) -> dict[str, EvalSummary]:
    """Run eval for multiple search modes and return side-by-side results."""
    if modes is None:
        modes = ["hybrid", "vector", "fts"]

    results: dict[str, EvalSummary] = {}
    for mode in modes:
        print(f"\n=== Running eval: {mode} ===")
        results[mode] = run_eval(queries, mode=mode, k=k, verbose=True)

    return results


# ── CLI entry point ────────────────────────────────────────────────


def print_summary(name: str, s: EvalSummary) -> None:
    """Pretty-print an EvalSummary."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Queries:       {s.num_queries}")
    print(f"  Recall@1:      {s.recall_at_1:.4f}")
    print(f"  Recall@5:      {s.recall_at_5:.4f}")
    print(f"  Recall@10:     {s.recall_at_10:.4f}")
    print(f"  Precision@5:   {s.precision_at_5:.4f}")
    print(f"  Precision@10:  {s.precision_at_10:.4f}")
    print(f"  MRR:           {s.mrr:.4f}")
    print(f"  NDCG@5:        {s.ndcg_at_5:.4f}")
    print(f"  NDCG@10:       {s.ndcg_at_10:.4f}")
    print(f"  Avg latency:   {s.avg_took_ms:.0f}ms")


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "run":
        path = sys.argv[2] if len(sys.argv) > 2 else "eval_queries.json"
        mode = sys.argv[3] if len(sys.argv) > 3 else "hybrid"

        with open(path) as f:
            data = json.load(f)

        queries = [QueryExample(**q) for q in data]
        print(f"Loaded {len(queries)} eval queries from {path}")

        summary = run_eval(queries, mode=mode, verbose=True)
        print_summary(mode, summary)

    elif cmd == "compare":
        path = sys.argv[2] if len(sys.argv) > 2 else "eval_queries.json"
        with open(path) as f:
            data = json.load(f)

        queries = [QueryExample(**q) for q in data]
        print(f"Loaded {len(queries)} eval queries from {path}")

        results = compare_modes(queries)
        for name, summary in results.items():
            print_summary(name, summary)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
