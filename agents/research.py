from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from retrieval.retriever import Retriever

# ---- Relevance filtering knobs (env overrides) ----
# If a question has 4+ meaningful keywords, require >=2 overlaps; otherwise >=1.
MIN_KEYWORD_OVERLAP = int(os.getenv("MIN_KEYWORD_OVERLAP", "1"))

# Optional: enable distance filtering if you want (0 = disabled).
# If you later want it, try 0.35 for cosine distance, but tune by printing distances.
MAX_EVIDENCE_DISTANCE = float(os.getenv("MAX_EVIDENCE_DISTANCE", "0"))  # 0 disables

# Keep this list small but effective for your HR domain.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or",
    "our", "should", "tell", "that", "the", "their", "then", "they", "this",
    "to", "us", "was", "we", "what", "when", "where", "which", "who", "why",
    "will", "with", "you", "your",
    # domain-generic words that cause noisy matches:
    "policy", "document", "company", "rule", "rules"
}


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def _min_overlap_needed(q_tokens: List[str]) -> int:
    # dynamic: longer, more specific questions should require more overlap
    base = 1 if len(q_tokens) <= 3 else 2
    return max(base, MIN_KEYWORD_OVERLAP)


def _keyword_overlap_count(q_tokens: List[str], chunk_text: str) -> int:
    if not q_tokens or not chunk_text:
        return 0
    t = chunk_text.lower()
    # count unique keyword hits to avoid double-counting repeats
    hits = {w for w in q_tokens if w in t}
    return len(hits)


def _passes_distance(e: Dict[str, Any]) -> bool:
    # distance filtering disabled by default
    if MAX_EVIDENCE_DISTANCE <= 0:
        return True
    d = e.get("distance", None)
    if d is None:
        return True
    return d <= MAX_EVIDENCE_DISTANCE


def _is_relevant(question: str, e: Dict[str, Any]) -> bool:
    q_tokens = _tokens(question)
    needed = _min_overlap_needed(q_tokens)

    overlap = _keyword_overlap_count(q_tokens, e.get("text", ""))

    # must pass both: distance (optional) + keyword overlap
    if not _passes_distance(e):
        return False

    return overlap >= needed


def retrieve_evidence(question: str, k: int = 6) -> List[Dict[str, Any]]:
    """
    Research agent:
    - Calls vector DB retriever
    - Filters out irrelevant matches so NOT_FOUND cases don't show random sources
    """
    r = Retriever()
    raw = r.search(question, k=k)

    filtered = [e for e in raw if _is_relevant(question, e)]
    return filtered


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
