from __future__ import annotations

from agents.planner import make_plan
from agents.research import retrieve_evidence, format_evidence
from agents.writer import write_answer, NOT_FOUND
from agents.verifier import verify_answer


def answer_question(question: str, k: int = 6) -> dict:
    plan = make_plan(question)

    evidence = retrieve_evidence(question, k=k)
    evidence_pack = format_evidence(evidence)

    # If nothing retrieved, force NOT_FOUND immediately
    if not evidence:
        return {
            "plan": plan,
            "evidence": evidence,
            "answer": NOT_FOUND,
            "verdict": {"status": "PASS", "issues": [], "fix_instructions": ""},
        }

    draft = write_answer(question, evidence_pack)
    verdict = verify_answer(question, evidence_pack, draft)

    # One revision only (keeps it predictable)
    if verdict.get("status") == "FAIL":
        draft = write_answer(
            question,
            evidence_pack
            + "\n\nVERIFIER FEEDBACK:\n"
            + verdict.get("fix_instructions", "Revise to be fully supported by evidence, or return NOT_FOUND."),
        )
        verdict = verify_answer(question, evidence_pack, draft)

    return {
        "plan": plan,
        "evidence": evidence,
        "answer": draft,
        "verdict": verdict,
    }
