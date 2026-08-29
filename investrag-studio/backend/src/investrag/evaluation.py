from __future__ import annotations

import math
from collections.abc import Iterable


def success_at_k(relevant: set[str], retrieved: Iterable[str], k: int) -> float:
    return float(bool(relevant.intersection(list(retrieved)[:k])))


def recall_at_k(relevant: set[str], retrieved: Iterable[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant.intersection(list(retrieved)[:k])) / len(relevant)


def reciprocal_rank(relevant: set[str], retrieved: Iterable[str], k: int) -> float:
    for index, item in enumerate(list(retrieved)[:k], start=1):
        if item in relevant:
            return 1 / index
    return 0.0


def ndcg_at_k(relevance: dict[str, int], retrieved: Iterable[str], k: int) -> float:
    ranked = list(retrieved)[:k]
    dcg = sum((2 ** relevance.get(item, 0) - 1) / math.log2(index + 2) for index, item in enumerate(ranked))
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**value - 1) / math.log2(index + 2) for index, value in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def citation_coverage(answer: str, cited_labels: set[str]) -> float:
    citations = {token.strip("[]") for token in answer.split() if token.startswith("[") and token.endswith("]")}
    return float(bool(citations and citations.intersection(cited_labels))) if cited_labels else 0.0
