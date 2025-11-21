The most important design patterns for building applications with LLMs, organized into modern categories with deep technical explanations, as they are used today in enterprise systems, RAG pipelines, agents, and advanced AI workloads (Azure OpenAI, AWS Bedrock, GCP Vertex, NVIDIA NIMs, etc.)

# LLM (Large Language Models) Design Patterns
A complete technical guide for architects, AI engineers, and MLOps practitioners.

## 🧱 1. Fundamental Interaction Patterns (Prompting / Chain-of-Thought / Context Management)
### 1.1 Prompt Engineering Pattern (Prompt Engineering + Few-Shot + System Prompts)

**Technical Description**

Prompt Engineering defines the behavioral contract between your application and the LLM. A well-designed prompt controls:

* Role conditioning (system prompts)
* Expected format (JSON, YAML, bullet steps, compliance tables)
* Reasoning strategy (CoT, few-shot, constraints)
* Safety boundaries (don’t invent, follow source citations)

Prompt engineering defines the structure, constraints, and behavior the LLM must follow. It acts as an interface contract between human-written logic and the generative model. Use of structured templates, roles, constraints, and context to guide the model’s output. It transforms the LLM from a “general generator” into a deterministic component within a larger architecture.

Key components:

* System instructions
    * Define purpose, constraints, tone, regulatory rules.
    * Essential in enterprise and safety-critical systems.
* Few-shot examples
    * The LLM imitates patterns and structure from the examples.
* Explicit instruction-following
    * “Respond in JSON schema X.”
    * “Provide 3 recommendations ranked by risk.”
* Constraints and policies:
    * Prevent hallucinations: **_“If insufficient data, say ‘NO DATA FOUND’.”_**

Examples:

* Few-shot prompting
* Chain-of-Thought (CoT)
* Self-Consistency
* Instruction-following

**Idea: the LLM behaves like an “interpreter” conditioned by:**

* System prompt (policies, role, style).
* In-context examples (few-shot).
* Explicit instructions (JSON format, numbered steps, etc.).

When to Use

* Regulated environments (oil & gas, healthcare)
* Enterprise chatbots
* JSON/YAML formatted outputs
* Legal/contract summarizers
* Medical triage (with human validation)
* Copilot-style enterprise assistants
* Chatbots with strict API outputs

Important details:

* It becomes an interface contract between your application and the model.
* It must be version-controlled (Git) and treated as code.
* You normally combine it with other patterns (RAG, ReAct, agents).

Verifiable real-world cases:

**_Azure, Google, OpenAI, Anthropic, etc., document the use of system instructions and example-based prompting to control behavior (e.g., Gemini / Vertex AI “system instructions”)._** 

References:  
[Google Cloud Documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini?utm_source=chatgpt.com)  
[Azure OpenAI System Messages](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/advanced-prompt-engineering?view=foundry-classic)  
[OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering)  
[Google Gemini System Instructions](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions)

---

### 1.2 Retrievers Pattern (RAG)

**Technical Description**

The retriever augments the LLM with external knowledge, creating a hybrid intelligence model (reasoning + memory store). The LLM retrieves external context through a retriever (vector store, hybrid, multimodal). It enables grounded, citation-based answers.

Includes:

* Dense retrieval (FAISS, Milvus, Pinecone)
    * Embeddings → ANN search (FAISS, Pinecone, Milvus).
    * Best for semantic similarity.
* Hybrid retrieval (BM25 + embeddings)
    * Combines BM25 + embeddings.
    * Reduces false positives from pure vector search.
* Multimodal retrieval (text + images)
    * Vector retrieval over images, PDFs, video frames, or audio.
    * Crucial in manufacturing, oil & gas, maintenance.

Why It Matters:

* Provides factual grounding
* Reduces hallucinations dramatically
* Enables enterprise data governance
* Most production LLM systems rely on it

**Idea: induce the model to “think in steps” and then provide the final answer.**
Variants:

* Simple CoT: “reason step by step.”
* Self-consistency: generate multiple reasoning chains and select the most consistent.

Advantages:

* Improves performance in mathematical and logical reasoning tasks.
* Increases explainability (you may show the reasoning to the user when appropriate).

Limitations:

* Increases tokens → more cost and latency.
* If the model reasons poorly, it will explain poorly (not a guarantee of correctness).

Typical use: for complex prompts in:

* Planning agents.
* Advanced QA for consulting, legal, medical domains (with human oversight), over policies, SOPs, manuals
* Safety compliance systems (HSE)
* Legal search
* Internal knowledge copilots

