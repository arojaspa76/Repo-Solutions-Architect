# Multi-stack code examples for a specific pattern
Centralized in the RAG + ReAct + Tool Calling pattern (the one most used today in enterprise) and give you skeletons in several stacks.

## 1. Generic Python (simple RAG orchestrator + tool)
```python
from typing import List, Dict
from my_vector_store import search_embeddings
from my_llm_client import call_llm  # wrapper sobre Azure/OpenAI/Bedrock/etc.

def retrieve_context(query: str, k: int = 5) -> List[Dict]:
    return search_embeddings(query=query, top_k=k)

def build_prompt(query: str, docs: List[Dict]) -> str:
    context = "\n\n".join(d["content"] for d in docs)
    return f"""You are an enterprise assistant.

Use ONLY the context below to answer.

Context:
{context}

Question: {query}

If the answer is not in the context, say you don't know and suggest who could help."""
    
def answer_question(query: str) -> str:
    docs = retrieve_context(query)
    prompt = build_prompt(query, docs)
    response = call_llm(prompt)
    return response

if __name__ == "__main__":
    print(answer_question("¿Cómo restauro un backup en el clúster SQL del AMVA?"))

```
That call_llm can use Azure, Bedrock, Vertex, or NIMs depending on your deployment.

## 2. Node.js/TypeScript with AWS Bedrock Runtime (Simple RAG)

```ts
import { BedrockRuntimeClient, InvokeModelCommand } from "@aws-sdk/client-bedrock-runtime";
import { searchEmbeddings } from "./vectorStore"; // tu implementación

const client = new BedrockRuntimeClient({ region: "us-east-1" });
const modelId = "anthropic.claude-3-haiku-20240307-v1:0"; // ejemplo

async function ragQuery(userQuery: string) {
  const docs = await searchEmbeddings(userQuery, 5);
  const context = docs.map(d => d.content).join("\n\n");

  const prompt = `
You are an internal assistant. Answer ONLY from the context.

Context:
${context}

Question: ${userQuery}
`;

  const command = new InvokeModelCommand({
    modelId,
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      messages: [{ role: "user", content: [{ type: "text", text: prompt }] }]
    })
  });

  const response = await client.send(command);
  const body = JSON.parse(new TextDecoder().decode(response.body));
  console.log(body);
}

ragQuery("Explain AMVA SharePoint cluster topology");

```

## 3. Azure OpenAI with Function Calling (ReAct + tool)
```python
from openai import OpenAI
import json, os

client = OpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_KEY"]
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Busca en el knowledge base corporativo",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            },
        },
    }
]

def search_kb(query: str, top_k: int = 5):
    # Aquí llamas Azure AI Search / vector DB
    return [{"title": "Doc1", "content": "..."}, ...]

def chat_with_tools(user_query: str):
    response = client.responses.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        input=user_query,
        tools=tools
    )

    tool_calls = response.output[0].content[0].tool_calls if hasattr(response.output[0].content[0], "tool_calls") else []
    if tool_calls:
        for tc in tool_calls:
            if tc.function.name == "search_kb":
                args = json.loads(tc.function.arguments)
                docs = search_kb(**args)
                tool_result = json.dumps(docs)
                followup = client.responses.create(
                    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                    input=[
                        {"role": "user", "content": user_query},
                        {
                            "role": "tool",
                            "name": "search_kb",
                            "content": tool_result
                        }
                    ]
                )
                return followup.output[0].content[0].text
    else:
        return response.output[0].content[0].text
```

## 4. AWS Bedrock Agents + Knowledge Base (high level)

In Bedrock, you define the Agent and the Knowledge Base in the console. Your Python code only invokes the agent:

```python
import boto3, os

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
agent_id = os.environ["BEDROCK_AGENT_ID"]
agent_alias_id = os.environ["BEDROCK_AGENT_ALIAS_ID"]

def ask_agent(question: str):
    resp = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId="andres-session-1",
        inputText=question,
    )
    # streaming; aquí simplificado
    chunks = []
    for event in resp["completion"]:
        if "chunk" in event:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
    return "".join(chunks)

print(ask_agent("Resume la arquitectura del clúster de SharePoint 2019 que diseñamos"))

```

The agent already handles RAG + tools + orchestration.

## GCP Vertex AI/Gemini (Python SDK)

```python
from vertexai.generative_models import GenerativeModel
import vertexai

vertexai.init(project="TU_PROYECTO", location="us-central1")

model = GenerativeModel("gemini-2.0-flash-exp")

def rag_with_vertex(user_query: str, context: str) -> str:
    prompt = f"""
Responde usando SOLO el siguiente contexto:

{context}

Pregunta: {user_query}
"""
    resp = model.generate_content(prompt)
    return resp.text

# El contexto podría venir de Vertex AI Search o tu vector store

```

## 6. NVIDIA NIMs + Triton + Jetson (Python client)

Suppose you have a NIM LLM (with TensorRT-LLM + Triton) deployed in a container accessible from your Jetson Orin:

```python
import requests
import json

NIM_ENDPOINT = "http://jetson-orin:8000/v1/chat/completions"
API_KEY = "tu-token-si-aplica"

def call_local_llm(prompt: str) -> str:
    payload = {
        "model": "nim-llama-3-8b-instruct",  # ejemplo
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    resp = requests.post(NIM_ENDPOINT, headers=headers, data=json.dumps(payload))
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

print(call_local_llm("Resume la topología de red de esta planta industrial en 3 puntos."))

```
That same pattern integrates with your DeepStream/TensorRT pipeline for vision, using the LLM only as a reasoning/explanation/reporting layer.
