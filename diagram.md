# Enterprise RAG Knowledge Assistant — Architecture Diagram

## High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENTERPRISE RAG KNOWLEDGE ASSISTANT                    │
│                    Adaptive + Corrective RAG on Azure OpenAI                 │
└─────────────────────────────────────────────────────────────────────────────┘

  USER INPUT
  ─────────
  [Streamlit UI]  ──or──  [FastAPI POST /ask]
        │                          │
        ▼                          ▼
  ┌─────────────────────────────────────┐
  │         GUARDRAILS (validators.py)   │
  │  • Prompt-injection detection        │
  │  • Toxic content filter              │
  │  • Input length cap (4000 chars)     │
  └──────────────┬──────────────────────┘
                 │  (blocked → return error)
                 ▼  (allowed → proceed)
  ┌─────────────────────────────────────┐
  │     LANGGRAPH RAG GRAPH (graph.py)   │
  └──────────────┬──────────────────────┘
                 │
                 ▼
        ╔═════════════════╗
        ║  ADAPTIVE ROUTER ║  ← LLM decides: vectorstore OR web_search
        ╚════════╤════════╝
         ┌───────┴───────┐
         ▼               ▼
  ┌────────────┐  ┌──────────────┐
  │  RETRIEVE   │  │  WEB SEARCH  │
  │  (FAISS)    │  │  (Tavily)    │
  └──────┬──────┘  └──────┬───────┘
         │                │
         ▼                │
  ┌──────────────────┐    │
  │  GRADE DOCUMENTS  │    │
  │  (Corrective RAG) │    │
  │  LLM grades each  │    │
  │  chunk: relevant? │    │
  └────────┬─────────┘    │
           │               │
    ┌──────┴──────┐        │
    │ docs left?  │        │
    ├── YES ──────────────►│
    └── NO ── web_search ◄─┘
                 │
                 ▼
        ┌────────────────┐
        │    GENERATE     │
        │  (Azure OpenAI) │
        │  GPT-4o answer  │
        └────────┬────────┘
                 │
                 ▼
        ╔═══════════════════╗
        ║  GRADE GENERATION  ║
        ╠═══════════════════╣
        ║ 1. Hallucination?  ║
        ║    grounded in docs║
        ║ 2. Useful?         ║
        ║    answers question ║
        ╚════════╤══════════╝
                 │
    ┌────────────┼──────────────┐
    ▼            ▼              ▼
not_grounded  not_useful     useful
(re-generate) (web_search)     │
    │              │            ▼
    └──────────────┘       ┌─────────┐
          (loop)            │  END    │
                            │ Return  │
                            │ Answer  │
                            └────┬────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  OUTPUT GUARDRAIL          │
                    │  • Toxic word redaction    │
                    └────────────┬──────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  USAGE TRACKER             │
                    │  • Token count             │
                    │  • Cost estimate (USD)     │
                    └────────────┬──────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  LANGSMITH TRACING         │
                    │  (every LLM call logged)   │
                    └──────────────────────────┘
