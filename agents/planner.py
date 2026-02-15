from __future__ import annotations

def make_plan(question: str) -> dict:
    """
    Planner agent:
    - No LLM needed.
    - Makes a deterministic plan (good for grading + reproducibility).
    """
    return {
        "goal": "Answer using only approved documents with citations.",
        "question": question,
        "steps": [
            "Retrieve relevant evidence chunks from the vector database",
            "Write an answer grounded only in the evidence, with citations",
            "Verify the answer is supported by evidence (no hallucinations)",
            "If verification fails, revise once using verifier feedback",
        ],
    }
