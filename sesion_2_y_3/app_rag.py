import os
from fastapi import FastAPI
from pydantic import BaseModel
import requests, chromadb
import logging

PERSIST_DIR = os.path.join("data", ".chroma")
os.makedirs(PERSIST_DIR, exist_ok=True)
app = FastAPI(title="RAG API", description="API de ejemplo para RAG con FastAPI y ChromaDB", version="1.0.0")
chroma = chromadb.PersistentClient(path=PERSIST_DIR)
coll = chroma.get_or_create_collection("docs")
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
    #logger.info("collection_count=%s", coll.count())
    qvec = embed(q.q)
    #logger.info("qvec=%s \n",qvec)

    hits = coll.query(query_embeddings=[qvec], n_results=5)
    #logger.info("hits=%s \n",hits)
    
    docs = hits.get("documents") or [[]]
    #logger.info("docs=%s \n",docs)
    
    first_docs = docs[0] if docs and isinstance(docs[0], list) else []
    #logger.info("first_docs=%s \n",first_docs)

    context = "\n".join(d for d in first_docs if isinstance(d, str))
    prompt = f"Usa el contexto para responder con precisión:\n{context}\n\nPregunta: {q.q}"
    #logger.info("Prompt=%s \n",prompt)

    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    })
    r.encoding="utf-8"
    r.raise_for_status()
    payload = r.json()
    answer = payload.get("response", "(sin respuesta)")
    logger.debug("Respuesta=%s \n", answer)
    return {"answer": answer}
