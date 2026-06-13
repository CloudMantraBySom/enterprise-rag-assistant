from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.observability.tracing import init_tracing, UsageTracker
from src.guardrails.validators import validate_input, validate_output
from src.rag.graph import answer_question

init_tracing()
app = FastAPI(title="Enterprise RAG Assistant", version="1.0.0")


class Query(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(q: Query):
    ok, msg = validate_input(q.question)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    tracker = UsageTracker()
    result  = answer_question(q.question)
    result["answer"] = validate_output(result["answer"])
    result["usage"]  = tracker.summary()
    return result


@app.post("/ingest")
def ingest():
    """Re-embed all PDFs from DOCS_PATH into the vector store."""
    from src.ingestion.loader import build_vector_store
    build_vector_store()
    return {"status": "ingested"}
