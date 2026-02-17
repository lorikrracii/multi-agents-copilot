# 💼 Kosovo HR Ops Multi-Agent Copilot

**Project #6 — Enterprise Multi-Agent Copilot (HR Operations)**

A production-oriented **Enterprise-style Multi-Agent Copilot** for **HR Operations in Kosovo**, grounded in **Kosovo public labor-law PDFs** and **company policy templates (Markdown)**. It answers HR questions using **Retrieval-Augmented Generation (RAG)** plus a **multi-agent workflow** (Planner → Research → Writer → Verifier → Deliverer), with **strict anti-hallucination rules**, **citations**, and **trace-friendly outputs**.

This project is designed to behave like an **enterprise HR compliance assistant**—not a generic chatbot.

---

## 🎯 Project Goal

The goal is to build a copilot that:

- Retrieves the **most relevant evidence** from your HR document set
- Generates **grounded answers with citations**
- Produces a **decision-ready structured deliverable** (not just chat text)
- **Refuses to answer** when the information is missing in the sources
- Exposes **agent traceability** (plan, evidence, verification status)

**Hard rule (anti-hallucination):**  
If evidence does not contain the answer, the system must output exactly:

> **`Not found in provided sources.`**

---

## 📄 Knowledge Base: Document Scope & Meaning

This project is grounded in two document categories:

### 🏛️ Kosovo Public Laws (PDFs)

Stored in: `data/public_kosovo/`

Examples (EN PDFs):

- Constitution (Consolidated)
- Labour Law
- Official Holidays
- Safety & Health at Work
- Gender Equality
- Anti-Discrimination
- Personal Data Protection

### 🧾 Company Policy Templates (Markdown)

Stored in: `data/company_policies_synthetic/`

Examples:

- `Employee_Handbook.md`
- `Recruitment_Equal_Opportunity_Policy.md`
- `Remote_and_Hybrid_Work_Policy.md`
- `PTO_and_Leave_Policy.md`
- `Complaints_and_Disciplinary_Procedure.md`

### ✅ Why these documents were chosen

These docs are ideal for an enterprise copilot because HR Ops questions require:

- **Exact wording + compliance correctness**
- **Citations you can audit**
- **Refusal behavior** when policy/law is not present
- Clear separation between **public law** vs **internal policy**

---

## 🧩 Core Functionality

### ✅ RAG / Retrieval Pipeline (ChromaDB)

**Flow:** PDFs/MD → chunks → embeddings → vector DB → top-k retrieval

- Persistent vector store: `storage/chroma/`
- Collection name: `hr_docs`
- Retriever returns: `text` + `citation` + metadata
- Citations format example:
  - `[Remote_and_Hybrid_Work_Policy.md | Remote_and_Hybrid_Work_Policy_chunk_0000]`
  - `[KOS_Law_03-L-212_Labour_EN.pdf | p.12 | ...chunk_0007]`

---

## 🧠 Multi-Agent Workflow (Enterprise-style)

This copilot runs as a coordinated workflow (Planner → Research → Writer → Verifier → Deliverer):

### 1) 📋 Planner Agent

Produces a short, deterministic plan (enterprise explainability).

### 2) 🔍 Research Agent

Retrieves the top-k most relevant chunks and builds an **evidence pack**.

### 3) ✍️ Writer Agent (Strict Grounding)

Generates an answer **only from the evidence pack**, enforcing:

- Every paragraph must include citations
- No external knowledge
- If missing → **`Not found in provided sources.`**

### 4) ✅ Verifier Agent (Citation Integrity Gate)

Blocks unsupported claims by checking:

- Every citation in the answer exists in the evidence pack
- Every paragraph has at least one citation (unless NOT_FOUND)
- If FAIL → one controlled revision attempt

### 5) 📦 Deliverer (Structured Output Builder)

Builds the required deliverable **without additional LLM calls** (predictable + grounded):

- Executive Summary (≤150 words)
- Client-ready Email
- Action List (owner, due date, confidence)
- Sources

**IMPORTANT behavior:**  
If NOT_FOUND → **Sources list must be empty** (avoids misleading “random sources”).

---

## 📦 Required Deliverables (System Output)

For every user question, the system outputs:

- **Executive Summary** (≤150 words)
- **Client-ready Email**
- **Action List** (owner, due date, confidence)
- **Sources / citations**

---

## 🎛️ User Interface (Streamlit Demo)

Built with **Streamlit** (`app/streamlit_app.py`) with:

- Chat-style UI
- Slider for `k` retrieved chunks
- Toggle for “Show details” (plan, evidence, verifier JSON)
- Answer display with citations
- Verifier PASS/FAIL badge

Run command:

```bash
streamlit run app/streamlit_app.py
```

## ⭐ Nice-to-Have Features - Implemented

| Feature                                                           | Status         |
| :---------------------------------------------------------------- | :------------- |
| Multi-agent workflow (Planner→Research→Writer→Verifier→Deliverer) | ✅ Implemented |
| Strict anti-hallucination (`Not found...`)                        | ✅ Implemented |
| Citations per answer                                              | ✅ Implemented |
| Persistent vector DB (Chroma)                                     | ✅ Implemented |
| Streamlit demo UI                                                 | ✅ Implemented |
| Controlled revision on verifier FAIL                              | ✅ Implemented |
| Evidence + verification viewing mode                              | ✅ Implemented |

## 🗂️ Repository Structure

```bash
app/ — Streamlit UI (demo interface)

agents/ — agents (planner, research, writer, verifier, deliverer, workflow)

retrieval/ — ingestion + retrieval + citations

data/ — Kosovo PDFs + synthetic policies

eval/ — evaluation runner + test set

storage/ — local ChromaDB files (ignored in Git)

run_ingest.py — ingestion runner

requirements.txt

README.md
```

## 🧪 Example Behaviors

**✔️ Grounded answers with citations**
**✔️ Enterprise-style structured deliverables**
**✔️ Verifier blocks unsupported claims**
**✔️ Clear refusal when evidence is missing**

**❌ No hallucinations**
**❌ No outside knowledge injection**

## 🚀 Quick Start (Local)

**1. Create & activate a virtual environment**

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**2. Install dependencies**

```bash
 pip install -r requirements.txt
```

**3. Configure environment variables**

Create a .env file in repo root:

```bash
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-small
```

.env must be ignored in Git.

Ingest documents into Chroma

Persistent Chroma store:

storage/chroma/

Collection: hr_docs

Run ingestion:

```bash
python run_ingest.py
```

Safe ingestion settings (PowerShell)

To avoid laptop overload:

```bash
$env:EMBED_BATCH_SIZE="6"
$env:MAX_PAGE_CHARS="40000"
$env:MAX_CHUNKS_PER_UNIT="180"
python run_ingest.py
```

Run Streamlit UI

```bash
streamlit run app/streamlit_app.py
```

## 🤖 Multi-Agent Workflow Test (CLI)

End-to-end test:

```bash
python -c "from agents.workflow import answer_question; out=answer_question('What is the remote work policy?', k=6); print(out['answer']); print(out['verdict']['status'])"
```

Expected behavior:

Answer contains citations

Verifier returns PASS

If missing evidence: answer is exactly Not found in provided sources.

## 🧪 Evaluation (10 test questions)

Run:

```bash
python eval/run_eval.py
```

Outputs:

eval/report.json — summary results

Console PASS/FAIL per question (flags citation integrity issues)

## 🧠 Tech Stack

Python

LangGraph (agent orchestration)

ChromaDB (vector store)

OpenAI (embeddings + LLM)

Streamlit (UI demo)
