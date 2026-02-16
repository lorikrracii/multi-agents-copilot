from __future__ import annotations

from typing import Any, Dict, List

from retrieval.retriever import Retriever


def retrieve_evidence(question: str, k: int = 6) -> List[Dict[str, Any]]:
    r = Retriever()

    ql = (question or "").lower()
    queries = [question]

    # Targeted expansion for Holidays PDF
    if "holiday" in ql or "holidays" in ql:
        queries += [
            "Law 03-L-064 Official Holidays Kosovo",
            "official holidays Kosovo law",
            "public holidays Kosovo",
        ]

    # Merge unique chunks
    merged: List[Dict[str, Any]] = []
    seen = set()

    for q in queries:
        res = r.search(q, k=max(k, 6))
        for item in res:
            key = item.get("citation") or (item.get("metadata", {}) or {}).get("chunk_id") or item.get("text", "")[:80]
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    # Sort by distance if present (lower is better)
    merged.sort(key=lambda x: (x.get("distance") if x.get("distance") is not None else 999999))

    return merged[:k]


def format_evidence(evidence: List[Dict[str, Any]]) -> str:
    parts = []
    for i, e in enumerate(evidence, start=1):
        citation = e.get("citation", f"[chunk {i}]")
        text = e.get("text", "")
        parts.append(f"EXCERPT {i} {citation}\n{text}")
    return "\n\n---\n\n".join(parts)
