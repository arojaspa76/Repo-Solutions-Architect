# CLAUDE.md — GenAIDemo

## Project
This repository contains the `GenAIDemo` project.
**GenAIDemo** (Generative Supply Chain using AI) is a modular, multi-agent AI solution built for Ecopetrol's GGO (Gas & Operations) area, targeting enterprise-grade supply chain intelligence via natural language.

Primary goal: build and evolve a modular AI agent solution with clear orchestration, routing, guardrails, observability, and deployment discipline — deployed on Microsoft Azure.

---

## Architecture

### Agent topology
- **Orchestrator**: Semantic Kernel (Python) — plans execution, routes to sub-agents, manages context window and semantic cache.
- **Sub-agents**: Azure AI Agent Service — one agent per supply chain domain, each with its own MCP Tools set and Azure AI Search index.
- **RAG engine**: Azure OpenAI `text-embedding-3-large` → Azure AI Search S1 (hybrid vector + BM25), one index per sub-agent domain.
- **LLMs**: `gpt-4o` (primary), `gpt-4o-mini` (lightweight routing/classification), `o3` (complex reasoning tasks). All via Azure AI Foundry.

### Domain sub-agents (v1)
| Agent module | Domain | Primary data sources |
|---|---|---|
| `crudo_pesado_intermedio` | Heavy/intermediate crude | ADF + Dataverse + SharePoint Online + OpenText|
| `refinados_petroquimicos` | Refined products & petrochemicals | ADF + Databases + External + SharePoint Online + OpenText |
| `licuados_energia` | LPG & energy | ADF + Web scraping + SharePoint Online + OpenText |
| `disponibilidad_sistemas` | System availability | ADF + Dataverse + SharePoint Online + OpenText |
| `diluyentes` | Diluents | ADF + SharePoint Online + OpenText |
| `gas` | Natural gas | ADF + Databases + SharePoint Online + OpenText |
| `combustible` | Fuel | ADF + External sources + SharePoint Online + OpenText |
| `desempeno_crudo_liviano` | Light crude performance | ADF + SharePoint Online + OpenText |
| `desempeno_integrado` | Integrated performance | ADF + Dataverse + Databases + SharePoint Online + OpenText |

New domains are added by subclassing `BaseGenAIDemoAgent` in `src/agents/` and registering MCP Tools — no changes to orchestrator layers above.

### Conversation & memory model
- Active session state: Redis (context window, semantic cache).
- Conversation history: Cosmos DB NoSQL, partitioned by `userId`, schema: `{userId, conversationId, messages[], summary, metadata}`.
- Context window strategy: last N turns full + older turns as compressed semantic summary stored in Cosmos DB.
- Semantic cache: queries with cosine similarity above configurable threshold are served from cache without LLM call.

### Auth
- Frontend auth: MSAL.js with OIDC/OAuth 2.0 against Microsoft Entra ID.
- Backend token validation: FastAPI middleware using `python-jose` / `msal`.
- Service-to-service: Azure Managed Identity — zero secrets in code or container env vars.
- All secrets in Azure Key Vault, accessed via Managed Identity with RBAC (no legacy Access Policies).

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI (async) |
| Frontend | React + TypeScript, MSAL.js |
| Mobile (future, ~5 months) | React Native — shares hooks, API client, auth logic with web |
| Orchestration | Semantic Kernel (Python SDK) |
| Sub-agents | Azure AI Agent Service |
| LLM platform | Azure AI Foundry (Azure OpenAI) |
| Embeddings | `text-embedding-3-large` |
| Vector search | Azure AI Search S1 — hybrid retrieval |
| Conversation store | Azure Cosmos DB (NoSQL API) |
| Session / cache | Azure Cache for Redis |
| Secrets | Azure Key Vault + Managed Identity |
| Containers | Docker — one image per service |
| Orchestration (prod) | Azure Container Apps (ACA) with KEDA |
| Registry | Azure Container Registry (ACR) |
| CI/CD | Azure DevOps Pipelines |
| IaC | Azure Bicep (all resources in `ops/`) |
| Observability | Azure Monitor + Application Insights + OpenTelemetry |
| Linting | `ruff` |
| Testing | `pytest`, minimum 70% coverage |

