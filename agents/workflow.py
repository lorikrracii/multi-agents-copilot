from __future__ import annotations

import re
import time
from typing import NotRequired, TypedDict

from langgraph.graph import StateGraph, START, END

from agents.planner import make_plan
from agents.research import retrieve_evidence, format_evidence
from agents.writer import write_answer
from agents.verifier import verify_answer
from agents.deliverer import build_deliverable, NOT_FOUND_EXACT

NOT_FOUND = "Not found in provided sources."


def _normalize_citations(answer: str) -> str:
    """
    Convert citation formatting from:
      (Doc | ...chunk_0001)  ->  [Doc | ...chunk_0001]
    Only touches strings that look like your citations (contain '|' and 'chunk_').
    """
    if not answer:
        return answer
    if answer.strip() == NOT_FOUND:
        return answer

    # Convert parentheses citations to bracket citations
    return re.sub(r"\(([^()]*\|[^()]*chunk_[^()]*)\)", r"[\1]", answer)


class WorkflowState(TypedDict):
    # Inputs
    question: str
    k: int
    revision_count: int
    company_name: str

    # Intermediate / outputs
    plan: NotRequired[dict]
    evidence: NotRequired[list]
    evidence_pack: NotRequired[str]
    draft: NotRequired[str]
    answer: NotRequired[str]
    verdict: NotRequired[dict]
    deliverable: NotRequired[dict]
    trace: NotRequired[list]


def _trace_append(state: WorkflowState, entry: dict) -> list:
    t = list(state.get("trace") or [])
    t.append(entry)
    return t


def _apply_company_name(text: str, company_name: str) -> str:
    if not text:
        return text
    return (
        text.replace("[Company Name]", company_name)
            .replace("{Company Name}", company_name)
    )


def _fix_answer_citations(answer: str, evidence: list[dict]) -> str:
    """
    If the LLM outputs citations like [Some_chunk_0000] (chunk-id only),
    rewrite them into the exact full citation strings that appear in evidence,
    e.g. [Doc.md | Some_chunk_0000] or [PDF | p.X | ...chunk...]
    """
    if not answer:
        return answer

    # Map chunk_id -> full citation (including brackets)
    chunk_to_full = {}
    for ev in evidence or []:
        md = ev.get("metadata", {}) or {}
        chunk_id = md.get("chunk_id")
        full = ev.get("citation")
        if chunk_id and full:
            chunk_to_full[str(chunk_id)] = str(full)

    # Replace bracketed citations that are chunk-only
    def repl(m: re.Match) -> str:
        inside = m.group(1).strip()
        # If it already looks like "Doc | chunk", keep it
        if "|" in inside:
            return m.group(0)

        # If it matches a known chunk_id, replace whole bracket with full citation
        if inside in chunk_to_full:
            return chunk_to_full[inside]

        # Otherwise keep as-is (verifier may fail it)
        return m.group(0)

    return re.sub(r"\[([^\]]+)\]", repl, answer)


def _plan_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()
    plan = make_plan(state["question"])
    ms = int((time.perf_counter() - t0) * 1000)
    trace = _trace_append(state, {"agent": "planner", "status": "ok", "ms": ms})
    return {"plan": plan, "trace": trace}


def _research_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()
    evidence = retrieve_evidence(state["question"], k=state["k"])
    evidence_pack = format_evidence(evidence)
    ms = int((time.perf_counter() - t0) * 1000)

    cites = []
    for ev in evidence or []:
        c = ev.get("citation")
        if c:
            cites.append(c)

    trace = _trace_append(
        state,
        {"agent": "research", "status": "ok", "ms": ms, "k": state["k"], "sources": cites},
    )
    return {"evidence": evidence, "evidence_pack": evidence_pack, "trace": trace}


def _no_evidence_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()
    ms = int((time.perf_counter() - t0) * 1000)

    trace = _trace_append(state, {"agent": "writer", "status": "not_found", "ms": ms})
    answer = NOT_FOUND_EXACT
    verdict = {"status": "PASS", "issues": [], "fix_instructions": ""}

    return {"answer": answer, "verdict": verdict, "trace": trace}


def _write_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()

    draft, meta = write_answer(state["question"], state.get("evidence_pack", ""), return_meta=True)

    ms = int((time.perf_counter() - t0) * 1000)
    draft = _apply_company_name(draft, state["company_name"])

    # ✅ Normalize ( ... ) citations -> [ ... ] BEFORE fixing chunk-only citations
    draft = _normalize_citations(draft)

    # ✅ Fix chunk-only citations using evidence mapping
    draft = _fix_answer_citations(draft, state.get("evidence", []) or [])

    trace = _trace_append(
        state,
        {
            "agent": "writer",
            "status": "ok",
            "ms": ms,
            "model": meta.get("model"),
            "prompt_tokens": meta.get("prompt_tokens"),
            "completion_tokens": meta.get("completion_tokens"),
            "total_tokens": meta.get("total_tokens"),
        },
    )
    return {"draft": draft, "answer": draft, "trace": trace}


