from typing import List, TypedDict


class GraphState(TypedDict):
    """Shared state flowing through the Adaptive / Corrective RAG graph."""
    question:   str
    generation: str
    documents:  List[str]
    datasource: str   # "vectorstore" | "web_search"
    retries:    int   # hallucination-retry counter