---

## Repository structure

```
vibecoding/
├── apps/
│   ├── api/src/                    # FastAPI service
│   │   ├── middleware/             # JWT auth, rate limit, security headers
│   │   ├── routers/                # HTTP route handlers (chat, agents, admin, etc.)
│   │   ├── main.py                 # FastAPI app factory + lifespan
│   │   └── schemas.py              # Pydantic request/response models
│   └── web/src/                    # React TypeScript frontend
│       ├── auth/                   # MSAL configuration
│       ├── components/             # UI components (chat, admin panel, etc.)
│       ├── hooks/                  # React Query data hooks
│       ├── locales/                # i18n translation files (es/en/fr)
│       ├── constants/              # Static domain definitions
│       ├── App.tsx                 # Root app component
│       ├── main.tsx                # React entry point
│       └── i18n.ts                 # i18n initialization
├── src/                            # Internal library — never deployed directly
│   ├── agents/
│   │   ├── tools/                  # Tool implementations (Azure Table, SQL, Cosmos, etc.)
│   │   ├── base.py                 # BaseGenAIDemoAgent + AgentResponse
│   │   ├── dynamic_agent.py        # Cosmos DB-driven agent (runtime definition)
│   │   ├── registry.py             # AgentRegistry singleton
│   │   ├── agente_crudos.py        # Crude oil supply chain agent
│   │   ├── agente_refinacion.py    # Refinery operations agent
│   │   ├── agente_gas.py           # Natural gas agent
│   │   ├── agente_licuados.py      # LPG agent
│   │   ├── agente_combustibles.py  # Fuel agent
│   │   └── agente_general.py       # General supply chain agent
│   ├── common/
│   │   └── exceptions.py           # Domain exception classes
│   ├── config/
│   │   └── settings.py             # Pydantic Settings — all env config
│   ├── core/
│   │   ├── kernel.py               # Semantic Kernel singleton (gpt4o + embedding)
│   │   ├── orchestrator.py         # GenAIDemoOrchestrator — route + execute
│   │   ├── router.py               # Intent classifier — LLM → RouterDecision
│   │   ├── permissions.py          # RBAC — static + dynamic agent access
│   │   ├── rate_limiter.py         # Redis sliding-window rate limiter
│   │   ├── resilience.py           # Circuit breaker + retry decorators
│   │   └── input_validator.py      # Input sanitization + injection detection
│   ├── data/
│   │   └── synthetic/              # Synthetic data generators (dev/test only)
│   ├── domain/
│   │   ├── agent_definition.py     # AgentDefinition dataclass
│   │   ├── agent_permission.py     # AgentPermission dataclass
│   │   ├── audit_event.py          # AuditEvent dataclass
│   │   └── tool_definition.py      # ToolDefinition dataclass (8 tool types)
│   ├── observability/
│   │   ├── logging.py              # JSON structured logging + OTEL trace injection
│   │   └── telemetry.py            # Azure Monitor setup + OTel metrics
│   ├── pipelines/
│   │   ├── chunker.py              # Word-based overlapping chunker
│   │   ├── indexing_pipeline.py    # Chunk → embed → upload to AI Search
│   │   └── rag_indexer.py          # Blob → OCR → index CLI pipeline
│   ├── rag/
│   │   ├── search_client.py        # GenAIDemoSearchClient (hybrid retrieval)
│   │   ├── retriever.py            # RAG retrieve() with Redis cache
│   │   ├── prompt_builder.py       # Injects retrieved context into system prompt
│   │   ├── index_manager.py        # AI Search index lifecycle (create/delete)
│   │   └── evaluator.py            # RAG quality metrics (precision@k, recall@k, MRR)
│   └── services/
│       ├── agent_definition_service.py   # CRUD for AgentDefinition in Cosmos DB
│       ├── agent_permission_service.py   # CRUD for AgentPermission in Cosmos DB
│       ├── audit_service.py              # Write AuditEvents to Cosmos DB
│       ├── blob_client.py                # Azure Blob Storage async client
│       ├── centro_cadena_client.py       # DB_Centro_Cadena_V2 async SQL client
│       ├── cosmos.py                     # Conversation CRUD in Cosmos DB
│       ├── docintelligence_client.py     # Azure Document Intelligence OCR
│       ├── graph_service.py              # Microsoft Graph API (users + app roles)
│       ├── query_loader.py               # SQL file loader from ops/queries/
│       ├── rag_document_service.py       # List/delete indexed documents in AI Search
│       ├── redis_client.py               # Redis async client singleton
│       ├── search.py                     # Sync AI Search upload + hybrid search
│       └── tool_definition_service.py    # CRUD for ToolDefinition in Cosmos DB
├── configs/
│   ├── prompts/agents/             # System prompts per agent domain (YAML)
│   ├── prompts/router.yaml         # Intent classifier system prompt
│   ├── prompts/synthesis.yaml      # Multi-agent synthesis prompt
│   └── security/injection_patterns.yaml  # Regex patterns for prompt injection detection
├── data/
│   ├── raw/                        # Source data — read-only
│   ├── interim/                    # In-progress ETL outputs
│   ├── processed/rag_eval/         # RAG evaluation datasets (JSON)
│   └── external/                   # Third-party reference data
├── docs/
│   ├── architecture/               # Cross-sprint living architecture documents
│   └── sprint_{n}/                 # Per-sprint documentation
├── ops/
│   ├── bicep/                      # Azure Bicep IaC — all Azure resources
│   ├── docker/                     # Dockerfiles + docker-compose
│   ├── k8s/                        # ACA manifests, Helm charts
│   └── scripts/                    # Automation scripts
├── tests/
│   ├── unit/                       # Fast unit tests — mocked Azure services
│   ├── integration/                # Real service integration tests
│   ├── e2e/                        # End-to-end conversation flow tests
│   └── load/                       # Locust load test scenarios
├── azure-pipelines-ci.yml          # CI pipeline
├── azure-pipelines-cd.yml          # CD blue-green pipeline to ACA
├── CLAUDE.md                       # AI assistant working instructions
├── Makefile                        # Developer commands
├── pyproject.toml                  # Project metadata, ruff, pytest, coverage config
└── README.md                       # Project README
```

