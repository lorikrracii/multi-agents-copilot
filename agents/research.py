from __future__ import annotations

from typing import Any, Dict, List

from retrieval.retriever import Retriever


def retrieve_evidence(question: str, k: int = 6) -> List[Dict[str, Any]]:
    """
    Research agent:
    - Calls the vector DB retriever.
    - Returns a list of chunks with text + citation + metadata.
    """
    r = Retriever()
    return r.search(question, k=k)


def format_evidence(evidence: List[Dict[str, Any]]) -> str:
    """
    Turns evidence into a compact 'evidence pack' that the LLM can use.
    """
    parts = []
    for i, e in enumerate(evidence, start=1):
        citation = e.get("citation", f"[chunk {i}]")
        text = e.get("text", "")
        parts.append(f"EXCERPT {i} {citation}\n{text}")
    return "\n\n---\n\n".join(parts)
