import sys
from pathlib import Path

# Ensure repo root is on PYTHONPATH so "agents" can be imported when Streamlit runs from /app
ROOT = Path(__file__).resolve().parents[1]  # repo root folder
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from agents.workflow import answer_question

st.set_page_config(page_title="Kosovo HR Ops Copilot", layout="wide")
st.title("Kosovo HR Ops Multi-Agent Copilot")
st.caption("Answers are grounded only in the provided Kosovo laws + company policy documents, with citations.")

q = st.text_area(
    "Ask an HR question",
    height=110,
    placeholder="e.g., What is the remote work policy?",
)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    k = st.slider("Retrieved chunks (k)", min_value=3, max_value=10, value=6)
with col2:
    show_plan = st.checkbox("Show plan", value=False)
with col3:
    show_evidence = st.checkbox("Show evidence", value=False)

if st.button("Answer") and q.strip():
    with st.spinner("Working..."):
        out = answer_question(q.strip(), k=k)

    st.subheader("Answer")
    st.write(out["answer"])

    st.subheader("Verifier")
    st.json(out["verdict"])

    if show_plan:
        st.subheader("Plan")
        st.json(out["plan"])

    if show_evidence:
        st.subheader("Retrieved evidence")
        for e in out["evidence"]:
            st.markdown(f"**{e['citation']}**")
            st.write(e["text"])
            st.divider()
