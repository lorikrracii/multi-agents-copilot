import sys
from pathlib import Path
import re
import html
import textwrap
from datetime import datetime

# ==================== PATH SETUP ====================
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
    page_icon="🤖",
)

# ==================== HTML HELPER (fixes stray </div> due to Markdown indentation) ====================
def html_block(s: str) -> str:
    return textwrap.dedent(s).strip()

# ==================== CONSTANTS ====================
NOT_FOUND = "Not found in provided sources."
COMPANY_NAME = "KosovoTech LLC"

# ==================== DESIGN & CSS (your remodeled UI) ====================
st.markdown(
    html_block(
        """
        <style>
            /* --- GLOBAL RESET & THEME --- */
            .stApp { background-color: #0f172a; } /* Slate 900 */

            .block-container {
                padding-top: 2rem;
                padding-bottom: 8rem; /* Space for input bar */
                max-width: 900px;
            }

            h1, h2, h3, p, div {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            /* --- CHAT MESSAGE CONTAINERS --- */
            .chat-container {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            /* USER MESSAGE: Clean Blue Bubble, Aligned Right */
            .message-user-wrap {
                display: flex;
                justify-content: flex-end;
                align-items: flex-end;
                margin-bottom: 24px;
                animation: fadeIn 0.3s ease-out;
            }
            .user-content {
                background: linear-gradient(145deg, #3b82f6, #2563eb);
                color: #eff6ff;
                padding: 16px 20px;
                border-radius: 20px 20px 4px 20px;
                font-size: 15px;
                line-height: 1.6;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
                max-width: 80%;
                word-wrap: break-word;
                overflow-wrap: anywhere;
                white-space: normal;
            }
            .user-header {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: rgba(255,255,255,0.7);
                margin-bottom: 4px;
                text-align: right;
            }

            /* AI MESSAGE: Clean Dark Card, Aligned Left */
            .message-ai-wrap {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                align-items: flex-start;
                margin-bottom: 24px;
                animation: fadeIn 0.3s ease-out;
            }
            .ai-content {
                background: #1e293b; /* Slate 800 */
                border: 1px solid #334155;
                color: #e2e8f0;
                padding: 24px 24px;
                border-radius: 20px 20px 20px 4px;
                font-size: 16px;
                line-height: 1.8;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                max-width: 90%;
                margin-left: 0;
                word-wrap: break-word;
                overflow-wrap: anywhere;
                white-space: normal;
            }
            .ai-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #94a3b8;
                margin-bottom: 12px;
                width: 100%;
            }
            .ai-header-left {
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            .ai-header-right {
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }

            /* Verdict pill */
            .verdict-pill {
                font-size: 10px;
                font-weight: 800;
                padding: 4px 10px;
                border-radius: 999px;
                border: 1px solid transparent;
                letter-spacing: 0.6px;
            }
            .verdict-pass {
                color: #dcfce7;
                background: rgba(34, 197, 94, 0.15);
                border-color: rgba(34, 197, 94, 0.35);
            }
            .verdict-fail {
                color: #fee2e2;
                background: rgba(239, 68, 68, 0.12);
                border-color: rgba(239, 68, 68, 0.35);
            }
            .verdict-unknown {
                color: #e2e8f0;
                background: rgba(148, 163, 184, 0.12);
                border-color: rgba(148, 163, 184, 0.3);
            }

            /* --- SOURCE TAGS --- */
            .sources-row {
                margin-top: 16px;
                padding-top: 12px;
                border-top: 1px solid #334155;
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                align-items: center;
            }
            .sources-label {
                font-size: 11px;
                font-weight: 700;
                color: #64748b;
                text-transform: uppercase;
                margin-right: 6px;
            }
            .source-chip {
                background: #0f172a;
                border: 1px solid #475569;
                color: #cbd5e1;
                padding: 4px 12px;
                border-radius: 9999px;
                font-size: 11px;
                font-weight: 600;
                transition: all 0.2s ease;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                max-width: 100%;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .source-chip:hover {
                border-color: #3b82f6;
                color: #60a5fa;
                transform: translateY(-1px);
            }

            /* --- ERROR/NOT FOUND --- */
            .not-found {
                border-left: 4px solid #f59e0b;
                background: rgba(245, 158, 11, 0.1);
                color: #fcd34d;
                padding: 16px;
                border-radius: 8px;
                font-weight: 600;
                margin-top: 8px;
            }

            /* --- TYPING INDICATOR --- */
            .typing-box {
                background: #1e293b;
                border: 1px dashed #334155;
                padding: 16px;
                border-radius: 12px;
                color: #94a3b8;
                font-size: 14px;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                max-width: 360px;
                animation: pulse 2s infinite;
            }
            .typing-dots {
                display: inline-flex;
                gap: 4px;
            }
            .typing-dots span {
                width: 6px;
                height: 6px;
                border-radius: 999px;
                background: #94a3b8;
                opacity: 0.35;
                animation: dotPulse 1.2s infinite ease-in-out;
            }
            .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
            .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

            /* --- ANIMATIONS --- */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pulse {
                0% { opacity: 0.8; }
                50% { opacity: 1; }
                100% { opacity: 0.8; }
            }
            @keyframes dotPulse {
                0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
                40% { opacity: 1; transform: translateY(-2px); }
            }

            /* --- STREAMLIT OVERRIDES --- */
            .stChatInput {
                background-color: #0f172a !important;
                border-top: 1px solid #334155 !important;
            }
            .stChatInput textarea {
                background: #1e293b !important;
                color: #f1f5f9 !important;
                border: 1px solid #475569 !important;
                border-radius: 12px !important;
            }
            .stChatInput textarea:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 2px rgba(59,130,246,0.3) !important;
            }

            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none;}
        </style>
        """
    ),
    unsafe_allow_html=True,
)