---

## Working principles
- Prioritize correctness, maintainability, and minimal-risk changes.
- Make the smallest viable change that solves the requested problem.
- Do not refactor unrelated areas.
- Do not introduce new frameworks, dependencies, or architectural patterns unless explicitly requested.
- Preserve existing public contracts unless the task explicitly asks to change them.
- Keep behavior backward compatible whenever possible.

---

## How to work in this repo
- First understand the task and identify the exact files involved.
- Before editing, state a short plan when the task is non-trivial.
- Limit file reads to the minimum relevant set.
- Prefer targeted edits over broad rewrites.
- After changes, explain:
  - what changed
  - why it changed
  - any risks or follow-up items
- If information is missing, make the safest grounded assumption and state it clearly.

---

## Scope control
When solving a task:
- Touch only files directly related to the requested change.
- Avoid scanning the whole repository unless the user explicitly asks for repo-wide analysis.
- If the task appears broad, propose a bounded implementation first.
- For debugging, identify the likely execution path first, then inspect only the relevant modules.

---

## Architecture expectations
Prefer solutions aligned with:
- modular design — one responsibility per module
- explicit orchestration and routing responsibilities (orchestrator in `src/core/`, sub-agents in `src/agents/`)
- configuration-driven behavior via `src/config/` (Pydantic Settings)
- clear observability and error handling via `src/observability/`
- production-friendly code over experimental shortcuts

