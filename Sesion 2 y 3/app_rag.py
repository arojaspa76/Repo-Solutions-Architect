from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
import requests, chromadb
import logging

app = FastAPI(default_response_class=ORJSONResponse)
coll = chromadb.Client().get_or_create_collection("docs")
logger = logging.getLogger("uvicorn.error")

class Query(BaseModel):
    q: str

def embed(text: str):
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    r.raise_for_status()
    return r.json()["embedding"]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Query):
    qvec = embed(q.q)
    hits = coll.query(query_embeddings=[qvec], n_results=5)
    context = "\n".join(hits.get("documents", [[""]])[0])
    prompt = f"Usa el contexto para responder con precisión:\n{context}\n\nPregunta: {q.q}"
    
    logger.info("Prompt=%s \n",prompt)

    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    })
    r.encoding="utf-8"
    r.raise_for_status()
    logger.debug("Respuesta=%s \n", r.json().get("response", "(sin respuesta)"))
    return {"answer": r.json().get("response", "(sin respuesta)")}