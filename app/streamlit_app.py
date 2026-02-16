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
    page_icon="🤖",
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
        padding-top: 2rem;
        padding-bottom: 1rem;
        max-width: 1000px;
    }

    /* Messages container */
    .messages-container {
        padding: 20px;
        margin-bottom: 120px;
        min-height: 60vh;
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

    /* MAIN ANSWER - BIGGER AND MORE VISIBLE */
    .message-content {
        font-size: 18px !important;
        line-height: 1.8 !important;
        color: #f7fafc !important;
        font-weight: 500 !important;
        margin: 16px 0 !important;
        padding: 12px 0 !important;
        word-wrap: break-word;
        overflow-wrap: anywhere;
        white-space: normal;
    }

    /* Agent workflow - SMALLER */
    .agent-workflow-inline {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        background: #2d374880;
        border-radius: 8px;
        margin: 8px 0;
        font-size: 10px;
        opacity: 0.7;
        flex-wrap: wrap;
    }

    .agent-step-inline {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 3px 8px;
        border-radius: 6px;
        background: #1a202c;
        font-size: 10px;
    }

    .agent-step-inline.active { background: #667eea; }
    .agent-step-inline.completed { background: #48bb78; }

    /* Citation badge */
    .citation-badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        margin: 0 4px;
        white-space: nowrap;
        max-width: 100%;
    }

    /* Status badge - SMALLER */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        margin-top: 8px;
        text-transform: uppercase;
        opacity: 0.8;
    }

    .status-pass { background: #48bb78; color: white; }
    .status-fail { background: #f56565; color: white; }
    .status-unknown { background: #718096; color: white; }

    /* Not found message */
    .not-found {
        background: #744210;
        border: 2px solid #ed8936;
        color: #fbd38d;
        padding: 16px 20px;
        border-radius: 12px;
        font-weight: 600;
        text-align: center;
        font-size: 16px;
        margin: 12px 0;
    }

    /* Citations section */
    .citations-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #2d3748;
    }

    .citations-title {
        font-size: 11px;
        color: #718096;
        margin-bottom: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Metrics - SMALLER */
    .metrics-row { display: flex; gap: 8px; margin: 10px 0; }
    .metric-box { flex: 1; background: #2d3748; padding: 8px; border-radius: 6px; text-align: center; }
    .metric-value { font-size: 16px; font-weight: 700; color: #667eea; }
    .metric-label { font-size: 9px; color: #a0aec0; text-transform: uppercase; margin-top: 2px; }

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
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    .chat-title { color: white; font-size: 24px; font-weight: 700; margin: 0; }
    .chat-subtitle { color: rgba(255, 255, 255, 0.9); font-size: 14px; margin-top: 4px; }

    /* Evidence card - SMALLER */
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
</style>
""",
    unsafe_allow_html=True,
)

# ==================== HELPER FUNCTIONS ====================


def now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def safe_html(text: str) -> str:
    """
    Escape user/LLM text so it can't inject HTML/JS into unsafe_allow_html blocks.
    Also keeps newlines readable.
    """
    if text is None:
        return ""
    return html.escape(str(text)).replace("\n", "<br>")


def extract_citations_from_text(text: str):
    """Extract all citations from answer text like [file | chunk]"""
    if not text:
        return []
    return re.findall(r"\[([^\]]+)\]", text)


def highlight_citations_in_text(text: str) -> str:
    """Replace citations with styled badges (safe against HTML injection)."""
    if not text:
        return ""

    # Escape the whole text first (prevents injection)
    escaped = safe_html(text)

    def replace_citation(match):
        citation_text = match.group(1)
        full_title = citation_text
        display_text = citation_text if len(citation_text) < 40 else citation_text[:37] + "..."
        return f'<span class="citation-badge" title="{full_title}">{display_text}</span>'

    return re.sub(r"\[([^\]]+)\]", replace_citation, escaped)


def render_agent_workflow_inline(steps_completed: list[int]):
    """Render compact inline agent workflow"""
    all_steps = [("📋", "Plan"), ("🔍", "Research"), ("✍️", "Write"), ("✅", "Verify")]

    html_out = '<div class="agent-workflow-inline">'
    for i, (icon, label) in enumerate(all_steps):
        if i < len(steps_completed):
            status_class = "completed" if i < len(steps_completed) - 1 else "active"
        else:
            status_class = ""
        html_out += f'<div class="agent-step-inline {status_class}">{icon} {label}</div>'
    html_out += "</div>"
    return html_out


def run_question(question: str, k: int, company_name: str = "KosovoTech LLC"):
    """Run the workflow safely and always return a result dict."""
    try:
        return answer_question(question, k=k, company_name=company_name)
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
    st.markdown("### 🤖 HR Ops Copilot")
    st.markdown(
        '<div style="font-size: 12px; color: #a0aec0; margin-bottom: 20px;">Kosovo Labor Laws & Policies</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### ⚙️ Settings")

    company_name = st.text_input("🏢 Company name", value="KosovoTech LLC")
    output_mode = st.radio("🧾 Output mode", ["Executive", "Analyst"], horizontal=True, index=0)

    k = st.slider("📊 Retrieved chunks", min_value=3, max_value=10, value=6)
    show_details = st.checkbox("🔍 Show details", value=False)
    show_citations_list = st.checkbox("📚 Show citations", value=True)

    st.markdown("---")
    st.markdown("### 💡 Example Questions")

    examples = [
        "What is the remote work policy?",
        "What are the official holidays in Kosovo?",
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
        '<div class="info-box">💡 <strong>Tip:</strong> Press Enter to submit your question. All answers include verified citations.</div>',
        unsafe_allow_html=True,
    )

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.pop("pending_question", None)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== INITIALIZE SESSION ====================
st.session_state.setdefault("conversation_history", [])

# ==================== HEADER ====================
st.markdown(
    """
<div class="chat-header">
    <div class="chat-title">💼 Kosovo HR Operations Assistant</div>
    <div class="chat-subtitle">Ask questions about labor laws and company policies • All answers are verified with citations</div>
</div>
""",
    unsafe_allow_html=True,
)

# ==================== CONVERSATION AREA ====================
with st.container():
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)

    if not st.session_state.conversation_history:
        st.markdown(
            """
        <div style="text-align: center; padding: 60px 20px; color: #a0aec0;">
            <div style="font-size: 48px; margin-bottom: 16px;">👋</div>
            <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Welcome to HR Ops Copilot</div>
            <div style="font-size: 14px;">Ask me anything about Kosovo labor laws or company policies</div>
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
                <div class="message-header">👤 You • {safe_html(timestamp)}</div>
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

            is_not_found = answer.strip().startswith("Not found in the sources.")

            st.markdown('<div class="ai-message">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="message-header">🤖 HR Copilot • {safe_html(timestamp)}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(render_agent_workflow_inline([1, 2, 3, 4]), unsafe_allow_html=True)

            if is_not_found:
                st.markdown(f'<div class="not-found">⚠️ {safe_html(answer)}</div>', unsafe_allow_html=True)
            else:
                highlighted_answer = highlight_citations_in_text(answer)
                st.markdown(f'<div class="message-content">{highlighted_answer}</div>', unsafe_allow_html=True)

            status = str(verdict.get("status", "UNKNOWN")).upper()
            if status == "PASS":
                status_class, status_icon = "status-pass", "✓"
            elif status == "FAIL":
                status_class, status_icon = "status-fail", "✗"
            else:
                status_class, status_icon = "status-unknown", "?"

            st.markdown(
                f'<div class="status-badge {status_class}">{status_icon} {safe_html(status)}</div>',
                unsafe_allow_html=True,
            )

            if show_citations_list and not is_not_found:
                citations = extract_citations_from_text(answer)
                if citations:
                    st.markdown('<div class="citations-section">', unsafe_allow_html=True)
                    st.markdown('<div class="citations-title">📚 Sources Used</div>', unsafe_allow_html=True)
                    for cite in citations:
                        st.markdown(f'<span class="citation-badge">{safe_html(cite)}</span>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            if show_details:
                citations_count = len(extract_citations_from_text(answer)) if not is_not_found else 0
                sources_count = len(evidence) if isinstance(evidence, list) else 0

                st.markdown(
                    f"""
                <div class="metrics-row">
                    <div class="metric-box">
                        <div class="metric-value">{sources_count}</div>
                        <div class="metric-label">Sources</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{citations_count}</div>
                        <div class="metric-label">Citations</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{safe_html(status)}</div>
                        <div class="metric-label">Status</div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                with st.expander("📋 Plan"):
                    st.markdown(f"**Goal:** {plan.get('goal','')}")
                    st.markdown("**Steps:**")
                    for i, step in enumerate(plan.get("steps", []) or [], 1):
                        st.markdown(f"{i}. {step}")

                with st.expander("🔍 Evidence"):
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

                with st.expander("✅ Verification"):
                    st.json(verdict)

                with st.expander("📦 Final Deliverable (Executive Summary + Email + Actions + Sources)"):
                    if deliverable:
                        st.markdown("### Executive Summary (≤150 words)")
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

                    with st.expander("📈 Observability (latency + tokens + errors)"):
                        if trace:
                            st.table(trace)

                            total_ms = sum(int(x.get("ms", 0) or 0) for x in trace)
                            total_tokens = sum(int(x.get("total_tokens", 0) or 0) for x in trace)

                            st.markdown(f"**Total latency:** {total_ms} ms")
                            st.markdown(f"**Total tokens (LLM calls):** {total_tokens}")
                        else:
                            st.write("No trace available.")

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== INPUT AREA ====================
pending = st.session_state.pop("pending_question", None)
if pending:
    q = pending.strip()
    if q:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        with st.spinner("🤔 Processing..."):
            result = run_question(q, k=k, company_name=company_name)

        st.session_state.conversation_history.append({"role": "assistant", "content": result, "timestamp": now_hhmm()})
        st.rerun()

if prompt := st.chat_input("Ask your HR question here... (Press Enter to submit)", key="chat_input"):
    q = prompt.strip()
    if q:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        with st.spinner("🤔 Processing..."):
            result = run_question(q, k=k, company_name=company_name)

        st.session_state.conversation_history.append({"role": "assistant", "content": result, "timestamp": now_hhmm()})
        st.rerun()
