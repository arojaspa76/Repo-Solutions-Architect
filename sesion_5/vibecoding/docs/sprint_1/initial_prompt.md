You are acting as a senior Python backend engineer and AI systems architect.
Sprint 0 is complete: Azure infrastructure is provisioned (Key Vault, Cosmos DB,
Redis, ACR, AKS, Entra ID App Registration). All secrets are in Key Vault.

Your task is Sprint 1 of GenAIDemo: "Backend Core".
Implement the FastAPI backend with Semantic Kernel, the Orchestrator Agent,
Entra ID JWT authentication, and conversational history management with
streaming SSE responses.

Read CLAUDE.md before doing anything else. Follow all working principles and editing rules defined there.
Create docs/sprint_0/ now. All documentation you produce during this sprint goes there.

---

## SPRINT CONTEXT

Sprint Goal: Deliver a fully functional backend that accepts a user message,
routes it to the correct domain agent via the Orchestrator, and streams the
response token-by-token via Server-Sent Events, with full conversation
history persisted in Cosmos DB.

Sprint 1 is complete when:
- FastAPI starts in Docker without errors
- /api/health returns 200 with status of all dependencies
- OrchestratorAgent correctly classifies intents for all 6 domains
- JWT from Entra ID is validated; protected endpoints return 401 without it
- Messages stream via SSE and are persisted in Cosmos DB
- pytest --cov reports >= 80% coverage on all new modules

---

## ENVIRONMENT (already provisioned from Sprint 0)

All secrets are in Azure Key Vault. Read them at startup via DefaultAzureCredential.
Key Vault URI is in env var KEY_VAULT_URI.

Secrets in Key Vault (exact names):
  COSMOS-DB-CONNECTION-STRING    → Cosmos DB NoSQL connection string
  REDIS-ACCESS-KEY               → Redis primary access key
  REDIS-HOST                     → Redis hostname
  AZURE-AD-CLIENT-ID             → Entra ID app client ID
  AZURE-AD-CLIENT-SECRET         → Entra ID client secret
  AZURE-AD-TENANT-ID             → Entra ID tenant ID
  AZURE-OPENAI-KEY               → Azure OpenAI API key
  AZURE-OPENAI-ENDPOINT          → Azure OpenAI endpoint URL (also in configmap)

Azure OpenAI deployments (already deployed):
  Orchestrator: gpt-4o           deployment name: "gpt-4o"
  Sub-agents:   gpt-4o-mini      deployment name: "gpt-4o-mini"
  Embeddings:   text-embedding-3-large  deployment name: "text-embedding-3-large"

Cosmos DB:
  Database:   genaidemo-db
  Container:  conversations   partition key: /user_id

Redis:
  SSL: true, port: 6380

---

## REPOSITORY LOCATION

Work inside: vibecoding/apps/api/

Final structure must be:
```
apps/api/
├── Dockerfile
├── pyproject.toml          ← uv-managed, Python 3.12
├── uv.lock
└── src/
    ├── main.py             ← FastAPI app entry point
    ├── agents/
    │   ├── __init__.py
    │   ├── orchestrator.py
    │   ├── base_agent.py
    │   ├── domain_registry.py
    │   └── domains/
    │       ├── __init__.py
    │       ├── general.py
    │       ├── refinacion.py
    │       ├── combustibles.py
    │       ├── crudos.py
    │       ├── gas.py
    │       └── licuados.py
    ├── api/
    │   ├── __init__.py
    │   ├── middleware/
    │   │   ├── __init__.py
    │   │   ├── logging_middleware.py
    │   │   └── request_id.py
    │   └── routes/
    │       ├── __init__.py
    │       ├── conversations.py
    │       └── health.py
    ├── auth/
    │   ├── __init__.py
    │   ├── entra_id.py
    │   └── models.py
    ├── config/
    │   ├── __init__.py
    │   ├── settings.py
    │   └── domains/
    │       ├── general.yaml
    │       ├── refinacion.yaml
    │       ├── combustibles.yaml
    │       ├── crudos.yaml
    │       ├── gas.yaml
    │       └── licuados.yaml
    ├── core/
    │   ├── __init__.py
    │   ├── dependencies.py
    │   └── kernel_factory.py
    └── history/
        ├── __init__.py
        ├── context_manager.py
        └── cosmos_repository.py
```

