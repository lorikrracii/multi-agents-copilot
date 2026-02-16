import sys
from pathlib import Path
import re
import html
from datetime import datetime

# Ensure repo root is on PYTHONPATH (fixes: No module named 'agents')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from agents.workflow import answer_question

# ==================== PAGE CONFIG (must be first Streamlit call) ====================
st.set_page_config(
    page_title="Kosovo HR Ops Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== CUSTOM CSS ====================
st.markdown(
    """
<style>
    /* Main app styling */
    .main { background: #0f1419; }
    .stApp { background: #0f1419; }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 1000px;
    }

    /* Messages container (min-height is overridden dynamically below) */
    .messages-container {
        padding: 20px;
        margin-bottom: 120px;
    }

    /* User message */
    .user-message {
        background: #2d3748;
        color: #e2e8f0;
        padding: 16px 20px;
        border-radius: 16px;
        margin: 16px 0;
        margin-left: 20%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        font-size: 15px;
        line-height: 1.6;
        animation: slideInRight 0.3s ease;
    }

    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* AI message */
    .ai-message {
        background: #1a202c;
        border: 1px solid #2d3748;
        color: #e2e8f0;
        padding: 20px;
        border-radius: 16px;
        margin: 16px 0;
        margin-right: 20%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        animation: slideInLeft 0.3s ease;
    }

    .message-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-weight: 600;
        font-size: 11px;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* MAIN ANSWER */
    .message-content {
        font-size: 18px !important;
        line-height: 1.8 !important;
        color: #f7fafc !important;
        font-weight: 500 !important;
        margin: 10px 0 8px 0 !important;
        padding: 8px 0 !important;
        word-wrap: break-word;
        overflow-wrap: anywhere;
        white-space: normal;
    }

    /* Not found message */
    .not-found {
        background: rgba(237, 137, 54, 0.10);
        border: 1px solid #ed8936;
        color: #fbd38d;
        padding: 14px 18px;
        border-radius: 12px;
        font-weight: 650;
        text-align: center;
        font-size: 15px;
        margin: 10px 0 6px 0;
    }

    /* Sources at end of answer */
    .sources-row {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #2d3748;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
    }

    .sources-title {
        font-size: 11px;
        color: #a0aec0;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 6px;
        opacity: 0.9;
    }

    .source-chip {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        background: #2d3748;
        border: 1px solid #4a5568;
        color: #e2e8f0;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Streamlit chat input styling */
    .stChatInput { background: #1a202c !important; border-top: 2px solid #2d3748 !important; }
    .stChatInput textarea {
        background: #2d3748 !important;
        color: #e2e8f0 !important;
        border: 2px solid #4a5568 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }
    .stChatInput textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }

    /* Button styling */
    .stButton>button {
        background: #667eea !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover { background: #5a67d8 !important; transform: translateY(-1px); }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #1a202c; }
    [data-testid="stSidebar"] .element-container { color: #e2e8f0; }

    /* Info box */
    .info-box {
        background: #2d3748;
        border-left: 4px solid #667eea;
        padding: 14px;
        border-radius: 8px;
        margin: 12px 0;
        font-size: 13px;
        color: #cbd5e0;
        line-height: 1.6;
    }

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Header */
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 18px 20px;
        border-radius: 12px;
        margin-bottom: 0px;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    .chat-title { color: white; font-size: 24px; font-weight: 700; margin: 0; }
    .chat-subtitle { color: rgba(255, 255, 255, 0.9); font-size: 14px; margin-top: 2px; }

    /* Welcome (transparent card inside messages container) */
    .welcome-wrap {
        text-align: center;
        padding: 18px 14px;
        margin: 8px 0 2px 0;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid #2d3748;
        border-radius: 16px;
        color: #a0aec0;
    }
    .welcome-emoji { font-size: 34px; margin-bottom: 6px; }
    .welcome-title { font-size: 18px; font-weight: 650; margin-bottom: 4px; color: #e2e8f0; }
    .welcome-sub { font-size: 13px; }

    /* Evidence card */
    .evidence-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 10px;
        margin: 6px 0;
        font-size: 12px;
    }
    .evidence-header { color: #a0aec0; font-weight: 600; margin-bottom: 4px; font-size: 11px; }
    .evidence-text { color: #cbd5e0; line-height: 1.5; font-size: 12px; }

    /* Visible assistant "thinking" bubble */
    .typing-message {
        background: #1a202c;
        border: 1px dashed #4a5568;
        color: #e2e8f0;
        padding: 18px 20px;
        border-radius: 16px;
        margin: 16px 0;
        margin-right: 20%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        animation: slideInLeft 0.25s ease;
    }
    .typing-line {
        font-size: 15px;
        color: #cbd5e0;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 2px;
    }
    .typing-dots {
        display: inline-flex;
        gap: 4px;
    }
    .typing-dots span {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: #a0aec0;
        opacity: 0.35;
        animation: dotPulse 1.2s infinite ease-in-out;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes dotPulse {
        0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
        40% { opacity: 1; transform: translateY(-2px); }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==================== HELPER FUNCTIONS ====================


def now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def safe_html(text: str) -> str:
    if text is None:
        return ""
    return html.escape(str(text)).replace("\n", "<br>")


def strip_citations(text: str) -> str:
    """Remove [ ... ] citations from answer so sources can be shown only at the end."""
    if not text:
        return ""
    cleaned = re.sub(r"\s*\[[^\]]+\]\s*", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Fix spacing before punctuation
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned


def extract_sources(text: str) -> list[str]:
    """
    Extract citations from answer, supports:
      [A | x]
      [A | x; B | y]
      [A | x, B | y]
    Returns unique sources preserving order.
    """
    if not text:
        return []
    groups = re.findall(r"\[([^\]]+)\]", text)
    out = []
    seen = set()
    for g in groups:
        parts = re.split(r"\s*[;,]\s*", g.strip())
        for p in parts:
            p = p.strip()
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return out


# Fixed company name (removed from sidebar as requested)
COMPANY_NAME = "KosovoTech LLC"


def run_question(question: str, k: int):
    try:
        return answer_question(question, k=k, company_name=COMPANY_NAME)
    except Exception as e:
        return {
            "answer": "Not found in the sources.",
            "verdict": {"status": "FAIL", "error": str(e)},
            "evidence": [],
            "plan": {"goal": "Handle error", "steps": ["Caught exception in UI wrapper."]},
            "deliverable": {},
            "trace": [],
        }


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown('<div style="padding: 16px;">', unsafe_allow_html=True)
    st.markdown("### HR Ops Copilot")
    st.markdown(
        '<div style="font-size: 12px; color: #a0aec0; margin-bottom: 16px;">Kosovo Labor Laws & Policies</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Settings")

    k_label_to_value = {"Small": 4, "Standard": 6, "Deep": 8}
    k_choice = st.radio("Retrieval depth", list(k_label_to_value.keys()), horizontal=True, index=1)
    k = k_label_to_value[k_choice]

    show_details = st.checkbox("Show details", value=False)
    show_sources = st.checkbox("Show sources", value=True)

    st.markdown("---")
    st.markdown("### Example Questions")

    examples = [
        "What is the remote work policy?",
        "List the official holidays in Kosovo according to Law 03-L-064.",
        "Maximum working hours per week?",
        "Safety requirements at work?",
        "Gender equality policy?",
        "Available leave types?",
    ]

    for example in examples:
        key = f"ex_{abs(hash(example))}"
        if st.button(example, key=key, use_container_width=True):
            st.session_state.pending_question = example
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<div class="info-box"><strong>Tip:</strong> Press Enter to submit your question. Answers include verified citations.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.pop("pending_question", None)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== INITIALIZE SESSION ====================
st.session_state.setdefault("conversation_history", [])
st.session_state.setdefault("inflight_question", None)
st.session_state.setdefault("assistant_typing_since", None)

# Dynamic: messages container is smaller when empty
is_empty = len(st.session_state.conversation_history) == 0
min_h = "20vh" if is_empty else "60vh"
mb = "80px" if is_empty else "120px"
st.markdown(
    f"<style>.messages-container{{min-height:{min_h}; margin-bottom:{mb};}}</style>",
    unsafe_allow_html=True,
)

# ==================== HEADER ====================
st.markdown(
    """
<div class="chat-header">
    <div class="chat-title">Kosovo HR Operations Assistant</div>
    <div class="chat-subtitle">Ask questions about labor laws and company policies. All answers are verified with citations.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ==================== CONVERSATION AREA ====================
with st.container():
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)

    # Welcome (transparent card inside container)
    if not st.session_state.conversation_history:
        st.markdown(
            """
        <div class="welcome-wrap">
            <div class="welcome-emoji"></div>
            <div class="welcome-title">Welcome to HR Ops Copilot</div>
            <div class="welcome-sub">Ask me anything about Kosovo labor laws or company policies</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    for message in st.session_state.conversation_history:
        role = message.get("role", "")
        timestamp = message.get("timestamp", "--:--")

        if role == "user":
            st.markdown(
                f"""
            <div class="user-message">
                <div class="message-header">You - {safe_html(timestamp)}</div>
                <div class="message-content">{safe_html(message.get("content",""))}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            result = message.get("content") or {}
            answer = result.get("answer", "")
            verdict = result.get("verdict", {}) or {}
            evidence = result.get("evidence", []) or []
            plan = result.get("plan", {}) or {}
            deliverable = result.get("deliverable", {}) or {}
            trace = result.get("trace", []) or []

            is_not_found = answer.strip().startswith("Not found")

            st.markdown('<div class="ai-message">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="message-header">HR Copilot - {safe_html(timestamp)}</div>',
                unsafe_allow_html=True,
            )

            # No more Plan/Research/Write/Verify pills here (removed)

            if is_not_found:
                st.markdown(f'<div class="not-found">{safe_html(answer)}</div>', unsafe_allow_html=True)
            else:
                answer_clean = strip_citations(answer)
                st.markdown(f'<div class="message-content">{safe_html(answer_clean)}</div>', unsafe_allow_html=True)

                # Sources ONLY at the end
                if show_sources:
                    sources = extract_sources(answer)
                    if sources:
                        chips = "".join(
                            f'<span class="source-chip" title="{html.escape(s)}">{html.escape(s)}</span>'
                            for s in sources
                        )
                        st.markdown(
                            f"""
                            <div class="sources-row">
                                <span class="sources-title">Sources</span>
                                {chips}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            # No PASS/FAIL badge shown under each answer anymore (removed)
            # If you want it, keep it ONLY inside Show details.

            if show_details:
                status = str(verdict.get("status", "UNKNOWN")).upper()
                citations_count = len(extract_sources(answer)) if not is_not_found else 0
                sources_count = len(evidence) if isinstance(evidence, list) else 0

                st.markdown(
                    f"""
                <div style="margin-top: 10px; opacity: 0.9;">
                    <div style="display:flex; gap:8px;">
                        <div style="flex:1; background:#2d3748; padding:8px; border-radius:8px; text-align:center;">
                            <div style="font-size:16px; font-weight:800; color:#667eea;">{sources_count}</div>
                            <div style="font-size:10px; color:#a0aec0; text-transform:uppercase;">Retrieved</div>
                        </div>
                        <div style="flex:1; background:#2d3748; padding:8px; border-radius:8px; text-align:center;">
                            <div style="font-size:16px; font-weight:800; color:#667eea;">{citations_count}</div>
                            <div style="font-size:10px; color:#a0aec0; text-transform:uppercase;">Cited</div>
                        </div>
                        <div style="flex:1; background:#2d3748; padding:8px; border-radius:8px; text-align:center;">
                            <div style="font-size:16px; font-weight:800; color:#667eea;">{html.escape(status)}</div>
                            <div style="font-size:10px; color:#a0aec0; text-transform:uppercase;">Verdict</div>
                        </div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                with st.expander("Plan"):
                    st.markdown(f"**Goal:** {plan.get('goal','')}")
                    st.markdown("**Steps:**")
                    for i, step in enumerate(plan.get("steps", []) or [], 1):
                        st.markdown(f"{i}. {step}")

                with st.expander("Evidence"):
                    if isinstance(evidence, list):
                        for i, ev in enumerate(evidence, 1):
                            cite = safe_html(ev.get("citation", f"Source {i}"))
                            txt = ev.get("text", "")
                            snippet = txt[:400] + ("..." if len(txt) > 400 else "")
                            st.markdown(
                                f"""
                            <div class="evidence-card">
                                <div class="evidence-header">Source {i}: {cite}</div>
                                <div class="evidence-text">{safe_html(snippet)}</div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(safe_html(str(evidence)), unsafe_allow_html=True)

                with st.expander("Verification"):
                    st.json(verdict)

                with st.expander("Final Deliverable (Executive Summary + Email + Actions + Sources)"):
                    if deliverable:
                        st.markdown("### Executive Summary (<=150 words)")
                        st.write(deliverable.get("executive_summary", ""))

                        st.markdown("### Client-ready Email")
                        email = deliverable.get("client_email", {}) or {}
                        st.markdown(f"**Subject:** {email.get('subject','')}")
                        st.text(email.get("body", ""))

                        st.markdown("### Action List")
                        actions = deliverable.get("action_list", []) or []
                        if actions:
                            st.table(actions)
                        else:
                            st.write("No actions generated.")

                        st.markdown("### Sources")
                        srcs = deliverable.get("sources", []) or []
                        if srcs:
                            for s in srcs:
                                st.markdown(f"- {s}")
                        else:
                            st.write("No sources.")
                    else:
                        st.write("No deliverable produced.")

                with st.expander("Observability (trace)"):
                    if trace:
                        st.table(trace)
                    else:
                        st.write("No trace available.")

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.inflight_question:
        st.markdown(
            f"""
        <div class="typing-message">
            <div class="message-header">HR Copilot - {safe_html(st.session_state.assistant_typing_since or "--:--")}</div>
            <div class="typing-line">
                Preparing a verified answer
                <span class="typing-dots"><span></span><span></span><span></span></span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== INPUT AREA ====================
queued = st.session_state.pop("pending_question", None)
if queued and not st.session_state.inflight_question:
    q = queued.strip()
    if q:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        st.session_state.inflight_question = q
        st.session_state.assistant_typing_since = now_hhmm()
        st.rerun()

if prompt := st.chat_input("Ask your HR question here... (Press Enter to submit)", key="chat_input"):
    q = prompt.strip()
    if q and not st.session_state.inflight_question:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        st.session_state.inflight_question = q
        st.session_state.assistant_typing_since = now_hhmm()
        st.rerun()

if st.session_state.inflight_question:
    with st.spinner("Processing..."):
        result = run_question(st.session_state.inflight_question, k=k)

    st.session_state.conversation_history.append({"role": "assistant", "content": result, "timestamp": now_hhmm()})
    st.session_state.inflight_question = None
    st.session_state.assistant_typing_since = None
    st.rerun()
