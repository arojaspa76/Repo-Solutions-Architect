# Reference architecture for LLMs

When it comes to large language model (LLM) applications in the cloud, each of the major providers has published **reference architectures** that describe the major components, design patterns, security/governance measures, and typical deployment topologies. Below are the key references:

## 1. Azure – Azure AI Foundry + Azure OpenAI  
- **Article**: “Baseline Microsoft Foundry Chat Reference Architecture”  
  URL: https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-azure-ai-foundry-chat
- **Description**: Shows how to build and deploy an enterprise chat application using Azure AI Foundry + Azure OpenAI. Includes UI layer, agent/orchestrator, data stores (for grounding), private network integration, managed identity, and security controls.

### 1.1. Key Official Architectures

#### 1. Basic / Baseline Azure AI Foundry Chat Reference Architecture
* Client (web/app) → Agent Service in Foundry → Azure OpenAI.
* The agent orchestrates grounding (RAG), data store calls, and tools.
* Designed for simple enterprise chat, but already includes:
    * Foundry Agent Service as the orchestrator.
    * Connection to Azure AI Search, Cosmos DB, SQL, etc. for grounding.

#### 2. RAG Solution Design and Evaluation Guide

* Formal RAG Reference Architecture:
    * Client Application → API/Backend → Orchestrator/Prompt Flow → Azure AI Search (vector/semantic index) + storage (Blob, Data Lake) → Azure OpenAI for generation.
* Includes considerations for: chunking, evaluation, human feedback, automated evaluation, etc.

#### 3. RAG Tutorial with Azure OpenAI + Azure AI Search (.NET + Blazor)

* Concrete diagram: Blazor App → Azure App Service → Azure AI Search + Azure OpenAI.
* Shows the complete chat flow with grounding, citing sources.

#### 4. Azure OpenAI Architecture Patterns & Landing Zones

* Patrones típicos:
    * AOAI + Front Door / App Gateway / APIM.
    * Multi-region, failover, seguridad con Private Link, RBAC, Key Vault.
* [Repo de landing zone con arquitecturas enterprise, Bicep/Terraform y diagramas.](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/azure-openai-architecture-patterns-and-implementation-steps/3979934?utm_source=chatgpt.com)


**Useful URLs (with diagrams)**

