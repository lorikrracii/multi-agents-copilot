from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# MUST match rubric / workflow
NOT_FOUND = "Not found in the sources."


def write_answer(question: str, evidence_pack: str) -> str:
    """
    Writer agent:
    - Uses an LLM to answer, but ONLY using the evidence pack.
    - Must cite sources like: [DocName | chunk_id]
    - If evidence doesn't contain the answer, must return NOT_FOUND exactly.
    """
    if not evidence_pack.strip():
        return NOT_FOUND

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = OpenAI()

    system = (
        "You are an HR Ops copilot for Kosovo.\n"
        "STRICT RULES (must follow):\n"
        "1) Use ONLY the provided evidence excerpts.\n"
        f"2) If the evidence does NOT explicitly answer the question, reply EXACTLY:\n{NOT_FOUND}\n"
        "   2a) If evidence says the topic is 'not defined', 'not specified', 'depends on another policy', "
        "or points to a missing document (e.g., finance policy not provided), treat that as NOT_FOUND.\n"
        "3) Do NOT use outside knowledge.\n"
        "4) Every paragraph must include at least one citation copied EXACTLY from the evidence "
        "(keep the brackets), e.g. [Remote_and_Hybrid_Work_Policy.md | Remote_and_Hybrid_Work_Policy_chunk_0001].\n"
        "5) Never invent citations (no made-up things like [Company Finance Policy]).\n"
        "6) Never put multiple citations inside ONE bracket. Use separate brackets.\n"
    )

    user = (
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE (use only this):\n{evidence_pack}\n\n"
        "Write a clear, practical HR answer.\n"
        f"If NOT_FOUND, output only this exact line:\n{NOT_FOUND}"
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    return resp.choices[0].message.content.strip()
