from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from src.config import settings
from src.llm.factory import get_llm
from src.ingestion.loader import get_retriever
from src.rag.graders import build_doc_grader
from src.rag.state import GraphState

_retriever  = None
_doc_grader = build_doc_grader()


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever


def retrieve(state: GraphState) -> dict:
    docs = _get_retriever().invoke(state["question"])
    return {"documents": [d.page_content for d in docs]}


def web_search(state: GraphState) -> dict:
    tool    = TavilySearchResults(max_results=3, api_key=settings.tavily_api_key)
    results = tool.invoke({"query": state["question"]})
    docs    = [r["content"] for r in results] if isinstance(results, list) else [str(results)]
    return {"documents": docs}


def grade_documents(state: GraphState) -> dict:
    """Corrective RAG: discard irrelevant chunks."""
    filtered = []
    for d in state["documents"]:
        score = _doc_grader.invoke({"question": state["question"], "document": d})
        if score.binary_score.lower() == "yes":
            filtered.append(d)
    return {"documents": filtered}


def generate(state: GraphState) -> dict:
    context = "\n\n".join(state["documents"])
    prompt  = ChatPromptTemplate.from_template(
        "Answer the question using ONLY the context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    )
    chain  = prompt | get_llm() | StrOutputParser()
    answer = chain.invoke({"context": context, "question": state["question"]})
    return {"generation": answer, "retries": state.get("retries", 0) + 1}
