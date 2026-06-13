from langgraph.graph import StateGraph, START, END
from src.rag.state import GraphState
from src.rag.router import build_router
from src.rag.nodes import retrieve, web_search, grade_documents, generate
from src.rag.graders import build_hallucination_grader, build_answer_grader

_router = build_router()
_halluc = build_hallucination_grader()
_ans    = build_answer_grader()
MAX_RETRIES = 2


def route_question(state: GraphState) -> str:
    """Adaptive RAG: route query to vectorstore or web search."""
    decision = _router.invoke({"question": state["question"]})
    return decision.datasource


def decide_after_grading(state: GraphState) -> str:
    """Corrective RAG: fall back to web search if no relevant docs survived."""
    return "generate" if state["documents"] else "web_search"


def grade_generation(state: GraphState) -> str:
    """Check grounding + answer quality; loop back if hallucinated."""
    if state.get("retries", 0) >= MAX_RETRIES:
        return "useful"
    grounded = _halluc.invoke(
        {"documents": "\n".join(state["documents"]), "generation": state["generation"]}
    )
    if grounded.binary_score.lower() == "no":
        return "not_grounded"
    answered = _ans.invoke(
        {"question": state["question"], "generation": state["generation"]}
    )
    return "useful" if answered.binary_score.lower() == "yes" else "not_useful"


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("retrieve",        retrieve)
    g.add_node("web_search",      web_search)
    g.add_node("grade_documents", grade_documents)
    g.add_node("generate",        generate)

    # Adaptive: route at entry
    g.add_conditional_edges(
        START, route_question,
        {"vectorstore": "retrieve", "web_search": "web_search"},
    )
    g.add_edge("retrieve", "grade_documents")

    # Corrective: fallback to web if docs filtered out
    g.add_conditional_edges(
        "grade_documents", decide_after_grading,
        {"generate": "generate", "web_search": "web_search"},
    )
    g.add_edge("web_search", "generate")

    # Hallucination / answer quality loop
    g.add_conditional_edges(
        "generate", grade_generation,
        {"not_grounded": "generate", "not_useful": "web_search", "useful": END},
    )
    return g.compile()


rag_app = build_graph()


def answer_question(question: str) -> dict:
    result = rag_app.invoke(
        {"question": question, "documents": [], "generation": "", "retries": 0}
    )
    return {"answer": result["generation"], "sources": result["documents"]}
