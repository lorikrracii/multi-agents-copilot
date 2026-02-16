from __future__ import annotations

import re
from typing import Dict, List, Tuple, Set, Optional

from agents.deliverer import NOT_FOUND_EXACT  # "Not found in the sources."


def _extract_bracket_groups(text: str) -> List[str]:
    """
    Extracts the raw content inside [ ... ] blocks.
    Returns items like: "Doc.pdf | p.1 | chunk_0000; Doc.pdf | p.2 | chunk_0001"
    """
    return re.findall(r"\[([^\]]+)\]", text or "")


def _split_multi_cites(group: str) -> List[str]:
    """
    Supports multiple citations inside one bracket, separated by ';' or ','.
    Example:
      "A | x; B | y" -> ["A | x", "B | y"]
    """
    parts = re.split(r"\s*[;,]\s*", (group or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _chunk_id_from_cite_inner(cite_inner: str) -> str:
    """
    Normalizes a citation to a comparable key.
    We use the chunk id as the key, since it's stable across formatting.
    If the cite has pipes, we take the last segment.
    """
    c = (cite_inner or "").strip()
    if "|" in c:
        return c.split("|")[-1].strip()
    return c


def _evidence_chunk_ids(evidence_pack: str) -> Set[str]:
    """
    Extract all chunk IDs present in evidence_pack.
    evidence_pack has lines like:
      EXCERPT 1 [Doc | ... | chunk_id]
    """
    ids: Set[str] = set()
    for group in _extract_bracket_groups(evidence_pack):
        for piece in _split_multi_cites(group):
            cid = _chunk_id_from_cite_inner(piece)
            if cid:
                ids.add(cid)
    return ids


def _answer_chunk_ids(answer: str) -> List[str]:
    """
    Extract chunk IDs referenced in the answer (supports multi-cites per bracket).
    """
    out: List[str] = []
    for group in _extract_bracket_groups(answer):
        for piece in _split_multi_cites(group):
            cid = _chunk_id_from_cite_inner(piece)
            if cid:
                out.append(cid)
    return out


def _paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]


def _paragraph_has_citation(p: str) -> bool:
    return bool(re.search(r"\[[^\]]+\]", p or ""))


def _citation_integrity_check(answer: str, evidence_pack: str) -> Tuple[bool, str]:
    """
    Validates:
    1) Answer citations refer only to chunk_ids present in evidence_pack
    2) Every paragraph has at least one citation (unless NOT_FOUND)
    """
    text = (answer or "").strip()

    # NOT_FOUND is always acceptable
    if text == NOT_FOUND_EXACT:
        return True, ""

    # Must contain at least one citation somewhere
    if not _extract_bracket_groups(text):
        return False, "Answer has no citations. Add citations copied from evidence, or return NOT_FOUND."

    ev_ids = _evidence_chunk_ids(evidence_pack)
    ans_ids = _answer_chunk_ids(text)

    missing = [cid for cid in ans_ids if cid not in ev_ids]
    if missing:
        return (
            False,
            f"Citations not in evidence (by chunk_id): {missing}. "
            "Use only citations present in evidence, or return NOT_FOUND.",
        )

    # Each paragraph must have at least one citation
    for p in _paragraphs(text):
        if not _paragraph_has_citation(p):
            return False, "A paragraph is missing a citation. Add at least one citation per paragraph."

    return True, ""


def verify_answer(question: str, evidence_pack: str, draft: str) -> Dict:
    """
    Verifier agent:
    - No hallucinations: citations must map to evidence chunks.
    - Every paragraph must contain at least one citation.
    - NOT_FOUND is allowed and returns PASS.
    """
    text = (draft or "").strip()

    ok, msg = _citation_integrity_check(text, evidence_pack)
    if not ok:
        return {"status": "FAIL", "issues": [msg], "fix_instructions": msg}

    return {"status": "PASS", "issues": [], "fix_instructions": ""}
