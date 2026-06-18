# Enterprise RAG Knowledge Assistant — Architecture & Flow (diagram.md)

This single file contains ALL diagrams and an end-to-end explanation.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph Clients
        UI[Streamlit UI<br/>app/streamlit_app.py]
        API_CLIENT[HTTP Client / curl]
    end

    subgraph API_Layer["API Layer (FastAPI)"]
        MAIN[src/main.py<br/>/ask, /health]
        GUARD_IN[Guardrails<br/>validate_input]
        GUARD_OUT[Guardrails<br/>validate_output]
    end

    subgraph RAG_Core["Adaptive + Corrective RAG (LangGraph)"]
        GRAPH[src/rag/graph.py<br/>Compiled StateGraph]
    end

    subgraph LLM_Layer["LLM / Embeddings"]
        FACTORY[src/llm/factory.py<br/>Azure OpenAI → OpenAI fallback]
    end

    subgraph Data_Layer["Knowledge & Tools"]
        VS[(FAISS Vector Store)]
        WEB[Tavily Web Search]
        DOCS[PDFs in ./data]
    end

    subgraph Ops["LLMOps & Observability"]
        TRACE[LangSmith Tracing]
        USAGE[UsageTracker<br/>tokens + cost]
        RAGAS[RAGAS Eval Gate<br/>run_ragas_eval.py]
    end

    UI --> MAIN
    API_CLIENT --> MAIN
    MAIN --> GUARD_IN --> GRAPH --> GUARD_OUT --> MAIN
    GRAPH --> FACTORY
    GRAPH --> VS
    GRAPH --> WEB
    DOCS -.ingestion.-> VS
    FACTORY --> TRACE
    MAIN --> USAGE
    GRAPH -.tested by.-> RAGAS
```

---

## 2. Ingestion Pipeline (offline / one-time)

```mermaid
flowchart LR
    A[PDFs in ./data] --> B[PyPDFDirectoryLoader<br/>load docs]
    B --> C[RecursiveCharacterTextSplitter<br/>chunk_size=1000, overlap=200]
    C --> D[Embeddings<br/>text-embedding-3-large]
    D --> E[(FAISS Index<br/>saved to ./vector_store)]
