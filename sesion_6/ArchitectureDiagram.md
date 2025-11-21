# Architecture Diagram (PlantUML)
Generic architecture combining: RAG + ReAct + Multi-Agent + Guardrails, with the option to run LLM on NIM/Triton (on-premises/Jetson) or in the cloud.

```plantuml

@startuml
skinparam componentStyle rectangle

actor User

rectangle "Client Apps" {
  [Web UI]
  [Mobile App]
  [CLI]
}

rectangle "API Gateway / BFF" as APIGW

rectangle "LLM Orchestrator Service" as Orchestrator {
  component "Policy & Guardrails\n(PII, Toxicity, RBAC)" as Guardrails
  component "Conversation Manager\n(Session, History, Memory)" as ConvMgr
  component "Planner Agent\n(CoT / ReAct)" as Planner
  component "Worker Agents\n(RAG, Coder, Tools)" as Workers
}

rectangle "Tools & Data" {
  database "Vector Store /\nKnowledge Bases\n(Azure AI Search /\nBedrock KB /\nVertex Search /\nMilvus/Pinecone)" as KB
  database "Operational DBs\n(SQL/NoSQL)" as DB
  component "External APIs\n(ERP, CRM, IoT, HSE)" as APIs
}

rectangle "LLM Backends" {
  component "Cloud LLMs\n(Azure OpenAI,\nBedrock, Vertex, etc.)" as CloudLLM
  component "On-Prem LLM\nNVIDIA NIM + Triton\n(TensorRT-LLM /\nJetson Edge)" as LocalLLM
}

User --> [Web UI]
User --> [Mobile App]
User --> [CLI]

[Web UI] --> APIGW
[Mobile App] --> APIGW
[CLI] --> APIGW

APIGW --> Guardrails
Guardrails --> ConvMgr
ConvMgr --> Planner

Planner --> Workers : ReAct\n(Thought/Action)
Workers --> KB : retrieve
Workers --> DB : queries
Workers --> APIs : tools

Workers --> CloudLLM : calls (if policy allows)
Workers --> LocalLLM : calls (for edge / on-prem)

CloudLLM --> Workers
LocalLLM --> Workers

Workers --> ConvMgr
ConvMgr --> APIGW
APIGW --> User : Response

@enduml

```

You can reuse this diagram as a "standard template" for AMVA/Colsubsidio/oil company proposals, simply replacing the logos and cloud elements.