Real-World References:  
[Azure AI Search RAG](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview?tabs=docs)  
[AWS Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)  
[Google Vertex AI Search](https://docs.cloud.google.com/generative-ai-app-builder/docs/introduction)

---

### 1.3 Context Window Management Pattern

**Technical Description:**  

Since LLMs have limited context windows, this pattern optimizes what enters the prompt. Effective management ensures relevance and performance.:

* Semantic chunking
* Sliding windows
* Hierarchical summarization
* Reranking

Techniques to properly manage the model's limited context window:

* Semantic Chunking (by logical sections, not raw character counts): Split based on meaning (sections, headings, tables), not raw tokens.
* Intelligent chunking
* Summarization-on-the-fly: Multi-level summaries (recap → section → document). Hierarchical summaries for long history contexts
* Sliding-window: Maintain conversational state while discarding non-essential history.
* Pre-prompt re-ranking
* Reranking Before Prompting: Sort retrieved chunks using a cross-encoder or ReRank model.

**Idea: since context is finite, you need strategies:**

Use Cases

* Long chats
* Large document analysis
* Compliance pipelines that require historical reasoning
* Customer support copilots

Real-world cases:

**_Frameworks like LangChain / LlamaIndex / LangGraph already include chunking + re-ranking + summarization patterns specifically built for RAG._**

References:  
[LangChain Docs](https://docs.langchain.com/oss/python/langgraph/workflows-agents?utm_source=chatgpt.com)  
[LlamaIndex Context Management](https://developers.llamaindex.ai/python/framework/)
[LangChain Retrievel Architure](https://docs.langchain.com/oss/python/langchain/overview)

## 🧠 2. Reasoning Patterns
### 2.1 Chain-of-Thought Pattern

**Technical Description**  

CoT instructs the model to reason step-by-step before giving the final answer.

Improves:

* Mathematical reasoning
* Complex decisions
* Explainability

Benefits:

* Improved accuracy in math, logic, and planning
* Transparent reasoning
* Better for audit/compliance environments (HSE, finance, medical)

Risks:

* Higher token usage
* Reveals internal thinking (must be redacted in some contexts)

Use Cases

* Diagnostic pipelines
* Root cause analysis
* Planning systems
* Code generation

References:  
[Paper: Chain-of-Thought Reasoning](https://arxiv.org/abs/2201.11903)

---

### 2.2 Tree-of-Thoughts Pattern

**Technical Description**  

Instead of a single chain of reasoning, the LLM explores multiple reasoning branches, evaluates them, and selects the best one.

Use Cases:

* Complex problem solving
* Plan optimization
* Complex engineering problems
* Scheduling and optimization
* Strategy planning
* Multi-stage decision systems

References:  
[ToT Paper](https://arxiv.org/abs/2305.10601)

---

### 2.3 Graph-of-Thoughts Pattern

**Technical Description**  

Reasoning modeled as a collaborative graph:

* Nodes = partial ideas
* Edges = relationships
* The system merges nodes into a high-precision final answer

Use Cases

* Multidisciplinary diagnostics
* HSE incident analysis
* Enterprise workflow reasoning
* Multi-document synthesis
* Better for tasks with multiple dependencies
* Ideal for diagnostics, workflows, and pipelines

References:  
[Graph of Thoughts: Solving Elaborate Problems with Large Language Models](https://arxiv.org/abs/2308.09687)  
[GoT: Unleashing Reasoning Capability of Multimodal Large Language Model for Visual Generation and Editing](https://arxiv.org/abs/2503.10639)  

## ⚙️ 3. Orchestration and Execution Patterns
### 3.1 ReAct Pattern (Reasoning + Acting)

**Technical Description**

Combines internal reasoning + external tool use.

ReAct alternates between:

* Thought (LLM internal reasoning)
* Action (tool/function call)
* Observation (tool result)

This creates an agentic loop.

Used By

* Azure AI Foundry Agents
* AWS Bedrock Agents
* OpenAI GPT-o Agents
* LangChain Agents

Example:

**_LLM thinks → calls tools → merges results._**

References:  
[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)

---

### 3.2 Tool-Use Pattern

**Technical Description**  

The LLM acts as an orchestrator making external tool calls::

* REST APIs
* Databases (SQL, NoSQL)
* Calculation/simulators tools
* Specialized models
    * Vision/ML models (CV, OCR)
    * IoT/SCADA systems

Use Cases

* Enterprise copilots
* Data pipeline orchestration
* Field engineering assistants
* Safety systems in industrial plants

References:  
[Anthropic MCP](https://www.anthropic.com/news/model-context-protocol)  
[What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/getting-started/intro)  
[GCP - What is the MCP and how does it work?](https://cloud.google.com/discover/what-is-model-context-protocol?hl=en)  
[Microsoft - Introducing Model Context Protocol (MCP) in Copilot Studio: Simplified Integration with AI Apps and Agents](https://www.microsoft.com/en-us/microsoft-copilot/blog/copilot-studio/introducing-model-context-protocol-mcp-in-copilot-studio-simplified-integration-with-ai-apps-and-agents/)  
[AWS - Unlocking the power of Model Context Protocol (MCP)](https://aws.amazon.com/blogs/machine-learning/unlocking-the-power-of-model-context-protocol-mcp-on-aws/)

### 3.3 Function Calling Pattern
**Technical Description**  

The LLM outputs structured JSON payloads that map directly to backend functions.

Critical pattern for:

* Enterprise chatbots
* Transactional systems
* AI-driven RPA
* Transactional workloads
* RPA + LLM
* ERP/CRM automation
* Conversational actions (create-ticket, schedule-task)

### 3.4 Program-Aided Language Models (PAL) Pattern

The LLM generates executable code (Python, SQL, etc.).
Useful for:

* Complex mathematics
* SQL queries
* Structured processing

## 📚 4. Retrieval and Context Enrichment Patterns (Advanced RAG)
### 4.1 Basic RAG Pattern

**_Query → Retrieval → Augment → Prompt → Output._**

Classic pipeline:

* User asks a question.
* Perform retrieval on a vector store (or hybrid) using embeddings.
* Select top-k chunks.
* Build a prompt with question + context.
* LLM generates a grounded answer.

The Lewis et al. (2020) paper formalized this pattern. [arXiv](https://arxiv.org/abs/2005.11401?utm_source=chatgpt.com)  
NVIDIA promotes it as the standard pattern for reducing hallucinations and enabling citation. [NVIDIA Blog](https://blogs.nvidia.com/blog/what-is-retrieval-augmented-generation/?utm_source=chatgpt.com)

Real-world cases:

* Copilot / ChatGPT Enterprise / Gemini + private data → all expose RAG under the hood for SharePoint, Drive, Confluence, etc. [Wikipedia](https://en.wikipedia.org/wiki/Retrieval-augmented_generation?utm_source=chatgpt.com)  
* Amazon Bedrock Knowledge Bases, Azure AI Search + Azure OpenAI, Vertex AI Search + Gemini, etc. [Medium](https://john-tucker.medium.com/amazon-bedrock-knowledge-bases-by-example-8686109ac5b1?utm_source=chatgpt.com)

Where it shines:

* Corporate portals, internal policy Q&A, technical manuals, SOPs, etc.

---

### 4.2 Structured / Hierarchical RAG Pattern

Hierarchical retrieval:

**_Titles → Subtitles → Paragraphs_**
Improves accuracy and reduces noise.

Variations:

* Hierarchical indexes (document → section → paragraph).
* RAG over tables and charts (parsed into structured elements).
* RAG + knowledge graph (RAG-KG).

**Advantage:** less noise, better grounding when documents are large.

---

### 4.3 Multi-Step RAG Pattern

**Idea:**

* The LLM first reformulates the query → “retrieval-prompting.”
* It performs multiple retrieval and re-ranking rounds.

Heavily used in **Agentic RAG** (planner + retriever). [Wikipedia](https://en.wikipedia.org/wiki/Retrieval-augmented_generation?utm_source=chatgpt.com)

The LLM performs iterative search cycles:

* Understands intent
* Rewrites the question
* Retrieves better
* Answers
* Validates

### 4.4 Query Rewriting Pattern

Before retrieval, the LLM optimizes the query:

* More precise
* Less ambiguous
* Better for embeddings

4.5 Reranking Pattern

**_Reduces “RAG noise.”_**
Models re-rank the most relevant chunks before prompting.

## 🧩 5. Personalization and Adaptation Patterns
### 5.1 Fine-Tuning Pattern

Supervised training of the model for highly specific use cases.
Examples:

* Legal models
* Medical
* Financial

### 5.2 LoRA / QLoRA Adaptation Pattern

Lightweight model adaptation via adapters.
Ideal for:

* Low cost
* Edge devices (Jetson)
* Private enterprise models

### 5.3 Prompt Personalization Pattern

Personalization based on:

* User profile
* Interaction history
* Business rules

## 🛡️ 6. Security and Governance Patterns
### 6.1 Guardrails Pattern

Pre- and post-filters:

* Guidelines
* Moderation
* Safety
* PII detection

### 6.2 Policy Enforcement Pattern

Application of corporate rules inside the pipeline:

* Do not fabricate data
* Do not generate sensitive content
* Do not execute functions without human validation

### 6.3 Self-Verification Pattern

The LLM verifies its own output:

* “Double LLM check”
* Self-evaluation
* Secondary verification models

## 🏗️ 7. Full System Patterns
### 7.1 Multi-Agent Pattern

Multiple LLMs with specialized roles:

* Planner
* Solver
* Critic
* Coder
* Retriever

Used in:

* OpenAI Agents
* AutoGPT
* Microsoft AutoGen

### 7.2 Supervisor-Agent Pattern

One LLM supervises other agents:

** Validates responses
* Manages roles
* Coordinates tasks

### 7.3 Orchestrator-Worker Pattern

Heavily used in enterprises:

* Orchestrator LLM interprets the task
* Worker LLMs/tools execute subtasks

### 7.4 Grounded Generation Pattern

Every generated statement must be supported by:

* A source
* A chunk
* An ID
* A reference

## 📊 8. Optimization and Cost Patterns
### 8.1 Caching Pattern

Caching of:

* Prompts
* Embeddings
* Responses
* Reduces cost by 30%–80%.

### 8.2 Dynamic Model Selection Pattern

Depending on the task:

* Small models → simple questions
* Large models → complex reasoning
* Specialized models → domain expertise

### 8.3 Distillation Pattern

Compress a large model into a more efficient one while preserving performance.