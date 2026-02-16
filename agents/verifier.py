from __future__ import annotations

import re
from typing import Dict, List

from agents.writer import NOT_FOUND


_STOP = {
    "what", "are", "is", "the", "a", "an", "in", "on", "of", "to", "for", "and", "or",
    "our", "your", "company", "policy", "please", "tell", "me", "kosovo"
}


def _keywords(question: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]{4,}", (question or "").lower())
    kws = [w for w in words if w not in _STOP]
    # keep top few keywords
    return kws[:6]


def _extract_bracket_blocks(text: str) -> List[str]:
    # returns full bracket tokens like "[Doc | chunk]"
    return re.findall(r"\[[^\]]+\]", text or "")


def _split_multi_citation_block(block: str) -> List[str]:
    """
    If someone outputs: [A | chunk_0, B | chunk_1]  -> INVALID (we want separate brackets)
    This returns the inside pieces so we can detect & fail it.
    """
    inside = block.strip()[1:-1]
    if "," in inside or ";" in inside:
        parts = re.split(r"[;,]", inside)
        return [p.strip() for p in parts if p.strip()]
    return []


def _paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return parts


def verify_answer(question: str, evidence_pack: str, draft: str) -> Dict:
    clean = (draft or "").strip()

    # NOT_FOUND is always acceptable
    if clean == NOT_FOUND or clean.startswith("Not found"):
        return {"status": "PASS", "issues": [], "fix_instructions": ""}

    # Evidence citations = all bracket citations appearing in evidence_pack
    evidence_cites = set(_extract_bracket_blocks(evidence_pack))

    # 1) Relevance guard: if none of the key question words appear in evidence_pack -> must be NOT_FOUND
    kws = _keywords(question)
    ev_low = (evidence_pack or "").lower()
    hits = sum(1 for w in kws if w in ev_low)
    if kws and hits == 0:
        msg = (
            "Evidence appears unrelated to the question keywords. "
            f"Return EXACTLY: {NOT_FOUND}"
        )
        return {"status": "FAIL", "issues": [msg], "fix_instructions": msg}

    # 2) Each paragraph must have a citation
    for p in _paragraphs(clean):
        if not _extract_bracket_blocks(p):
            msg = "Every paragraph must include at least one citation copied EXACTLY from the evidence."
            return {"status": "FAIL", "issues": [msg], "fix_instructions": msg}

    # 3) No multi-citations inside one bracket
    for b in _extract_bracket_blocks(clean):
        multi = _split_multi_citation_block(b)
        if multi:
            msg = (
                "Do not put multiple citations inside one bracket. "
                "Use separate brackets for each citation, and copy them exactly from evidence."
            )
            return {"status": "FAIL", "issues": [msg], "fix_instructions": msg}

    # 4) Citation integrity: every citation must exist in evidence
    used = _extract_bracket_blocks(clean)
    invalid = [c for c in used if c not in evidence_cites]
    if invalid:
        msg = (
            "Invalid / invented citation(s) detected (not present in evidence): "
            + ", ".join(invalid)
            + f". Fix citations or return EXACTLY: {NOT_FOUND}"
        )
        return {"status": "FAIL", "issues": [msg], "fix_instructions": msg}

    return {"status": "PASS", "issues": [], "fix_instructions": ""}