[Azure – Basic AI Foundry Chat Reference Architecture](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/basic-azure-ai-foundry-chat)  
[Azure – Baseline AI Foundry Chat Reference Architecture](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-azure-ai-foundry-chat)  
[Azure – RAG Solution Design and Evaluation Guide](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide)  
[Azure – RAG app with Azure OpenAI + Azure AI Search (.NET tutorial)](https://learn.microsoft.com/en-us/azure/app-service/tutorial-ai-openai-search-dotnet)  
[Azure – Azure OpenAI architecture patterns (TechCommunity)](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/azure-openai-architecture-patterns-and-implementation-steps/3979934)  
[Azure – Azure OpenAI Landing Zone reference architectures (GitHub)](https://github.com/Azure/azure-openai-landing-zone)

## 2. AWS – Amazon Bedrock + GenAI Reference Architectures  
- **Page**: “AWS Reference Architecture Diagrams”  
  URL: https://aws.amazon.com/architecture/reference-architecture-diagrams/
- **Description**: A library of diagrams built by AWS that cover generative AI, machine learning, data lakes, and agent-based workloads. While not always specific to LLMs, they serve as high-level reference for AI/ML architecture on AWS.

### 2.1. Official Bedrock Architectures

#### 1. Amazon Bedrock – Generative AI Application Architecture (RAG)

* Typical architecture:
    * Client → API Gateway → Lambda/backend → Amazon Bedrock (models)
    * Bedrock Knowledge Bases (Managed RAG) + S3 / OpenSearch / Aurora
    * Observability with CloudWatch / X-Ray.

#### 2. AI Gateway to Amazon Bedrock con API Gateway

* AI Gateway Pattern:
    * API Gateway as a unified entry point.
    * Lambda/Step Functions for routing and policies.
    * Bedrock as a model layer (Claude, Llama, Titan, etc.).
    * Thin-grained access policies per user/application.

#### 3. Amazon Bedrock Architectures Repository

* Collection of architectures for various GenAI use cases:
    * Q&A with RAG.
    * Document analysis.
    * Agents, tools, pipelines.
* Includes diagrams and templates (CloudFormation, CDK)

#### 2.2. Typical LLM Architecture on AWS

The most common diagrams share the following characteristics:

* Front-end: Amplify, SPA in S3 + CloudFront, App Runner, etc.
* API / Orchestration:
    * Amazon API Gateway + Lambda
    * Or back-end in ECS/EKS/Fargate

Model:

* Amazon Bedrock (Claude, Llama, Titan…)

RAG:

* Bedrock Knowledge Bases
* S3 + Amazon OpenSearch Service / Aurora / DynamoDB

Governance & Security:

* IAM, KMS, CloudTrail, WAF, GuardDuty

#### 2.3. URLs with diagrams

[AWS – Amazon Bedrock main (overview + diagrams)](https://aws.amazon.com/bedrock/)  
[AWS – Bedrock Generative AI Application Architecture (RAG)](https://builder.aws.com/content/2f2d59922DQNz3iH1pCTeudpmhv/aws-bedrock-generative-ai-application-architecture)  
[AWS – AI gateway to Amazon Bedrock with API Gateway](https://aws.amazon.com/blogs/architecture/building-an-ai-gateway-to-amazon-bedrock-with-amazon-api-gateway/)  
[AWS – Bedrock Architectures (GitHub: diagrams + templates)](https://github.com/aws-samples/amazon-bedrock-architectures)

## 3. Google Cloud – Vertex AI / Gemini GenAI 
- **Page**: “AI and machine learning resources | Cloud Architecture Center”  
  URL: https://cloud.google.com/architecture/ai-ml  
- **Description**: Offers generative AI, agentic AI, RAG, ML Ops reference architectures. Includes design guides and reference diagrams on deploying AI/ML workloads at enterprise scale on Google Cloud.

### 3.1. Key Official Architectures

#### 1. Reference architecture for RAG apps in GKE + Cloud SQL

* Diagram of a GenAI app with RAG:
    * Front-end → API / back-end in GKE
    * RAG using LangChain / Ray and vector store
    * Database in Cloud SQL
    * Models in Vertex AI Generative AI / Gemini.

#### 2. Architecting GenAI applications with Google Cloud (blog)

* Typical GenAI app diagram:
    * How to choose a model (Gemini vs. others).
    * Customization (prompting, RAG, fine-tuning).
    * Evaluation and deployment.

#### 3. Generative AI on Vertex AI overview

* Describe how it's orchestrated:
    * Vertex AI (Gemini, other models) + Model Garden.
    * Integration with BigQuery, Cloud Storage, Dataform, etc.

### 3.2. Typical Architecture in GCP

In the diagrams, you'll see something like this:

* Front-end: Cloud Run (frontend), Firebase Hosting, App Engine, etc.
* Backend/Orchestrator:
    * Cloud Run/GKE/Cloud Functions
    * Code that handles RAGs, prompting, and policies.

* Models:
    * Vertex AI, Generative AI (Gemini Pro/Flash/2.5/etc.)

* RAGs:
    * Vector store (sometimes in Postgres/Cloud SQL + pgvector, AlloyDB, Bigtable, or OSS tools)
    * Data in Cloud Storage/BigQuery

* Ops and Security:
    * IAM, VPC-SC, Cloud Armor, Cloud Logging, Cloud Trace.

### 3.3. URLs with Diagrams

[Google Cloud – Generative AI overview](https://cloud.google.com/ai/generative-ai)  
[Google Cloud – Vertex AI platform](https://cloud.google.com/vertex-ai)  
[Google Cloud – RAG-capable Generative AI app (GKE + Cloud SQL + LangChain)](https://cloud.google.com/docs/generative-ai#infrastructure-for-a-rag-capable-generative-ai-application-using-gke-and-cloud-sql)  
[Google Cloud – Architecting GenAI applications with Google Cloud (diagramas en el post)](https://medium.com/google-cloud/architecting-genai-applications-with-google-cloud-b38c9cbc66e0)

---