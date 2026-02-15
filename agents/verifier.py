from __future__ import annotations

import os
import re
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NOT_FOUND = "Not found in provided sources."


def _extract_citations(text: str) -> List[str]:
    # Extracts things like: [DocName | chunk_id]
    return re.findall(r"\[[^\]]+\]", text)


def verify_answer(question: str, evidence_pack: str, draft: str) -> Dict:
    """
    Verifier agent:
    - Uses simple heuristics + an LLM check.
    - Returns dict: {status: PASS/FAIL, issues: [...], fix_instructions: "..."}
    """
    issues = []

    # Rule: if writer says NOT_FOUND, it must be exact
    if draft.strip() == NOT_FOUND:
        return {"status": "PASS", "issues": [], "fix_instructions": ""}

    # Rule: must have at least one citation
    citations = _extract_citations(draft)
    if not citations:
        issues.append("Missing citations in the answer.")

    # If no evidence, answer should have been NOT_FOUND
    if not evidence_pack.strip():
        issues.append(f"No evidence was provided, but the answer was not '{NOT_FOUND}'.")

    # If heuristics already show serious issues, still run LLM verifier (it can give better guidance)
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = OpenAI()

    system = (
        "You are a strict verifier.\n"
        "Check the draft ONLY against the evidence excerpts.\n"
        "Fail if the draft contains claims not supported by evidence.\n"
        f"Fail if the draft should have said '{NOT_FOUND}'.\n"
        "Fail if citations are missing or appear invented.\n"
        "Return a short verdict with PASS/FAIL + concrete fix instructions."
    )

    user = (
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE:\n{evidence_pack}\n\n"
        f"DRAFT:\n{draft}\n\n"
        "Return exactly this format:\n"
        "STATUS: PASS or FAIL\n"
        "ISSUES: bullet list\n"
        "FIX: one paragraph instructions\n"
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    verdict_text = resp.choices[0].message.content.strip()

    status = "FAIL" if "STATUS: FAIL" in verdict_text.upper() else "PASS"

    # merge heuristic issues if any
    if issues and status == "PASS":
        status = "FAIL"

    return {
        "status": status,
        "issues": issues + [verdict_text],
        "fix_instructions": "Use only supported statements from evidence, add citations per paragraph, or return NOT_FOUND.",
    }