Avoid:
- hidden side effects
- duplicated business logic across sub-agents (promote to `src/common/`)
- mixing orchestration, transport, and domain concerns in one place
- hardcoded secrets, endpoints, or environment-specific values
- adding new sub-agent classes outside `src/agents/`
- bypassing `BaseGenAIDemoAgent` for new domain implementations

---

## Code style
- Keep code clear, consistent, and exact.
- Use descriptive names — domain terminology from Ecopetrol supply chain is preferred over generic names.
- Keep functions focused.
- Add comments only where they clarify non-obvious intent.
- Do not add decorative comments or unnecessary abstractions.
- Follow the existing project style unless it is clearly broken.
- Type hints on all public functions.

---

## Configuration and secrets
- **Never hardcode** secrets, tokens, passwords, connection strings, or private endpoints.
- All secrets live in **Azure Key Vault**, accessed via Managed Identity at runtime.
- Use `src/config/` (Pydantic Settings) as the single access point for all configuration.
- Preserve `.env`, config templates, and deployment conventions already used by the repo.
- `.env` is for local development only — never commit it.

---

## Testing and validation
For every meaningful code change:
- run the smallest relevant validation first
- prefer targeted tests before broader test suites
- if tests cannot be run, say so explicitly
- do not claim success without indicating what was actually validated

Validation order:
1. `ruff check` on touched files
2. focused unit tests in `tests/unit/` for touched modules
3. integration tests in `tests/integration/` only if service wiring was changed
4. e2e only if full conversation flow was modified

Coverage minimum: **70%** on `src/` modules.

---

## Editing & Deliverable Rules

- Do not rename files, move modules, or reorganize directories unless explicitly requested.
- Do not update lockfiles unless dependency changes are required.
- Do not modify `ops/`, `azure-pipelines.yml`, or Bicep files unless the task is directly about deployment or infrastructure.
- Do not remove existing logs, telemetry, or guards unless the task requires it.
- Do not modify `data/raw/` — it is read-only by convention.
- Strip notebook outputs before committing anything in `notebooks/`.

- At the start of every sprint, create `docs/sprint_{n}/` where `n` is the sprint number
  (zero-padded if the project exceeds 9 sprints: sprint_00, sprint_01, ...).
  Place all documentation generated during that sprint inside that folder.
  Do not mix documentation from different sprints in the same folder.
  The `docs/architecture/` folder is reserved for cross-sprint, living architecture documents
  (ADRs, system diagrams, OpenAPI specs) — do not put sprint-specific content there.

---

## Deliverable Completion Rules (MANDATORY)

A deliverable (PBI) is NOT complete until ALL of the following are done:

1. Implementation is finished
2. Validation steps are completed
3. docs/sprint_{n}/README.md is updated
4. PBI Summary is printed in the response

If any of these steps are missing, the deliverable is INCOMPLETE.

---

## README Update Instructions (STRICT)

At the end of every deliverable, update the README.md file located at `docs/sprint_{n}`:

1. Locate the "## Deliverables" section:
   - Find the corresponding PBI
   - Change status from [ ] to [x]

2. Locate the "## Deliverable Log" section:
   - Append a new line at the end using this format:
     - PBI-XX: <short description> — <YYYY-MM-DD>

Rules:
- Do NOT rewrite the entire file
- Do NOT remove existing entries
- Only append or update the relevant lines
- This step is mandatory and cannot be skipped

---

## Deliverable Summary (MANDATORY)

At the end of EVERY PBI, you MUST output a concise summary.

Format:

### PBI-XX Summary

(Replace XX with the actual PBI number being implemented, e.g., PBI-27)

#### Files Created or Modified

| File Name | Description |
|-----------|-------------|
| <file_path> | <what was created or changed> |

#### Validation Performed

| Item | Description |
|------|-------------|
| Lint / Tests / Manual checks | <what was executed> |

### What the module does

- Short functional description

#### Risks / Blockers

- List any risks, blockers, or open questions

