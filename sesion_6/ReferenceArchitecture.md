# Reference architecture for LLMs

When it comes to large language model (LLM) applications in the cloud, each of the major providers has published **reference architectures** that describe the major components, design patterns, security/governance measures, and typical deployment topologies. Below are the key references:

## • Azure  
- **Article**: “Baseline Microsoft Foundry Chat Reference Architecture”  
  URL: https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-azure-ai-foundry-chat :contentReference[oaicite:0]{index=0}  
- **Description**: Shows how to build and deploy an enterprise chat application using Azure AI Foundry + Azure OpenAI. Includes UI layer, agent/orchestrator, data stores (for grounding), private network integration, managed identity, and security controls.

### 1. Azure – Azure AI Foundry + Azure OpenAI
#### 1.1. Key Official Architectures

1. Basic / Baseline Azure AI Foundry Chat Reference Architecture
* Client (web/app) → Agent Service in Foundry → Azure OpenAI.
* The agent orchestrates grounding (RAG), data store calls, and tools.
* Designed for simple enterprise chat, but already includes:
    * Foundry Agent Service as the orchestrator.
    * Connection to Azure AI Search, Cosmos DB, SQL, etc. for grounding.

2. RAG Solution Design and Evaluation Guide

* Formal RAG Reference Architecture:
    * Client Application → API/Backend → Orchestrator/Prompt Flow → Azure AI Search (vector/semantic index) + storage (Blob, Data Lake) → Azure OpenAI for generation.
* Includes considerations for: chunking, evaluation, human feedback, automated evaluation, etc.

3. RAG Tutorial with Azure OpenAI + Azure AI Search (.NET + Blazor)

* Concrete diagram: Blazor App → Azure App Service → Azure AI Search + Azure OpenAI.
* Shows the complete chat flow with grounding, citing sources.

4. Azure OpenAI Architecture Patterns & Landing Zones

* Patrones típicos:
    * AOAI + Front Door / App Gateway / APIM.
    * Multi-region, failover, seguridad con Private Link, RBAC, Key Vault.
* [Repo de landing zone con arquitecturas enterprise, Bicep/Terraform y diagramas.](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/azure-openai-architecture-patterns-and-implementation-steps/3979934?utm_source=chatgpt.com)

```text
Azure – Basic AI Foundry Chat Reference Architecture
https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/basic-azure-ai-foundry-chat

Azure – Baseline AI Foundry Chat Reference Architecture
https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-azure-ai-foundry-chat

Azure – RAG Solution Design and Evaluation Guide
https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide

Azure – RAG app with Azure OpenAI + Azure AI Search (.NET tutorial)
https://learn.microsoft.com/en-us/azure/app-service/tutorial-ai-openai-search-dotnet

Azure – Azure OpenAI architecture patterns (TechCommunity)
https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/azure-openai-architecture-patterns-and-implementation-steps/3979934

Azure – Azure OpenAI Landing Zone reference architectures (GitHub)
https://github.com/Azure/azure-openai-landing-zone
```


## • AWS  
- **Page**: “AWS Reference Architecture Diagrams”  
  URL: https://aws.amazon.com/architecture/reference-architecture-diagrams/ :contentReference[oaicite:1]{index=1}  
- **Description**: A library of diagrams built by AWS that cover generative AI, machine learning, data lakes, and agent-based workloads. While not always specific to LLMs, they serve as high-level reference for AI/ML architecture on AWS.

## • GCP (Google Cloud Platform)  
- **Page**: “AI and machine learning resources | Cloud Architecture Center”  
  URL: https://cloud.google.com/architecture/ai-ml :contentReference[oaicite:2]{index=2}  
- **Description**: Offers generative AI, agentic AI, RAG, ML Ops reference architectures. Includes design guides and reference diagrams on deploying AI/ML workloads at enterprise scale on Google Cloud.

---