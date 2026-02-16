from __future__ import annotations

import os
from typing import Any, Dict, Tuple, Union
from agents.deliverer import NOT_FOUND_EXACT as NOT_FOUND
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NOT_FOUND = "Not found in provided sources."


def write_answer(
    question: str,
    evidence_pack: str,
    return_meta: bool = False,
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """
    Writer agent:
    - Uses an LLM to answer ONLY using the evidence pack.
    - Citations must be copied EXACTLY from evidence (including full [Doc | chunk] format).
    - If evidence doesn't contain the answer, returns NOT_FOUND exactly.
    - If return_meta=True, also returns token usage + model for observability.
    """
    if not evidence_pack.strip():
        return (NOT_FOUND, {"model": None, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}) if return_meta else NOT_FOUND

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = OpenAI()

    system = (
        "You are an HR Ops copilot for Kosovo.\n"
        "RULES (must follow):\n"
        "1) Use ONLY the provided evidence excerpts.\n"
        f"2) If the evidence does NOT contain the answer, reply EXACTLY: {NOT_FOUND}\n"
        "3) Do NOT use outside knowledge.\n"
        "4) Every paragraph MUST include at least ONE citation.\n"
        "5) Citations MUST be copied EXACTLY from the evidence. Do NOT shorten, rename, or reformat them.\n"
        "6) Do NOT combine multiple citations inside one bracket. Use separate brackets if needed.\n"
        "7) Never invent citations.\n"
    )

    user = (
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE (use only this):\n{evidence_pack}\n\n"
        "Write a clear, practical answer for HR. Keep it concise but helpful.\n"
        f"If the answer is not directly supported by the evidence, return exactly: {NOT_FOUND}"
    )

    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    text = (resp.choices[0].message.content or "").strip()

    usage = getattr(resp, "usage", None)
    meta = {
        "model": model,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
    }

    return (text, meta) if return_meta else text
