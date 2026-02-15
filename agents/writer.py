from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NOT_FOUND = "Not found in provided sources."


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
        "RULES (must follow):\n"
        "1) Use ONLY the provided evidence excerpts.\n"
        f"2) If the evidence does NOT contain the answer, reply EXACTLY: {NOT_FOUND}\n"
        "3) Do NOT use outside knowledge.\n"
        "4) Every paragraph must include at least one citation copied from the evidence "
        "(example: [Remote_and_Hybrid_Work_Policy.md | Remote_and_Hybrid_Work_Policy_chunk_0001]).\n"
        "5) Never invent citations.\n"
    )

    user = (
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE (use only this):\n{evidence_pack}\n\n"
        "Write a clear, practical answer for HR. Keep it concise but helpful.\n"
        "If the answer is not directly supported by the evidence, return the NOT_FOUND message."
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    return resp.choices[0].message.content.strip()