---

## DELIVERABLE 1 — pyproject.toml

Use uv. Python 3.12. Dependencies:

```toml
[project]
name = "genaidemo-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "semantic-kernel>=1.11.0",
    "azure-identity>=1.19.0",
    "azure-keyvault-secrets>=4.9.0",
    "azure-cosmos>=4.9.0",
    "redis>=5.2.0",
    "fastapi-azure-auth>=5.0.0",
    "tiktoken>=0.8.0",
    "httpx>=0.27.0",
    "structlog>=24.4.0",
    "python-multipart>=0.0.12",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.27.0",
    "respx>=0.21.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.8.0",
]
```

---

## DELIVERABLE 2 — src/config/settings.py

```python
from pydantic_settings import BaseSettings
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class Settings(BaseSettings):
    # Read from environment variable
    key_vault_uri: str
    environment: str = "dev"
    project_name: str = "genaidemo"

    # Populated at startup from Key Vault
    cosmos_connection_string: str = ""
    redis_host: str = ""
    redis_access_key: str = ""
    azure_ad_client_id: str = ""
    azure_ad_tenant_id: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def load_from_key_vault(self) -> None:
        """Load all secrets from Azure Key Vault using DefaultAzureCredential."""
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=self.key_vault_uri, credential=credential)
        # Load each secret by name
        # Map: KV secret name → settings attribute name
        ...

settings = Settings()
```

Implement load_from_key_vault() fully. Call it in the FastAPI lifespan.
Add a @lru_cache wrapper so the settings object is a singleton.

---

## DELIVERABLE 3 — src/main.py

FastAPI application with:
- @asynccontextmanager lifespan that:
  1. Calls settings.load_from_key_vault()
  2. Initializes CosmosRepository
  3. Initializes Redis client (ssl=True)
  4. Creates SK kernel instances (orchestrator + agents)
  5. Stores all in app.state
  6. On shutdown: closes Redis and Cosmos connections
- CORS middleware: allow all origins in dev, restrict in prod
- TrustedHost middleware
- Custom RequestID middleware (generate UUID per request, add to response headers)
- Custom structlog logging middleware
- Include routers: conversations, health
- Mount under prefix /api/v1

---

## DELIVERABLE 4 — src/core/kernel_factory.py

```python
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

def create_orchestrator_kernel(settings: Settings) -> Kernel:
    """Create a Kernel with GPT-4o for the orchestrator."""
    kernel = Kernel()
    kernel.add_service(AzureChatCompletion(
        service_id="orchestrator",
        deployment_name="gpt-4o",
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
    ))
    return kernel

def create_agent_kernel(settings: Settings, domain: str) -> Kernel:
    """Create a Kernel with GPT-4o-mini for a domain sub-agent."""
    ...
```

---

## DELIVERABLE 5 — src/auth/entra_id.py and models.py

### entra_id.py
Use fastapi-azure-auth SingleTenantAzureAuthorizationCodeBearer.
Configure with settings.azure_ad_client_id and settings.azure_ad_tenant_id.
Scopes:
  - api://{client_id}/Chat.ReadWrite
  - api://{client_id}/History.Read

Export: azure_scheme (the dependency)

### models.py
```python
from pydantic import BaseModel

class User(BaseModel):
    oid: str           # Entra ID Object ID — use as user_id in Cosmos
    tid: str           # Tenant ID
    email: str
    display_name: str
    roles: list[str] = []

    @classmethod
    def from_token(cls, token_claims: dict) -> "User":
        """Build User from validated JWT claims."""
        ...
```