# ==================== HELPERS ====================
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

def verdict_class(status: str) -> str:
    s = (status or "").upper()
    if s == "PASS":
        return "verdict-pass"
    if s == "FAIL":
        return "verdict-fail"
    return "verdict-unknown"

def run_question(question: str, k: int):
    """
    UI wrapper so the app doesn't crash.
    IMPORTANT: keep strict NOT_FOUND string.
    """
    try:
        # If your workflow accepts company_name:
        return answer_question(question, k=k, company_name=COMPANY_NAME)
    except TypeError:
        # Backward compat if answer_question doesn't accept company_name
        try:
            return answer_question(question, k=k)
        except Exception as e:
            return {
                "answer": NOT_FOUND,
                "verdict": {"status": "FAIL", "error": str(e)},
                "evidence": [],
                "plan": {"goal": "Handle error", "steps": ["Caught exception in UI wrapper."]},
                "deliverable": {},
                "trace": [],
            }
    except Exception as e:
        return {
            "answer": NOT_FOUND,
            "verdict": {"status": "FAIL", "error": str(e)},
            "evidence": [],
            "plan": {"goal": "Handle error", "steps": ["Caught exception in UI wrapper."]},
            "deliverable": {},
            "trace": [],
        }

def render_deliverable(deliverable: dict):
    """Pretty deliverable view."""
    if not deliverable:
        st.write("No deliverable produced.")
        return

    st.markdown("### Executive Summary (≤150 words)")
    st.write(deliverable.get("executive_summary", ""))

    st.markdown("### Client-ready Email")
    email = deliverable.get("client_email", {}) or {}
    subj = email.get("subject", "")
    body = email.get("body", "")
    if subj:
        st.markdown(f"**Subject:** {subj}")
    if body:
        st.text(body)
    else:
        st.write("No email body.")

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

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712139.png", width=50)
    st.markdown("### HR Ops Copilot")
    st.caption("Kosovo Labor Laws & Policies Assistant")

    st.markdown("---")

    k_label_to_value = {"Small": 4, "Standard": 6, "Deep": 8}
    k_choice = st.radio("Search Depth", list(k_label_to_value.keys()), index=1)
    k = k_label_to_value[k_choice]

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        show_sources = st.checkbox("Sources", value=True)
    with col2:
        show_details = st.checkbox("Debug", value=False)

    st.markdown("### Quick Examples")
    examples = [
        "What is the remote work policy?",
        "Official holidays in Kosovo (Law 03-L-064)?",
        "Maximum working hours per week?",
        "Safety requirements at work?",
    ]

    # IMPORTANT: stable unique keys (no collisions)
    for example in examples:
        if st.button(example, key=f"ex_{abs(hash(example))}", use_container_width=True):
            st.session_state.pending_question = example
            st.rerun()

    if st.button("Clear Chat", key="clear_chat", type="secondary", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.pop("pending_question", None)
        st.session_state.inflight_question = None
        st.session_state.assistant_typing_since = None
        st.rerun()

# ==================== SESSION STATE ====================
st.session_state.setdefault("conversation_history", [])
st.session_state.setdefault("inflight_question", None)
st.session_state.setdefault("assistant_typing_since", None)

# ==================== HEADER ====================
st.markdown(
    html_block(
        """
        <div style="text-align: center; margin-bottom: 40px; padding: 20px 0;">
            <h1 style="color: #f8fafc; margin-bottom: 8px;">HR Operations Assistant</h1>
            <p style="color: #94a3b8; font-size: 16px;">
                Verified answers on Kosovo labor laws and company policies.
            </p>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

# ==================== WELCOME (if empty) ====================
if not st.session_state.conversation_history:
    st.markdown(
        html_block(
            """
            <div style="text-align: center; padding: 40px; border: 1px dashed #334155; border-radius: 16px; margin: 0 auto; max-width: 600px; background: rgba(30, 41, 59, 0.5);">
                <div style="font-size: 40px; margin-bottom: 16px;">👋</div>
                <h3 style="color: #e2e8f0; margin-bottom: 8px;">Welcome to HR Copilot</h3>
                <p style="color: #94a3b8;">Ask me anything about contracts, leave policies, or compliance.</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

# ==================== CONVERSATION ====================
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg_idx, message in enumerate(st.session_state.conversation_history):
    role = message.get("role", "")
    timestamp = message.get("timestamp", "--:--")

    if role == "user":
        st.markdown(
            html_block(
                f"""
                <div class="message-user-wrap">
                    <div class="user-content">
                        <div class="user-header">You • {safe_html(timestamp)}</div>
                        {safe_html(message.get("content",""))}
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        continue

    # Assistant message
    result = message.get("content") or {}
    answer = result.get("answer", "") or ""
    verdict = result.get("verdict", {}) or {}
    evidence = result.get("evidence", []) or []
    plan = result.get("plan", {}) or {}
    deliverable = result.get("deliverable", {}) or {}
    trace = result.get("trace", []) or []

    status = str(verdict.get("status", "UNKNOWN")).upper()
    pill_cls = verdict_class(status)

    is_not_found = answer.strip() == NOT_FOUND or answer.strip().startswith("Not found")

    content_html = ""
    if is_not_found:
        content_html = f'<div class="not-found">{safe_html(NOT_FOUND)}</div>'
    else:
        answer_clean = strip_citations(answer)
        content_html = f"<div>{safe_html(answer_clean)}</div>"

        if show_sources:
            sources = extract_sources(answer)
            if sources:
                chips = "".join(
                    f'<span class="source-chip" title="{html.escape(s)}">{html.escape(s)}</span>'
                    for s in sources
                )
                content_html += html_block(
                    f"""
                    <div class="sources-row">
                        <span class="sources-label">Sources</span>
                        {chips}
                    </div>
                    """
                )

    st.markdown(
        html_block(
            f"""
            <div class="message-ai-wrap">
                <div class="ai-content">
                    <div class="ai-header">
                        <div class="ai-header-left">
                            <span>🤖 HR Copilot</span>
                            <span>• {safe_html(timestamp)}</span>
                        </div>
                        <div class="ai-header-right">
                            <span class="verdict-pill {pill_cls}">{safe_html(status)}</span>
                        </div>
                    </div>
                    {content_html}
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    # ==================== DEBUG ====================
    if show_details:
        with st.expander("🔍 View Analysis Details (Debug)", expanded=False):
            st.markdown(f"**Verdict Status:** `{status}`")
            if verdict.get("error"):
                st.error(f"Error: {verdict.get('error')}")

            tab1, tab2, tab3, tab4 = st.tabs(["Evidence", "Plan", "Deliverable", "Trace"])

            # Evidence FULL (no truncation)
            with tab1:
                if isinstance(evidence, list) and evidence:
                    for i, ev in enumerate(evidence, 1):
                        cite = ev.get("citation", f"Source {i}")
                        txt = ev.get("text", "") or ""

                        with st.expander(f"Source {i}: {cite}", expanded=False):
                            st.text_area(
                                "Chunk text",
                                value=txt,
                                height=240,
                                key=f"ev_full_{msg_idx}_{i}",
                            )
                else:
                    st.caption("No evidence returned.")

            with tab2:
                st.json(plan)

            with tab3:
                render_deliverable(deliverable)

            with tab4:
                if trace:
                    try:
                        st.dataframe(trace)
                    except Exception:
                        st.json(trace)
                else:
                    st.caption("No trace available.")

st.markdown("</div>", unsafe_allow_html=True)

# ==================== TYPING INDICATOR ====================
if st.session_state.inflight_question:
    started = st.session_state.assistant_typing_since or "--:--"
    st.markdown(
        html_block(
            f"""
            <div class="typing-box">
                <span>Preparing a verified answer • {safe_html(started)}</span>
                <span class="typing-dots"><span></span><span></span><span></span></span>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

# ==================== INPUT AREA ====================

# Handle queued questions from sidebar buttons
queued = st.session_state.pop("pending_question", None)
if queued and not st.session_state.inflight_question:
    q = str(queued).strip()
    if q:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        st.session_state.inflight_question = q
        st.session_state.assistant_typing_since = now_hhmm()
        st.rerun()

# Main chat input
if prompt := st.chat_input("Type your question here...", key="chat_input"):
    q = prompt.strip()
    if q and not st.session_state.inflight_question:
        st.session_state.conversation_history.append({"role": "user", "content": q, "timestamp": now_hhmm()})
        st.session_state.inflight_question = q
        st.session_state.assistant_typing_since = now_hhmm()
        st.rerun()

# Process inflight question (runs after rerun to show typing UI)
if st.session_state.inflight_question:
    with st.spinner("Processing HR knowledge base..."):
        result = run_question(st.session_state.inflight_question, k=k)

    st.session_state.conversation_history.append({"role": "assistant", "content": result, "timestamp": now_hhmm()})
    st.session_state.inflight_question = None
    st.session_state.assistant_typing_since = None
    st.rerun()
