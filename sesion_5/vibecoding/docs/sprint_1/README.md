# Sprint 1 — Backend Core

Goal: FastAPI backend with Semantic Kernel orchestration, Entra ID JWT auth, and
conversational history in Cosmos DB, streamed via SSE.

Note: implemented against CLAUDE.md's canonical repo structure (root `src/`,
`apps/api/src/`), not the isolated `apps/api/` project layout literally described in
`initial_prompt.md` — see Deliverable Log for the file-path mapping rationale.

## Deliverables

- [x] D1: pyproject.toml — Sprint 1 dependencies added to root pyproject.toml
- [x] D2: src/config/settings.py — Key Vault-backed Settings singleton
- [x] D3: apps/api/src/main.py — FastAPI app factory + lifespan
- [x] D4: src/core/kernel.py — orchestrator (gpt-4o) / agent (gpt-4o-mini) kernel factories
- [x] D5: apps/api/src/middleware/auth.py + schemas.py — Entra ID JWT auth, User model
- [x] D6: src/core/orchestrator.py + src/core/router.py — intent classification + dispatch
- [x] D7: src/agents/base.py — BaseGenAIDemoAgent + AgentResponse
- [x] D8: src/agents/agente_*.py — 6 domain sub-agents
- [x] D9: src/agents/registry.py — AgentRegistry
- [x] D10: src/core/context_manager.py — token-windowed conversation context
- [x] D11: src/services/cosmos.py — CosmosRepository CRUD
- [x] D12: apps/api/src/routers/conversations.py — 7 endpoints incl. SSE streaming
- [x] D13: apps/api/src/routers/health.py — dependency health check
- [x] D14: apps/api/Dockerfile — multi-stage build, repo-root context
- [x] D15: Tests — 34 unit + integration tests, 82% coverage on touched modules

## Deliverable Log

- PBI-11: Sprint 1 Backend Core implemented against CLAUDE.md's repo structure
  (root `src/`, `apps/api/src/`) instead of `initial_prompt.md`'s isolated
  `apps/api/` project layout — decision confirmed with user due to conflict with
  the existing CI pipeline and root `pyproject.toml`. Delivered: Key Vault-backed
  settings, SK kernel factories, JWT auth (fastapi-azure-auth), intent router +
  orchestrator with SSE streaming, 6 domain sub-agents, token-windowed
  conversation context with Cosmos persistence, 7 conversation endpoints, health
  check, Dockerfile. 34 tests passing, 82% coverage (target: 80%). — 2026-07-31

## Known Risks / Follow-ups

- `ops/k8s/backend-deployment.yaml` probes hit `/api/health` (Sprint 0), but the
  app now mounts routes under `/api/v1/health` (Sprint 1 spec). Not fixed here —
  `ops/` is out of scope for a backend-core task per CLAUDE.md; needs a follow-up
  PBI to update the K8s manifest probe paths.
- `test_list_conversations_requires_auth` exercises the real `fastapi-azure-auth`
  scheme (no dependency override) to assert non-200 without a token. It performs
  a real OpenID discovery call and will be flaky/slow without network access —
  worth revisiting with a proper auth-failure mock in a later sprint.
- No RAG/document search yet — sub-agents respond from training knowledge only,
  as scoped for Sprint 1 (`sources=[]`). Sprint 2 adds Azure AI Search integration.
- Root `pyproject.toml`'s coverage config combines Sprint 0 (`src`) and Sprint 1
  (`apps/api/src`) into one gate; CI's `build-backend.yml` still runs
  `--cov=src` only — should be updated to include `apps/api/src` in a follow-up.