---

## DELIVERABLE 6 — src/agents/orchestrator.py

### OrchestratorAgent class

System prompt (include verbatim in the file):
```
You are the orchestrator agent for GenAIDemo at TechCorp Inc.
Your ONLY task is to analyze the user's query and decide which domain
sub-agent should handle it.

Available domains and their scope:
- REFINACION:    Refinery operations, refining processes, yields, margins, CDU/VDU
- COMBUSTIBLES:  Fuels, gasoline, diesel, jet fuel, distribution, pricing, demand
- CRUDOS:        Crude oil, grades, API gravity, sulfur, extraction, quality, blending
- GAS:           Natural gas, LNG, pipelines, compression, GPA standards
- LICUADOS:      LPG, propane, butane, liquefied gases, storage, transport
- GENERAL:       Company policies, cross-domain questions, greetings, anything else

Respond ONLY with a JSON object. No explanation. No markdown. Just JSON:
{
  "target_agent": "REFINACION|COMBUSTIBLES|CRUDOS|GAS|LICUADOS|GENERAL",
  "confidence": 0.0,
  "reasoning": "one sentence",
  "requires_multi_agent": false,
  "additional_agents": []
}

If confidence < 0.5, set target_agent to GENERAL.
If the question spans 2 domains, set requires_multi_agent to true.
```

Methods:
- `async classify_intent(message: str, conversation_summary: str = "") -> RoutingDecision`
  Call GPT-4o with the system prompt. Parse JSON response.
  Return RoutingDecision(target_agent, confidence, requires_multi_agent, additional_agents)
- `async process(message: str, context: ConversationContext, user: User) -> AgentResponse`
  1. classify_intent()
  2. If requires_multi_agent: gather responses from multiple agents
  3. Else: invoke single target agent
  4. Return AgentResponse with content, sources, agent_domain, token_usage

### RoutingDecision and AgentResponse dataclasses (define in this file)

---

## DELIVERABLE 7 — src/agents/base_agent.py

```python
class DomainAgent(ABC):
    """Abstract base class for all domain-specific sub-agents."""

    def __init__(
        self,
        kernel: Kernel,
        domain: str,
        system_prompt: str,
        tools: list = None,
    ):
        self.domain = domain
        self.kernel = kernel
        # Register tools as plugins
        ...
        self.agent = ChatCompletionAgent(
            kernel=kernel,
            service_id=f"agent-{domain.lower()}",
            name=f"{domain}Agent",
            instructions=system_prompt,
        )

    async def invoke(
        self,
        message: str,
        context: "ConversationContext",
    ) -> AgentResponse:
        """Invoke the agent with the user message and conversation context."""
        messages = context.get_windowed_messages(max_tokens=12000)
        messages.append({"role": "user", "content": message})
        response = await self.agent.invoke(messages)
        return AgentResponse(
            domain=self.domain,
            content=response.content,
            sources=[],  # Populated by RAG plugin in Sprint 2
            token_usage=response.metadata.get("usage", {}),
        )
```

---

## DELIVERABLE 8 — src/agents/domains/*.py (6 files)

Create all 6 domain agent subclasses. Each file is minimal in Sprint 1
(RAG plugins are added in Sprint 2). Focus on the system prompts.

System prompt requirements for each agent:
- Language: ALWAYS respond in Spanish. Keep technical terms in English.
- Role: Describe the agent's expertise domain
- Citation: "When referencing information, mention the source document if available."
- Tone: Professional, precise, enterprise-appropriate

### general.py system prompt template:
```
You are GenAIDemo's General Agent for TechCorp Inc.
You handle cross-domain questions, company policies, greetings, and any
question that does not belong to a specific domain.
Respond in Spanish. Be concise and helpful.
If the question clearly belongs to a specific domain, acknowledge it and
suggest the user ask in that context.
```

