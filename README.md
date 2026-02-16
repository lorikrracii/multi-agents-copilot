# Enterprise Multi-Agent HR Ops Copilot (Kosovo)

A small enterprise-style **multi-agent copilot** that answers HR Ops questions **only from provided sources** (company policies + Kosovo laws), produces a **structured final deliverable**, and shows **agent trace / observability**.  
Includes a **Streamlit UI**, a **CLI smoke test**, and an **evaluation set**.

---

## What this system does

### Required final output (always produced)

For every user question, the system returns a `deliverable` object containing:

- **Executive Summary** (≤ 150 words)
- **Client-ready Email** (subject + body)
- **Action List** (owner, due date, confidence)
- **Sources and citations**
- **Workflow status** (PASS/FAIL)

### User stories supported

- As a user, I submit a task (question + goal) and the system creates a plan and executes it using multiple agents.
- As a user, I can see which agent did what (trace/logs) and which sources were used (citations).
- As a user, I receive a final deliverable that is structured and usable (not raw chat text).
- As a user, if evidence is missing, the system clearly says **Not found in provided sources** and suggests what is needed.

---

## Architecture

### Agents

- **Planner**: creates a short plan for the question.
- **Research**: retrieves top-K chunks from Chroma Vector DB (citations included).
- **Writer**: generates an answer **strictly from evidence** and adds citations.
- **Verifier**: enforces citation integrity (no hallucinated sources).
- **Deliverer**: formats the required final deliverable (summary/email/actions/sources) **without extra LLM calls**.

### Orchestration

- Implemented using **LangGraph** (`agents/workflow.py`).
- One revision loop max:
  - If verifier FAILs → writer revises once using verifier feedback → re-verify.

### Storage / Retrieval

- ChromaDB persistent storage in: `storage/chroma`
- Collection name: `hr_docs`
- Retrieval code: `retrieval/retriever.py`

### UI

- Streamlit chat UI: `app/streamlit_app.py`
- Displays:
  - Answer (with citation badges)
  - PASS/FAIL status
  - Deliverable block (summary/email/actions/sources)
  - Trace / observability (latency, model, tokens, etc.)

---

## Project Structure

multi-agents-copilot/
├─ agents/
│ ├─ workflow.py # LangGraph orchestration + trace
│ ├─ planner.py # Planning agent
│ ├─ research.py # Retrieval agent (evidence pack)
│ ├─ writer.py # LLM writer (evidence-only) + usage meta
│ ├─ verifier.py # Citation integrity checks
│ └─ deliverer.py # Final deliverable builder
├─ retrieval/
│ ├─ retriever.py # Chroma + embeddings search
│ └─ citations.py # Citation formatting helper (if present)
├─ app/
│ └─ streamlit_app.py # Streamlit UI
├─ eval/
│ ├─ questions.json # Evaluation set (10 questions)
│ ├─ run_eval.py # Runs evaluation + saves report
│ └─ report.json # Output report (generated)
├─ docs/ # Source documents (PDF/MD)
├─ storage/chroma/ # Vector store (generated)
├─ requirements.txt
└─ README.md