```

---

## Component Map

```
enterprise-rag-assistant/
│
├── src/
│   ├── config.py             ← All settings via .env (Azure keys, paths, tuning)
│   │
│   ├── llm/
│   │   └── factory.py        ← LLM factory: Azure OpenAI primary, OpenAI fallback
│   │
│   ├── ingestion/
│   │   └── loader.py         ← PDF → chunks → FAISS vector store
│   │
│   ├── rag/
│   │   ├── state.py          ← GraphState (shared data between all nodes)
│   │   ├── router.py         ← Adaptive Router: vectorstore vs. web_search
│   │   ├── graders.py        ← 3 LLM graders: doc relevance, hallucination, answer
│   │   ├── nodes.py          ← retrieve, web_search, grade_documents, generate
│   │   └── graph.py          ← LangGraph wiring + conditional edges
│   │
│   ├── guardrails/
│   │   └── validators.py     ← Input/output safety (injection, toxicity, length)
│   │
│   ├── observability/
│   │   └── tracing.py        ← LangSmith init + per-request token/cost tracker
│   │
│   └── main.py               ← FastAPI app: /health + /ask endpoints
│
├── app/
│   └── streamlit_app.py      ← Chat UI (browser-based, calls answer_question())
│
├── evaluation/
│   ├── eval_dataset.json     ← Q&A golden set (3 enterprise questions)
│   └── run_ragas_eval.py     ← RAGAS evaluator: fails if scores drop below threshold
│
├── tests/
│   └── test_graph.py         ← Unit tests: schema validation + guardrail checks
│
├── Dockerfile                ← Python 3.11-slim, port 8000
├── docker-compose.yml        ← Single service: rag-api
└── azure-pipelines.yml       ← CI/CD: test → RAGAS gate → Docker push
```

---

## LangGraph Node & Edge Flow (Detailed)

```
START
  │
  │  [conditional edge: route_question()]
  │  LLM reads the question → picks datasource
  │
  ├──── "vectorstore" ──────► RETRIEVE
  │                               │
  │                               │  [FAISS similarity search, top-k chunks]
  │                               ▼
  │                         GRADE_DOCUMENTS
  │                               │
  │                     [LLM grades each doc]
  │                               │
  │              [conditional edge: decide_after_grading()]
  │                    ┌──────────┴──────────┐
  │               docs exist?             no docs
  │                    │                    │
  │                    ▼                    ▼
  └──── "web_search" ──────────► WEB_SEARCH
                                      │
                                      │  [Tavily API, 3 results]
                                      ▼
                                  GENERATE
                                      │
                          [conditional edge: grade_generation()]
                                      │
                          ┌───────────┼───────────┐
                     not_grounded  not_useful    useful
                          │            │            │
                          ▼            ▼            ▼
                       GENERATE    WEB_SEARCH      END
                     (retry loop) (fallback)   (return answer)
```

**Retry guard:** `retries` counter in `GraphState`. After `MAX_RETRIES=2`, `grade_generation()` forces `"useful"` to prevent infinite loops.

---

## Data Flow Through GraphState

```
GraphState (TypedDict):
┌────────────────┬────────────────────────────────────────────────────────┐
│ Field          │ Lifecycle                                               │
├────────────────┼────────────────────────────────────────────────────────┤
│ question       │ Set at START, read-only through the graph               │
│ datasource     │ Set by router ("vectorstore" or "web_search")           │
│ documents      │ Populated by retrieve/web_search, filtered by grader    │
│ generation     │ Set by generate node, re-set on each retry              │
│ retries        │ Incremented by generate node, caps at MAX_RETRIES=2     │
└────────────────┴────────────────────────────────────────────────────────┘
```

---

## LLMOps / CI-CD Pipeline

```
  git push → main
       │
       ▼
  Azure Pipelines
       │
       ├── 1. Install dependencies (requirements.txt)
       │
       ├── 2. Unit Tests (pytest)
       │      test_route_query_schema()
       │      test_guardrail_blocks_injection()
       │      test_guardrail_allows_normal()
       │
       ├── 3. RAGAS Evaluation Gate  ← LLMOps quality gate
       │      Runs 3 golden Q&A pairs through the full RAG graph
       │      Checks:
       │        faithfulness      ≥ 0.80
       │        answer_relevancy  ≥ 0.80
       │        context_precision ≥ 0.70
       │      ❌ FAIL → pipeline stops, build blocked
       │      ✅ PASS → continue
       │
       └── 4. Docker Build & Push
              image tagged with $(Build.BuildId)
              pushed to container registry
```

---

## Key Design Patterns

| Pattern | Where Used | Purpose |
|---|---|---|
| **Adaptive RAG** | `router.py` + `graph.py` | Route each query to best source (internal docs vs. live web) |
| **Corrective RAG** | `graders.py` (doc grader) + `graph.py` | Drop irrelevant chunks; fall back to web if nothing passes |
| **Self-RAG / Hallucination Check** | `graders.py` (hallucination grader) + `graph.py` | Retry generation if answer is not grounded in retrieved docs |
| **Answer Quality Check** | `graders.py` (answer grader) + `graph.py` | Re-route to web search if answer doesn't address the question |
| **Guardrails** | `validators.py` | Block prompt injection & toxic content at input; redact at output |
| **LLMOps Evaluation Gate** | `run_ragas_eval.py` + `azure-pipelines.yml` | RAGAS scores gate every CI run — prevents regression |
| **Factory Pattern (LLM)** | `factory.py` | Azure OpenAI in prod, plain OpenAI for local dev — no code change |
| **Lazy Singleton (Retriever)** | `nodes.py` | FAISS index loaded once per process, reused across requests |
