# 📚 Enterprise RAG Knowledge Assistant

> **Production-grade conversational RAG platform on Azure**
> Adaptive + Corrective RAG · RAGAS evaluation gate in CI/CD · LLMOps observability

---

## Architecture

```
User query
    │
    ▼
Guardrails (input validation / prompt-injection block)
    │
    ▼
Adaptive Router (LLM) ──► vectorstore ──► FAISS retrieval ──┐
    │                                                        │
    └──────────────────► web search (Tavily) ────────────────┤
                                                             ▼
                                               Corrective Grader
                                           (filter irrelevant chunks)
                                                    │ no relevant docs → web search
                                                    ▼
                                                Generate (Azure OpenAI GPT-4o)
                                                    │
                                               Hallucination Grader
                                               Answer Quality Grader
                                                    │ not grounded → retry generate
                                                    │ not useful   → retry web search
                                                    ▼
                                              Final Answer
                                                    │
                                          Guardrails (output)
                                                    │
                                               Response + Sources
```

**Azure Services:** Azure OpenAI (GPT-4o + text-embedding-3-large)

**AI/LLMOps Stack:** LangGraph · LangChain · LangSmith · RAGAS · FAISS · Tavily

**DevOps Stack:** Docker · FastAPI · Streamlit · Azure Pipelines

---

## Project Structure

```
enterprise-rag-assistant/
├── src/
│   ├── config.py                     # Pydantic settings (Azure OpenAI, paths, tuning)
│   ├── main.py                       # FastAPI app (/health, /ask, /ingest)
│   ├── llm/factory.py                # Azure OpenAI LLM + Embeddings factory
│   ├── ingestion/loader.py           # PDF → chunk → embed → FAISS
│   ├── rag/
│   │   ├── state.py                  # LangGraph GraphState TypedDict
│   │   ├── router.py                 # Adaptive RAG: structured-output query router
│   │   ├── graders.py                # Doc relevance, hallucination, answer graders
│   │   ├── nodes.py                  # retrieve, web_search, grade_documents, generate
│   │   └── graph.py                  # LangGraph graph: wiring + conditional edges
│   ├── guardrails/validators.py      # Input/output validation + injection blocking
│   └── observability/tracing.py     # LangSmith init + token cost tracker
├── app/streamlit_app.py              # Operator UI
├── evaluation/
│   ├── eval_dataset.json             # Golden Q&A pairs
│   └── run_ragas_eval.py             # RAGAS gate (CI fails if scores drop)
├── tests/test_graph.py               # Unit tests: router, guardrails
├── Dockerfile
├── docker-compose.yml
└── azure-pipelines.yml               # CI: test → RAGAS gate → Docker push
```

---

## Quick Start

### 1. Setup
```bash
git clone https://github.com/somraj0611/enterprise-rag-assistant.git
cd enterprise-rag-assistant

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your Azure OpenAI endpoint, API key, and Tavily key
```

### 2. Add Documents
```bash
# Drop PDF files into the data/ folder
cp your-docs/*.pdf data/
```

### 3. Run
```bash
# API
uvicorn src.main:app --reload --port 8000

# UI (new terminal)
streamlit run app/streamlit_app.py

# Or both via Docker Compose
docker-compose up --build
```

### 4. Test & Evaluate
```bash
pytest tests/ -v
python -m evaluation.run_ragas_eval
```

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ask` | POST | `{"question": "..."}` → answer + sources |
| `/ingest` | POST | Re-embed all PDFs in `data/` |

---

## RAG Flow Detail

| Stage | Pattern | What it does |
|-------|---------|-------------|
| **Router** | Adaptive RAG | LLM classifies query → vectorstore or web |
| **Retrieve** | Standard RAG | FAISS top-k semantic search |
| **Grade docs** | Corrective RAG | LLM filters irrelevant chunks; falls back to web if all filtered |
| **Generate** | — | GPT-4o answers from grounded context only |
| **Grade generation** | Corrective RAG | Hallucination + answer quality checks; retries up to 2x |

---

## LLMOps Quality Gate (RAGAS in CI)

Every push to `main` runs `run_ragas_eval.py` in Azure Pipelines.
Build **fails** if any metric drops below threshold:

| Metric | Threshold |
|--------|-----------|
| Faithfulness | ≥ 0.80 |
| Answer Relevancy | ≥ 0.80 |
| Context Precision | ≥ 0.70 |

---

*Built by Som Raj — AI Platform Engineer | LLMOps | Azure DevOps | LangGraph*
