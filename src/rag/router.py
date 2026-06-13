from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.llm.factory import get_llm


class RouteQuery(BaseModel):
    """Adaptive RAG: pick the best data source for the question."""
    datasource: Literal["vectorstore", "web_search"] = Field(
        description="Route to internal vectorstore or live web search."
    )


def build_router():
    llm      = get_llm()
    structured = llm.with_structured_output(RouteQuery)
    prompt   = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert query router. The vectorstore holds internal "
"enterprise documents (policies, product docs, runbooks). "
"Use 'vectorstore' for those. Use 'web_search' for current events "
"or general world knowledge."),
        ("human", "{question}"),
    ])
    return prompt | structured