def _verify_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()

    # ✅ Verify the normalized/fixed draft
    draft = state.get("draft", "") or state.get("answer", "")

    verdict = verify_answer(
        state["question"],
        state.get("evidence_pack", ""),
        draft,
        evidence_list=state.get("evidence", []) or [],
    )

    ms = int((time.perf_counter() - t0) * 1000)
    status = str((verdict or {}).get("status", "UNKNOWN")).upper()
    trace = _trace_append(state, {"agent": "verifier", "status": status, "ms": ms})
    return {"verdict": verdict, "trace": trace}


def _revise_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()
    feedback = (state.get("verdict") or {}).get(
        "fix_instructions",
        "Revise to be fully supported by evidence, or return NOT_FOUND.",
    )

    revised, meta = write_answer(
        state["question"],
        state.get("evidence_pack", "") + "\n\nVERIFIER FEEDBACK:\n" + feedback,
        return_meta=True,
    )

    revised = _apply_company_name(revised, state["company_name"])

    # ✅ Normalize ( ... ) citations -> [ ... ] BEFORE fixing chunk-only citations
    revised = _normalize_citations(revised)

    # ✅ Fix chunk-only citations using evidence mapping
    revised = _fix_answer_citations(revised, state.get("evidence", []) or [])

    ms = int((time.perf_counter() - t0) * 1000)
    trace = _trace_append(
        state,
        {
            "agent": "writer",
            "status": "revised_once",
            "ms": ms,
            "model": meta.get("model"),
            "prompt_tokens": meta.get("prompt_tokens"),
            "completion_tokens": meta.get("completion_tokens"),
            "total_tokens": meta.get("total_tokens"),
        },
    )

    return {
        "revision_count": state["revision_count"] + 1,
        "draft": revised,
        "answer": revised,
        "trace": trace,
    }


def _deliver_node(state: WorkflowState) -> dict:
    t0 = time.perf_counter()

    deliverable = build_deliverable(
        question=state["question"],
        answer=state.get("answer", NOT_FOUND_EXACT),
        evidence=state.get("evidence", []) or [],
        verdict=state.get("verdict", {}) or {},
        company_name=state["company_name"],
    )

    ms = int((time.perf_counter() - t0) * 1000)
    trace = _trace_append(state, {"agent": "deliverer", "status": "ok", "ms": ms})
    return {"deliverable": deliverable, "trace": trace}


def _route_after_research(state: WorkflowState) -> str:
    ev = state.get("evidence") or []
    return "no_evidence" if len(ev) == 0 else "write"


def _route_after_verify(state: WorkflowState) -> str:
    verdict = state.get("verdict") or {}
    status = str(verdict.get("status", "")).upper()

    if status == "FAIL" and state.get("revision_count", 0) < 1:
        return "revise"
    return "deliver"


def _build_graph():
    g = StateGraph(WorkflowState)

    g.add_node("plan", _plan_node)
    g.add_node("research", _research_node)
    g.add_node("no_evidence", _no_evidence_node)
    g.add_node("write", _write_node)
    g.add_node("verify", _verify_node)
    g.add_node("revise", _revise_node)
    g.add_node("deliver", _deliver_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "research")

    g.add_conditional_edges("research", _route_after_research, {
        "no_evidence": "no_evidence",
        "write": "write",
    })

    g.add_edge("no_evidence", "deliver")
    g.add_edge("write", "verify")

    g.add_conditional_edges("verify", _route_after_verify, {
        "revise": "revise",
        "deliver": "deliver",
    })

    g.add_edge("revise", "verify")
    g.add_edge("deliver", END)

    return g.compile()


_GRAPH = _build_graph()


def answer_question(question: str, k: int = 6, company_name: str = "Your Company") -> dict:
    final_state = _GRAPH.invoke(
        {
            "question": question,
            "k": k,
            "revision_count": 0,
            "company_name": company_name,
            "trace": [],
        }
    )

    return {
        "plan": final_state.get("plan"),
        "evidence": final_state.get("evidence", []),
        "answer": final_state.get("answer", NOT_FOUND_EXACT),
        "verdict": final_state.get("verdict", {"status": "FAIL", "issues": ["No verdict returned"]}),
        "deliverable": final_state.get("deliverable", {}),
        "trace": final_state.get("trace", []),
    }