```

Built once via `build_vector_store()`, reloaded later via `load_vector_store()`.

---

## 3. The Core RAG Graph (LangGraph State Machine)

Combines **Adaptive RAG** (smart routing) and **Corrective RAG**
(self-correcting via grading + fallback).

```mermaid
stateDiagram-v2
    [*] --> route_question : START

    route_question --> retrieve : datasource = "vectorstore"
    route_question --> web_search : datasource = "web_search"

    retrieve --> grade_documents

    grade_documents --> generate : relevant docs survive
    grade_documents --> web_search : NO relevant docs (Corrective fallback)

    web_search --> generate

    generate --> grade_generation

    grade_generation --> generate : not_grounded (hallucination → retry)
    grade_generation --> web_search : not_useful (doesn't answer Q)
    grade_generation --> [*] : useful (END)

    note right of grade_generation
        Loop capped at MAX_RETRIES = 2
        to prevent infinite loops
    end note
```

### Graph State (shared memory)
```python
GraphState = {
    "question":   str,        # user's input
    "generation": str,        # current LLM answer
    "documents":  List[str],  # retrieved / filtered context
    "datasource": str,        # "vectorstore" | "web_search"
    "retries":    int,        # hallucination retry counter
}
```

---

## 4. Component Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| Config | `src/config.py` | Centralized env-based settings (Pydantic) |
| LLM Factory | `src/llm/factory.py` | Azure OpenAI w/ OpenAI fallback |
| Ingestion | `src/ingestion/loader.py` | PDF → chunks → FAISS index |
| Router | `src/rag/router.py` | **Adaptive**: vectorstore vs web |
| Graders | `src/rag/graders.py` | Doc relevance, hallucination, answer quality |
| Nodes | `src/rag/nodes.py` | retrieve, web_search, grade_documents, generate |
| Graph | `src/rag/graph.py` | Wires nodes + conditional edges |
| Guardrails | `src/guardrails/validators.py` | Prompt-injection, toxicity, length |
| Observability | `src/observability/tracing.py` | LangSmith + token/cost tracking |
| API | `src/main.py` | FastAPI endpoints |
| UI | `app/streamlit_app.py` | Chat interface |
| Eval | `evaluation/run_ragas_eval.py` | CI quality gate (RAGAS) |

---

## 5. CI/CD + LLMOps Quality Gate

```mermaid
flowchart TD
    PUSH[git push to main] --> PIPE[azure-pipelines.yml]
    PIPE --> T1[Install deps]
    T1 --> T2[pytest -q<br/>unit tests]
    T2 --> T3{RAGAS Eval Gate}
    T3 -->|scores >= thresholds| T4[Docker build & push]
    T3 -->|any score below threshold| FAIL[❌ Build FAILS<br/>sys.exit 1]
    T4 --> DEPLOY[Deployable Image]

    subgraph Thresholds
        TH1[faithfulness >= 0.80]
        TH2[answer_relevancy >= 0.80]
        TH3[context_precision >= 0.70]
    end
    T3 -.checks.-> Thresholds
```

Every prompt or model change must pass the RAGAS gate before shipping.

---

## 6. End-to-End Request Sequence

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI /ask
    participant G as Guardrails
    participant Graph as LangGraph
    participant Router
    participant VS as FAISS
    participant Web as Tavily
    participant LLM
    participant LS as LangSmith

    User->>API: POST /ask {question}
    API->>G: validate_input()
    alt blocked (injection/toxic/too long)
        G-->>API: (False, reason)
        API-->>User: {error}
    else allowed
        API->>Graph: answer_question(question)
        Graph->>Router: route_question()
        Router->>LLM: structured route decision
        LLM-->>Router: "vectorstore" or "web_search"

        alt vectorstore route
            Graph->>VS: retrieve top-k chunks
            VS-->>Graph: documents
            Graph->>LLM: grade_documents (relevance)
            alt no relevant docs
                Graph->>Web: web_search (Corrective fallback)
                Web-->>Graph: web documents
            end
        else web route
            Graph->>Web: web_search
            Web-->>Graph: web documents
        end

        Graph->>LLM: generate answer from context
        LLM-->>Graph: generation
        Graph->>LLM: grade_generation (grounded? useful?)
        alt not grounded → retry / not useful → web
            Graph->>LLM: regenerate or re-search (max 2)
        end

        Graph-->>API: {answer, sources}
        API->>G: validate_output() redact
        API-->>User: {answer, sources, usage}
        Note over LLM,LS: All calls traced in LangSmith
    end
```

---

# How It Works — Walkthrough with an Example

### Example Query
> **User asks:** *"What is the company's remote work policy?"*

**Step 1 — API Entry & Input Guardrails**
`POST /ask` → `validate_input()` checks for prompt-injection patterns, toxic
words, and length < 4000. Passes ✅ → enters the RAG graph.

**Step 2 — Adaptive Routing**
`route_question()` asks the router LLM. "Remote work policy" = internal doc →
returns `datasource = "vectorstore"` → routes to `retrieve`.

**Step 3 — Retrieval**
`retrieve()` queries FAISS (`k=4`) and pulls the 4 most similar chunks into
`state["documents"]`.

**Step 4 — Corrective Document Grading**
`grade_documents()` keeps only relevant chunks (HR policy = yes, payments SLA = no).
`decide_after_grading()`: if relevant docs survive → `generate`; if zero
survive → **Corrective fallback to web_search**.

**Step 5 — Generation**
`generate()` answers using ONLY the context:
> *"Employees may work remotely up to 3 days per week with manager approval."*
`retries` → 1.

**Step 6 — Self-Correction**
`grade_generation()` runs two graders:
- Hallucination grader → grounded? `yes` ✅
- Answer grader → answers question? `yes` ✅
Result = `"useful"` → `END`.

> 🔁 `"not_grounded"` → loop back to `generate`
> 🔁 `"not_useful"` → fall back to `web_search`
> ⛔ Capped at `MAX_RETRIES = 2`.

**Step 7 — Output Guardrails & Response**
`validate_output()` redacts disallowed words; `UsageTracker` attaches cost.
```json
{
  "answer": "Employees may work remotely up to 3 days per week with manager approval.",
  "sources": ["...relevant policy chunk text..."],
  "usage": { "total_tokens": 0, "estimated_cost_usd": 0.0 }
}
```

---

### Contrast Example — Web Fallback
> *"What's the latest news on OpenAI API pricing changes?"*

1. Router → current world knowledge → `web_search`
2. Skips FAISS, calls Tavily for live results
3. `generate()` answers from web context
4. Grading confirms grounded + useful → `END`

If a vectorstore query returned only irrelevant chunks, **Corrective RAG**
automatically reroutes to web search — the self-healing safety net.

---

### Why this design is "Production-Grade"
| Feature | Mechanism |
|---------|-----------|
| **Adaptive** | LLM router picks best source per query |
| **Corrective** | Doc grading + web fallback + hallucination loop |
| **Safe** | Input/output guardrails |
| **Observable** | LangSmith tracing + token/cost tracking |
| **Quality-gated** | RAGAS thresholds fail the CI build on regressions |
| **Portable** | Docker + Azure Pipelines, Azure→OpenAI fallback |