### refinacion.py, combustibles.py, etc.:
Follow same pattern, customizing the domain expertise description.
For Sprint 1, these agents respond from their training knowledge only
(RAG search plugin is integrated in Sprint 2).

---

## DELIVERABLE 9 — src/agents/domain_registry.py

```python
from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class DomainConfig:
    name: str
    display_name: str
    description: str
    model: str           # "gpt-4o-mini" for all domains
    system_prompt_file: str
    tools: list[str]
    enabled: bool
    max_tokens: int

class DomainRegistry:
    """Loads domain configurations from YAML files at startup."""

    def __init__(self, config_path: str = "src/config/domains/"):
        self.domains: dict[str, DomainConfig] = {}
        self._load_domains(config_path)

    def _load_domains(self, path: str) -> None:
        ...

    def get_domain(self, name: str) -> DomainConfig | None:
        ...

    def list_enabled(self) -> list[str]:
        ...

    def register_domain(self, config: DomainConfig) -> None:
        """Register a new domain at runtime without restart."""
        ...
```

Create the 6 YAML files in src/config/domains/:
```yaml
# general.yaml
name: "GENERAL"
display_name: "General"
description: "Cross-domain questions, policies, greetings, fallback"
model: "gpt-4o-mini"
system_prompt_file: "src/config/prompts/general.txt"
tools: []
enabled: true
max_tokens: 4096
```

---

## DELIVERABLE 10 — src/history/context_manager.py

```python
import tiktoken

class ConversationContext:
    MAX_CONTEXT_TOKENS: int = 16_000
    SUMMARY_THRESHOLD: int = 12_000
    ENCODING: str = "cl100k_base"  # tiktoken encoding for GPT-4o

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        cosmos_repo: "CosmosRepository",
        summary: str = "",
    ):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.cosmos = cosmos_repo
        self.messages: list[dict] = []
        self.summary: str = summary
        self._enc = tiktoken.get_encoding(self.ENCODING)

    def _count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _total_tokens(self) -> int:
        return sum(self._count_tokens(m["content"]) for m in self.messages)

    def get_windowed_messages(self, max_tokens: int = None) -> list[dict]:
        """Return messages fitting within the context window, newest first."""
        ...

    async def add_message(
        self, role: str, content: str, metadata: dict = None
    ) -> None:
        """Add a message and persist to Cosmos DB. Trigger summarization if needed."""
        ...

    async def _summarize_older_messages(self) -> None:
        """Summarize the first half of messages using GPT-4o-mini."""
        # Use a simple SK kernel call: "Summarize this conversation in 3 sentences in Spanish:"
        ...

    async def load_from_cosmos(self) -> None:
        """Load conversation history from Cosmos DB into memory."""
        ...
```

---

## DELIVERABLE 11 — src/history/cosmos_repository.py

Implement CosmosRepository with these methods:

```python
class CosmosRepository:
    def __init__(self, connection_string: str):
        self.client = CosmosClient.from_connection_string(connection_string)
        self.container = self.client \
            .get_database_client("genaidemo-db") \
            .get_container_client("conversations")

    async def get_conversation(self, conversation_id: str, user_id: str) -> dict | None:
        """Get a conversation by ID. Returns None if not found."""
        ...

    async def list_conversations(
        self, user_id: str, tenant_id: str, limit: int = 50
    ) -> list[dict]:
        """List conversations for a user, ordered by updated_at desc."""
        ...

    async def upsert_conversation(self, conversation: dict) -> dict:
        """Create or update a conversation document."""
        ...

    async def append_message(
        self, conversation_id: str, user_id: str, message: dict
    ) -> None:
        """Append a message to the conversation's messages array."""
        ...

    async def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        ...

    async def search_conversations(
        self, user_id: str, query: str, limit: int = 20
    ) -> list[dict]:
        """Full-text search in conversation titles and message content."""
        ...
```

