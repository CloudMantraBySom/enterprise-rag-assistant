# AKS Autonomous Operations Agent — Architecture Diagrams

> All diagrams use **Mermaid** syntax and render natively in GitHub, GitLab,
> Azure DevOps Repos, and VS Code (with the Mermaid extension).

---

## Table of Contents
1. [System Context Diagram](#1-system-context-diagram)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Multi-Agent Component Diagram](#3-multi-agent-component-diagram)
4. [LangGraph Workflow (State Machine)](#4-langgraph-workflow-state-machine)
5. [End-to-End Sequence Diagram](#5-end-to-end-sequence-diagram)
6. [RAG / Knowledge Flow](#6-rag--knowledge-flow)
7. [AKS Deployment Topology](#7-aks-deployment-topology)
8. [Security & Identity Flow](#8-security--identity-flow)
9. [CI/CD Pipeline Flow](#9-cicd-pipeline-flow)
10. [Terraform Infrastructure Map](#10-terraform-infrastructure-map)
11. [Observability Data Flow](#11-observability-data-flow)
12. [Incident State Lifecycle](#12-incident-state-lifecycle)
13. [Folder Structure Tree](#13-folder-structure-tree)

---

## 1. System Context Diagram

```mermaid
graph TB
    Dev[👨‍💻 Developer / SRE]
    UI[🖥️ Streamlit Operator Console]
    Agent[🤖 AKS Autonomous Ops Agent]
    AKS[(☸️ AKS Cluster Workloads)]
    AOAI[🧠 Azure OpenAI GPT-4o]
    Search[🔎 Azure AI Search RAG]
    Obs[📊 Azure Monitor / App Insights]

    Dev -->|Azure AD OAuth| UI
    UI <-->|REST /api/v1| Agent
    Agent -->|watch + remediate| AKS
    Agent -->|reason / diagnose| AOAI
    Agent <-->|retrieve / store| Search
    Agent -->|traces / metrics| Obs
    AKS -->|events / logs| Agent

    classDef ai fill:#6f42c1,color:#fff
    classDef k8s fill:#326ce5,color:#fff
    classDef user fill:#2ea44f,color:#fff
    class AOAI,Search ai
    class AKS,Agent k8s
    class Dev,UI user
```

---

## 2. High-Level Architecture

```mermaid
graph TB
    subgraph CLUSTER["☸️ AKS Cluster"]
        subgraph APPNS["App Namespaces"]
            W[App Workloads / Pods]
        end
        subgraph OPSNS["agent-ops Namespace"]
            WATCH[Event Watcher<br/>Detection Daemon]
            ORCH[FastAPI Orchestrator<br/>+ LangGraph Engine]
            SUI[Streamlit UI]
        end
    end

    subgraph AZURE["☁️ Azure Platform Services"]
        AOAI[Azure OpenAI<br/>GPT-4o + Embeddings]
        SEARCH[Azure AI Search<br/>Vector Store]
        KV[Key Vault<br/>Secrets]
        BLOB[Blob Storage<br/>Audit + Evidence]
        LAW[Log Analytics]
        APPI[Application Insights]
    end

    W -->|events / status| WATCH
    WATCH -->|POST incident| ORCH
    SUI <-->|approve / monitor| ORCH
    ORCH -->|kubectl actions| W
    ORCH -->|prompt| AOAI
    ORCH <-->|RAG query / upsert| SEARCH
    ORCH -->|get secrets| KV
    ORCH -->|store audit| BLOB
    ORCH -->|traces| APPI
    APPI --> LAW

    classDef az fill:#0078d4,color:#fff
    classDef ops fill:#326ce5,color:#fff
    class AOAI,SEARCH,KV,BLOB,LAW,APPI az
    class WATCH,ORCH,SUI ops
```

---

## 3. Multi-Agent Component Diagram

```mermaid
graph LR
    subgraph ORCH["🤖 LangGraph Orchestrator"]
        A1[Agent 1<br/>Incident Detection]
        A2[Agent 2<br/>Diagnostics]
        A3[Agent 3<br/>Root Cause Analysis]
        A5[Agent 5<br/>Approval]
        A4[Agent 4<br/>Remediation]
        A6[Agent 6<br/>Knowledge]
    end

    A1 -->|classified incident| A2
    A2 -->|evidence bundle| A3
    A3 -->|confidence < 0.90| A5
    A3 -->|confidence ≥ 0.90| A4
    A5 -->|approved| A4
    A4 -->|action result| A6

    A2 -.kubectl logs/describe.-> K8S[(AKS API)]
    A3 -.RAG context.-> SEARCH[(AI Search)]
    A3 -.reasoning.-> LLM[(GPT-4o)]
    A4 -.patch/scale.-> K8S
    A6 -.embed + store.-> SEARCH

    classDef agent fill:#6f42c1,color:#fff
    class A1,A2,A3,A4,A5,A6 agent
```

---

## 4. LangGraph Workflow (State Machine)

```mermaid
stateDiagram-v2
    [*] --> Detection
    Detection --> Diagnostics: classified
    Diagnostics --> RootCause: evidence collected
    RootCause --> ConfidenceGate: RCA + confidence

    ConfidenceGate --> AutoRemediation: conf ≥ 0.90 AND low-risk
    ConfidenceGate --> HumanApproval: conf < 0.90 OR high-risk

    HumanApproval --> AutoRemediation: ✅ approved (resume)
    HumanApproval --> Rejected: ❌ rejected

    AutoRemediation --> Validation: action applied
    Validation --> Knowledge: fix verified
    Validation --> Escalate: fix failed

    Knowledge --> [*]: resolved + learned
    Rejected --> [*]
    Escalate --> [*]

    note right of HumanApproval
        LangGraph interrupt_before
        pauses here & checkpoints
        state until UI approval
    end note
```

---

## 5. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant K8s as ☸️ AKS Events
    participant W as Event Watcher
    participant O as Orchestrator (FastAPI)
    participant G as LangGraph
    participant L as GPT-4o
    participant S as AI Search
    participant UI as Streamlit
    participant H as SRE Human

    K8s->>W: ImagePullBackOff event
    W->>O: POST /api/v1/incidents
    O->>G: invoke(state, thread_id)

    G->>K8s: get_pod_logs / describe / events
    K8s-->>G: evidence bundle

    G->>S: retrieve_context(query)
    S-->>G: top-k past incidents + docs
    G->>L: diagnose(evidence + RAG)
    L-->>G: root_cause + confidence=0.94

    alt confidence ≥ 0.90
        G->>K8s: fix_image_reference(v1.3)
        K8s-->>G: rolling update started
    else confidence < 0.90
        G->>UI: pending approval
        UI->>H: notify
        H->>UI: Approve
        UI->>O: POST /approvals/{id}
        O->>G: resume(approved=true)
        G->>K8s: apply remediation
    end

    G->>K8s: validate_cluster_health()
    K8s-->>G: pods Running ✅
    G->>S: embed + upsert incident
    G-->>O: resolved (MTTR=87s)
    O-->>UI: status: resolved
```

---

## 6. RAG / Knowledge Flow

```mermaid
graph TB
    subgraph INGEST["📥 Ingestion (Offline / Batch)"]
        D1[K8s Documentation]
        D2[Internal Runbooks]
        D3[Past Incident History]
        D4[Azure Docs]
        CHUNK[Chunk + Clean]
        EMB1[Azure OpenAI<br/>Embeddings]
    end

    subgraph STORE["🗄️ Azure AI Search"]
        IDX[(Vector Index<br/>contentVector + metadata)]
    end

    subgraph QUERY["🔍 Retrieval (Runtime — RCA Agent)"]
        Q[Incident Query]
        EMB2[Embed Query]
        RANK[Hybrid Search<br/>vector + keyword]
        CTX[Top-K Context]
    end

    D1 & D2 & D3 & D4 --> CHUNK --> EMB1 --> IDX
    Q --> EMB2 --> RANK
    IDX --> RANK --> CTX
    CTX --> LLM[GPT-4o RCA]

    NEW[New Resolved Incident] -->|embed + upsert| IDX

    classDef store fill:#0078d4,color:#fff
    class IDX store
```

---

## 7. AKS Deployment Topology

```mermaid
graph TB
    subgraph CLUSTER["☸️ AKS Cluster (1.29)"]
        subgraph SYS["System Node Pool (autoscaled)"]
            subgraph NS["Namespace: agent-ops"]
                SA[ServiceAccount: agent-sa<br/>+ Workload Identity label]

                subgraph ORCHD["Deployment: orchestrator (2 replicas)"]
                    P1[Pod: orchestrator]
                    P2[Pod: orchestrator]
                end
                WD[Deployment: watcher (1)]
                UD[Deployment: ui (2)]

                SVC1[Service: orchestrator:8000]
                SVC2[Service: ui:8501]
                ING[Ingress<br/>TLS + Azure AD]
                HPA[HPA: CPU/Mem autoscale]
                NP[NetworkPolicy<br/>least-privilege egress]
            end
        end
    end

    ING --> SVC2 --> UD
    SVC2 -. internal .-> SVC1
    SVC1 --> ORCHD
    WD -->|POST| SVC1
    HPA -.scales.-> ORCHD
    SA -.identity.-> P1 & P2 & WD & UD

    classDef pod fill:#326ce5,color:#fff
    class P1,P2,WD,UD pod
```

---

## 8. Security & Identity Flow

```mermaid
sequenceDiagram
    autonumber
    participant Pod as Agent Pod
    participant SA as K8s ServiceAccount
    participant OIDC as AKS OIDC Issuer
    participant Entra as Entra ID (Azure AD)
    participant MI as Managed Identity
    participant KV as Key Vault
    participant AOAI as Azure OpenAI

    Pod->>SA: mount projected SA token
    Pod->>Entra: exchange SA token (federated cred)
    Entra->>OIDC: validate issuer + subject
    OIDC-->>Entra: trust confirmed
    Entra-->>MI: issue AAD access token
    MI-->>Pod: scoped token (no secrets stored!)

    Pod->>KV: get_secret (RBAC: Secrets User)
    KV-->>Pod: secret value
    Pod->>AOAI: bearer token (Cognitive Services User)
    AOAI-->>Pod: completion

    Note over Pod,AOAI: Zero passwords on disk.<br/>Least-privilege RBAC at every hop.
```

```mermaid
graph LR
    subgraph RBAC["K8s RBAC — Least Privilege"]
        R1[pods, logs, events: GET/LIST/WATCH]
        R2[configmaps: CREATE/UPDATE/PATCH]
        R3[deployments, scale: GET/PATCH/UPDATE]
        R4[metrics: GET/LIST]
    end
    subgraph AZRBAC["Azure RBAC Roles"]
        A1[Key Vault Secrets User]
        A2[Cognitive Services OpenAI User]
        A3[Search Index Data Contributor]
        A4[Storage Blob Data Contributor]
    end
    SA[agent-sa / Managed Identity] --> RBAC
    SA --> AZRBAC
```

---

## 9. CI/CD Pipeline Flow

```mermaid
graph LR
    DEV[git push] --> BUILD

    subgraph PIPE["Azure DevOps Pipelines"]
        BUILD[1. Build<br/>lint + compile]
        TEST[2. Test<br/>pytest + coverage]
        SEC[3. Security Scan<br/>Trivy + Bandit + tfsec]
        DOCK[4. Docker Build<br/>push to ACR]
        DEPLOY[5. Deploy<br/>kubectl/Helm to AKS]
    end

    BUILD --> TEST --> SEC --> DOCK --> DEPLOY
    DOCK -->|images| ACR[(Azure Container Registry)]
    DEPLOY -->|manifests| AKS[(AKS Cluster)]
    ACR --> AKS

    DEPLOY --> GATE{Prod?}
    GATE -->|yes| APPROVE[Manual Approval Gate]
    APPROVE --> AKS

    classDef stage fill:#0078d4,color:#fff
    class BUILD,TEST,SEC,DOCK,DEPLOY stage
```

---

## 10. Terraform Infrastructure Map

```mermaid
graph TB
    subgraph TF["📦 Terraform Root Module"]
        RG[module: resource_group]
        LAW[module: log_analytics]
        APPI[module: app_insights]
        AKS[module: aks<br/>OIDC + Workload Identity]
        AOAI[module: openai<br/>gpt-4o + embeddings]
        SRCH[module: ai_search]
        KV[module: key_vault<br/>RBAC enabled]
        ST[module: storage]
        MI[user_assigned_identity]
        FIC[federated_identity_credential]
    end

    RG --> LAW --> APPI
    RG --> AKS
    RG --> AOAI & SRCH & KV & ST
    AKS -->|oidc_issuer_url| FIC
    MI --> FIC
    APPI -.monitors.-> AKS

    STATE[(Remote State<br/>Azure Storage Backend)]
    TF -.stores.-> STATE

    classDef mod fill:#7b42bc,color:#fff
    class RG,LAW,APPI,AKS,AOAI,SRCH,KV,ST,MI,FIC mod
```

---

## 11. Observability Data Flow

```mermaid
graph LR
    subgraph SOURCES["Telemetry Sources"]
        T1[LangGraph Traces<br/>per-node spans]
        T2[Token + Cost Tracking]
        T3[K8s Action Audit]
        T4[Container stdout/logs]
        T5[Cluster Metrics]
    end

    subgraph PIPE["Collection"]
        OTEL[OpenTelemetry SDK]
        OMS[OMS Agent / Container Insights]
    end

    subgraph STORE["Azure"]
        APPI[Application Insights]
        LAW[Log Analytics Workspace]
    end

    subgraph VIZ["Dashboards"]
        DASH[Azure Workbooks / Grafana]
    end

    T1 & T2 & T3 --> OTEL --> APPI
    T4 & T5 --> OMS --> LAW
    APPI --> LAW
    LAW --> DASH

    DASH --> M1[Incident Count]
    DASH --> M2[MTTR]
    DASH --> M3[Auto-Remediation Success %]
    DASH --> M4[Human Escalations]
    DASH --> M5[Cost per Incident]
```

---

## 12. Incident State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> detected: watcher fires
    detected --> classified: detection node
    classified --> diagnosed: evidence gathered
    diagnosed --> rca_complete: root cause found
    rca_complete --> awaiting_approval: low confidence
    rca_complete --> remediated: high confidence (auto)
    awaiting_approval --> remediated: approved
    awaiting_approval --> rejected: rejected
    remediated --> resolved: validation passed ✅
    remediated --> remediation_failed: validation failed ❌
    remediation_failed --> escalated: notify human
    resolved --> [*]: knowledge stored
    rejected --> [*]
    escalated --> [*]
```

---

## 13. Folder Structure Tree

```mermaid
graph TD
    ROOT[aks-autonomous-ops-agent/]
    ROOT --> DOCS[docs/<br/>architecture, runbooks, guides]
    ROOT --> INFRA[infra/terraform/<br/>modules + root]
    ROOT --> SRC[src/]
    ROOT --> UI[ui/<br/>streamlit_app.py]
    ROOT --> DEPLOY[deploy/k8s/<br/>manifests]
    ROOT --> PIPE[pipelines/<br/>5 Azure DevOps YAMLs]
    ROOT --> TESTS[tests/]
    ROOT --> DOCKER[docker/<br/>3 Dockerfiles]

    SRC --> ORCH[orchestrator/<br/>FastAPI + routers]
    SRC --> AGENTS[agents/<br/>graph + 6 agent nodes]
    SRC --> K8S[k8s/<br/>client + actions]
    SRC --> AZ[azure/<br/>openai, search, kv, blob]
    SRC --> RAG[rag/<br/>ingest, retriever, embeddings]
    SRC --> LLMOPS[llmops/<br/>prompts, tracing, cost, eval]
    SRC --> DOMAIN[domain/<br/>models.py]
    SRC --> CTRL[controllers/<br/>event_watcher.py]

    classDef folder fill:#f5a623,color:#000
    class ROOT,DOCS,INFRA,SRC,UI,DEPLOY,PIPE,TESTS,DOCKER folder
```

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🤖 | AI Agent / Orchestrator |
| ☸️ | Kubernetes / AKS |
| 🧠 | LLM (GPT-4o) |
| 🔎 | Vector Search (RAG) |
| ☁️ | Azure Platform Service |
| 🖥️ | User Interface |
| 📊 | Observability |

---

> **Rendering tip:** On GitHub/Azure DevOps these render automatically.
> In VS Code install **"Markdown Preview Mermaid Support"** extension.
> To export as PNG/SVG use the [Mermaid Live Editor](https://mermaid.live).