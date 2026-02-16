from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# ✅ Ensure repo root is on PYTHONPATH (fixes: No module named 'agents')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.workflow import answer_question  # noqa: E402

QUESTIONS_PATH = ROOT / "eval" / "questions.json"
REPORT_PATH = ROOT / "eval" / "report.json"


def _extract_bracket_citations(text: str) -> List[str]:
    import re
    if not text:
        return []
    return [c.strip() for c in re.findall(r"\[([^\]]+)\]", text)]


def _is_not_found(result: Dict[str, Any]) -> bool:
    ans = (result.get("answer") or "").strip().lower()
    exec_sum = ((result.get("deliverable") or {}).get("executive_summary") or "").strip().lower()
    return ans.startswith("not found") or exec_sum.startswith("not found")


def _allowed_citations_from_evidence(result: Dict[str, Any]) -> set[str]:
    allowed = set()
    for ev in (result.get("evidence") or []):
        cite = (ev.get("citation") or "").strip()
        if cite.startswith("[") and cite.endswith("]"):
            cite = cite[1:-1].strip()
        if cite:
            allowed.add(cite)
    return allowed


def run(company_name: str = "KosovoTech LLC", k: int = 6) -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    rows = []
    passed = 0

    for q in questions:
        qid = q["id"]
        question = q["question"]
        expect_found = bool(q["expect_found"])

        result = answer_question(question, k=k, company_name=company_name)

        not_found = _is_not_found(result)
        verdict = (result.get("verdict") or {}).get("status", "UNKNOWN")
        deliverable = result.get("deliverable") or {}
        trace = result.get("trace") or []

        # citation sanity check: answer citations must be subset of evidence citations
        answer_cites = _extract_bracket_citations(result.get("answer") or "")
        allowed = _allowed_citations_from_evidence(result)
        out_of_set = [c for c in answer_cites if c not in allowed] if allowed else []

        ok_found_logic = (expect_found and not not_found) or ((not expect_found) and not_found)
        ok_verdict = (str(verdict).upper() == "PASS")
        ok_cites = (len(out_of_set) == 0) if not not_found else True  # not-found doesn't require cites

        ok = ok_found_logic and ok_verdict and ok_cites
        passed += 1 if ok else 0

        rows.append({
            "id": qid,
            "expect_found": expect_found,
            "not_found": not_found,
            "verdict": verdict,
            "ok": ok,
            "out_of_set_citations": out_of_set,
            "sources_count": len(deliverable.get("sources") or []),
            "trace": trace,
        })

        print(f"{qid} | {'OK' if ok else 'FAIL'} | expect_found={expect_found} | not_found={not_found} | verdict={verdict}")
        if out_of_set:
            print(f"   ⚠ citations not in evidence: {out_of_set}")

    summary = {
        "company_name": company_name,
        "k": k,
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "results": rows,
    }
    REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== EVAL SUMMARY ===")
    print(f"Passed: {passed}/{len(rows)}")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    run()