Cosmos DB document schema:
```json
{
  "id": "uuid",
  "user_id": "entra_oid",
  "tenant_id": "entra_tid",
  "title": "Auto-generated from first message (first 60 chars)",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "messages": [
    {
      "id": "uuid",
      "role": "user | assistant | system",
      "content": "...",
      "timestamp": "ISO 8601",
      "metadata": {
        "agent": "REFINACION",
        "tokens_used": 350,
        "sources": [],
        "latency_ms": 1200
      }
    }
  ],
  "summary": "Running conversation summary...",
  "tags": [],
  "is_archived": false
}
```

---

## DELIVERABLE 12 — src/api/routes/conversations.py

Implement 7 endpoints. All require JWT via Depends(azure_scheme).

```python
router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("/", response_model=list[ConversationSummary])
async def list_conversations(user: User = Depends(get_current_user), ...):
    """List conversations for the authenticated user."""

@router.post("/", response_model=ConversationDetail, status_code=201)
async def create_conversation(user: User = Depends(get_current_user), ...):
    """Create a new empty conversation."""

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, user: User = ...):
    """Get a conversation with all messages."""

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> StreamingResponse:
    """Send a message and stream the response via SSE."""
    async def event_stream():
        # 1. Load or create ConversationContext
        # 2. Add user message to context
        # 3. Stream orchestrator response:
        async for chunk in orchestrator.process_stream(...):
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.put("/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(conversation_id: str, body: ConversationUpdate, ...):
    """Rename or archive a conversation."""

@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, user: User = ...):
    """Permanently delete a conversation."""

@router.get("/search", response_model=list[ConversationSummary])
async def search_conversations(q: str, user: User = ...):
    """Search conversations by content."""
```

Define Pydantic request/response models:
- ConversationSummary: id, title, updated_at, message_count, last_agent
- ConversationDetail: all fields + messages array
- MessageCreate: content (str, min 1 char, max 4000 chars), domain_override (optional)
- ConversationUpdate: title (optional), is_archived (optional)

---

## DELIVERABLE 13 — src/api/routes/health.py

```python
@router.get("/health")
async def health_check(
    cosmos: CosmosRepository = Depends(get_cosmos),
    redis_client = Depends(get_redis),
) -> dict:
    """Health check endpoint — returns status of all dependencies."""
    checks = {}

    # Cosmos DB: try to read database properties
    try:
        ... # ping cosmos
        checks["cosmos_db"] = "healthy"
    except Exception as e:
        checks["cosmos_db"] = f"unhealthy: {str(e)[:100]}"

    # Redis: PING command
    try:
        ... # await redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)[:100]}"

    overall = "healthy" if all("healthy" == v for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "version": "0.1.0",
        "environment": settings.environment,
        "dependencies": checks,
    }
```

Return HTTP 200 if healthy, 503 if degraded.

---

## DELIVERABLE 14 — Dockerfile (apps/api/Dockerfile)

```dockerfile
# Project:     GenAIDemo
# Component:   Backend API
# Description: Multi-stage Docker build for FastAPI backend
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv --no-cache-dir

FROM base AS builder
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS production
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import httpx; r=httpx.get('http://localhost:8000/api/v1/health'); exit(0 if r.status_code==200 else 1)"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--log-level", "info"]
```

---

## DELIVERABLE 15 — Tests

### tests/unit/test_orchestrator.py
- Mock SK ChatCompletionAgent to return controlled JSON routing decisions
- test_route_to_refinacion(): assert target_agent == "REFINACION"
- test_route_to_combustibles(): assert target_agent == "COMBUSTIBLES"
- test_route_to_crudos(), test_route_to_gas(), test_route_to_licuados()
- test_route_to_general(): assert target_agent == "GENERAL"
- test_low_confidence_fallback(): confidence=0.3 → GENERAL
- test_multi_agent_routing(): requires_multi_agent=True