Rules:
- Replace "PBI-XX" with the actual PBI number (e.g., PBI-27, PBI-28)
- The PBI number MUST match the deliverable being implemented
- Keep the summary short and precise
- Do NOT include large code blocks
- Do NOT skip this section under any circumstance
- Always place this summary at the END of the response
- Once the summary is provided, ask for confirmation of the next PBI

---

## Output format
When finishing a task, respond with:
1. **Summary** — what was done
2. **Files changed** — list with brief reason per file
3. **Validation performed** — what was run and result
4. **Risks or follow-ups** — unresolved items, assumptions made

---

## For large tasks
If the request is large or ambiguous:
- first produce a concise implementation plan
- identify assumptions
- suggest the smallest safe increment
- then execute only that increment unless asked for a larger rewrite

---

## Exploration policy

**Start here for most tasks:**
- `src/` and `tests/` — feature work, bugfixes, orchestration, agent logic, RAG, services

**Read only if the task touches these explicitly:**
- `configs/` — environment config changes
- `apps/` — startup flow, API routing, frontend wiring
- `ops/` — Docker, ACA, Bicep, CI/CD (high-impact, treat with care)

**Usually ignore:**
- `artifacts/`, `reports/`, `.pytest_cache/`, `.vscode/`
- `notebooks/` — exploration only, not implementation reference
- `models/` — only for prompt versioning or inference integration tasks
- `data/` — only for fixture or input/output debugging

---

## Definition of done
A task is done only when:
- the requested behavior is implemented or the issue is isolated
- affected files remain internally consistent
- `ruff` passes on touched files
- relevant tests pass or their absence is explicitly justified
- unresolved items are clearly called out

---

## Key project contacts
- **GGO Lead**: Rohyman Ramos
- **Advanced Analytics**: Francisco Medina
- **Data Scientist / Dev**: Andrés Felipe Rojas Parra
- **Client**: Ecopetrol S.A. — VTI (Vicepresidencia de Tecnología e Innovación)

---

## Token efficiency rules

These rules are mandatory in every session. They exist to maximize
useful work per context window.

- Read only the files directly needed for the current task.
  Never read a file "just to understand the project".
- When reading a file, use line ranges if only part is needed.
- Never repeat back large blocks of code in your response.
  Show only the changed lines with brief context.
- Never summarize files you just read unless explicitly asked.
- Never explain what you are about to do at length — just do it.
- After completing a task, give the shortest accurate summary possible.
- Do not re-read CLAUDE.md or other reference files mid-session
  unless the task explicitly requires it.
- If a task requires reading more than 5 files, stop and ask
  which files are actually needed before reading anything.
- Prefer targeted edits (str_replace) over full file rewrites.
- Never output a full file unless the user explicitly asks for it.
- **Direct Action**: Do not use "Thinking Mode" for trivial code changes or file reads.
- **Minimal Output**: Only rewrite the specific lines or functions that need changing. Do not output the entire file unless explicitly asked.
- **Subagent Policy**: You are FORBIDDEN from spawning subagents for file exploration or status checks. Use local tools directly.
- **Compactness**: If the conversation history exceeds 5 turns, alert me to run `/compact`.
- **Code Diffs**: Always prefer providing `diffs` instead of full file rewrites to save output tokens.

---

## Agent and subagent constraints

CRITICAL — read before every task:

- Never spawn subagents unless explicitly told to with "run in parallel".
- Execute all tasks sequentially in the main agent context.
- Never use the Task tool for work that can be done directly.
- One file edit at a time — do not batch multiple file operations
  into parallel subagent calls.
- If you feel the urge to spawn a subagent, stop and do the work
  directly instead.

---

## Context size constraints

- Never read more than 3 files per task unless explicitly required.
- When reading source files, use line ranges — never read a full
  file if you only need part of it.
- After writing code, do not re-read it to "verify" unless the
  user asks. Trust your output.
- Never load the full compiled Bicep JSON (*.json in ops/bicep/).
  Read only the .bicep source files.
- Use /compact when context feels large before starting a new PBI.