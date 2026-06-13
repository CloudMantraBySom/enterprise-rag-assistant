import streamlit as st
from src.rag.graph import answer_question
from src.guardrails.validators import validate_input
from src.observability.tracing import init_tracing

init_tracing()

st.set_page_config(page_title="Enterprise RAG Assistant", page_icon="📚", layout="wide")
st.title("📚 Enterprise RAG Knowledge Assistant")
st.caption("Adaptive + Corrective RAG · Azure OpenAI · LangGraph · LangSmith")

with st.sidebar:
    st.header("How it works")
    st.markdown("""
1. **Adaptive router** decides: vectorstore or web search
2. **Corrective grader** filters irrelevant chunks
3. **Generator** answers using only grounded context
4. **Hallucination grader** loops until answer is grounded
5. All calls traced in **LangSmith**
""")

q = st.text_input("Ask a question about your documents:",
                   placeholder="e.g. What is the remote work policy?")

if q:
    ok, msg = validate_input(q)
    if not ok:
        st.error(f"Blocked: {msg}")
    else:
        with st.spinner("Routing → retrieving → grading → generating…"):
            res = answer_question(q)
        st.markdown("### Answer")
        st.write(res["answer"])
        with st.expander(f"Retrieved sources ({len(res['sources'])} chunks)"):
            for i, s in enumerate(res["sources"], 1):
                st.markdown(f"**Source {i}**")
                st.write(s[:800])
                st.divider()