### tests/unit/test_context_manager.py
- test_get_windowed_messages_respects_token_limit()
- test_add_message_triggers_summarization_at_threshold()
- test_summary_injected_as_system_message()
- test_total_tokens_counting()

### tests/unit/test_auth.py
- test_valid_jwt_returns_user()
- test_expired_jwt_returns_401()
- test_missing_scope_returns_403()
- test_user_from_token_claims()

### tests/unit/test_health.py
- test_health_all_healthy_returns_200()
- test_health_cosmos_down_returns_503()
- test_health_redis_down_returns_503()

### tests/integration/test_conversations_api.py
- Uses httpx.AsyncClient with app (no real Azure calls)
- Mock CosmosRepository and OrchestratorAgent
- test_list_conversations_requires_auth()
- test_create_conversation_returns_201()
- test_send_message_streams_sse()
- test_delete_conversation_returns_204()

---

## CODING STANDARDS

- All files must start with the header comment block:
  # Project:     GenAIDemo
  # Component:   <name>
  # Description: <one line>
  # Owner:       Andrés Felipe Rojas Parra
  # Created:     2026-07

- Type hints on ALL functions (no `Any` without justification)
- Docstrings on all public classes and methods
- No bare `except:` — always `except SpecificException as e:`
- Black-compatible formatting (88 char line limit)
- Use `structlog.get_logger(__name__)` for all logging
- Log at INFO: request_id, user_id, conversation_id, agent_domain, latency_ms
- Never log: JWT tokens, secrets, connection strings, user message content

---

## IMPORTANT NOTES

1. In Sprint 1, sub-agents do NOT have RAG plugins. They respond from
   LLM training knowledge only. RAG integration happens in Sprint 2.
   DomainAgent.invoke() returns sources=[] for now.

2. OrchestratorAgent.process_stream() should yield SSEChunk objects:
   - type="delta", data={"text": "token"} during generation
   - type="agent", data={"domain": "REFINACION"} at start
   - type="sources", data={"sources": []} at end (empty in Sprint 1)
   - type="done" as final event

3. ConversationContext does NOT load all messages from Cosmos at every
   request. Use load_from_cosmos() only when the context is first created
   in a new server instance. Keep it in Redis (key: ctx:{conversation_id})
   with TTL of 1 hour as a serialized JSON for warm sessions.

4. The send_message endpoint must handle the case where conversation_id
   does not exist: create a new conversation document automatically with
   title = first 60 chars of the user's message.

5. process_stream() must catch ALL exceptions from SK and yield an error
   SSE event before closing the stream:
   data: {"type": "error", "message": "An error occurred. Please try again."}
   Never expose internal error details to the client.

---

## START INSTRUCTIONS

Execute in this order:

1. Create pyproject.toml and run `uv sync` to generate uv.lock
2. Create the full directory structure with __init__.py stubs
3. Implement src/config/settings.py with Key Vault integration
4. Implement src/core/kernel_factory.py
5. Implement src/auth/entra_id.py and models.py
6. Implement src/history/cosmos_repository.py
7. Implement src/history/context_manager.py
8. Create domain config YAMLs (6 files in src/config/domains/)
9. Implement src/agents/base_agent.py
10. Implement src/agents/orchestrator.py
11. Implement all 6 src/agents/domains/*.py
12. Implement src/agents/domain_registry.py
13. Implement src/api/routes/health.py
14. Implement src/api/routes/conversations.py with all 7 endpoints
15. Implement src/main.py (ties everything together)
16. Create Dockerfile
17. Write all tests (unit first, then integration)
18. Run: pytest tests/unit --cov=src --cov-report=term-missing
    Target: >= 80% coverage on all modules

After completing all steps, print:

---
[SPRINT 1 COMPLETE]

Files created: <count>
Test results: <X passed, Y failed>
Coverage: <percentage>%

Ready for Sprint 2: RAG Pipeline + Azure AI Search integration.
---
