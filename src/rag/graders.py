from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.llm.factory import get_llm


class GradeDocuments(BaseModel):
    binary_score: str = Field(description="'yes' if relevant else 'no'")


class GradeHallucination(BaseModel):
    binary_score: str = Field(description="'yes' if grounded in docs else 'no'")


class GradeAnswer(BaseModel):
    binary_score: str = Field(description="'yes' if it answers the question else 'no'")


def build_doc_grader():
    llm    = get_llm().with_structured_output(GradeDocuments)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Grade whether the document is relevant to the question. Answer 'yes' or 'no'."),
        ("human",  "Document:\n{document}\n\nQuestion: {question}"),
    ])
    return prompt | llm


def build_hallucination_grader():
    llm    = get_llm().with_structured_output(GradeHallucination)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Is the answer grounded in the provided facts? 'yes'/'no'."),
        ("human",  "Facts:\n{documents}\n\nAnswer: {generation}"),
    ])
    return prompt | llm


def build_answer_grader():
    llm    = get_llm().with_structured_output(GradeAnswer)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Does the answer address the question? 'yes'/'no'."),
        ("human",  "Question: {question}\n\nAnswer: {generation}"),
    ])
    return prompt | llm
