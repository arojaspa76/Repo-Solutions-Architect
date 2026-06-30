import os
import logging
from typing import List

import requests
import chromadb
from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

# ----------------------------
# Configuración (env overrides)
# ----------------------------
OLLAMA_URL_GENERATE = os.getenv("OLLAMA_URL_GENERATE", "http://localhost:11434/api/generate")
OLLAMA_URL_EMBED    = os.getenv("OLLAMA_URL_EMBED",    "http://localhost:11434/api/embeddings")
EMBED_MODEL         = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL           = os.getenv("GEN_MODEL",   "llama3")
TOP_K               = int(os.getenv("TOP_K", "3"))
REQ_TIMEOUT         = float(os.getenv("REQ_TIMEOUT", "180"))
PERSIST_DIR         = os.getenv("CHROMA_DIR", os.path.join("data", ".chroma"))

# ----------------------------
# Logging
# ----------------------------
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

# ----------------------------
# Chroma persistente (data/.chroma)
# ----------------------------
os.makedirs(PERSIST_DIR, exist_ok=True)
client = chromadb.PersistentClient(path=PERSIST_DIR)
coll = client.get_or_create_collection("docs")

# ----------------------------
# FastAPI
# ----------------------------
app = FastAPI(default_response_class=ORJSONResponse)

class Query(BaseModel):
    q: str

def embed(text: str) -> List[float]:
    """Obtiene embedding desde Ollama (modelo de embeddings)."""
    try:
        r = requests.post(
            OLLAMA_URL_EMBED,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=REQ_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception as e:
        logger.exception("Error en embeddings: %s", e)
        raise HTTPException(status_code=502, detail=f"Embedding error: {e}")

def generate(prompt: str) -> str:
    """Genera respuesta con el LLM de Ollama (no streaming)."""
    try:
        r = requests.post(
            OLLAMA_URL_GENERATE,
            json={"model": GEN_MODEL, "prompt": prompt, "stream": False},
            timeout=REQ_TIMEOUT,
        )
        #r.encoding = "utf-8"
        r.raise_for_status()
        return r.json().get("response", "(sin respuesta)")
    except Exception as e:
        logger.exception("Error en generación: %s", e)
        raise HTTPException(status_code=502, detail=f"Generate error: {e}")

@app.get("/health")
def health():
    """Estado + métricas simples del índice."""
    try:
        count = coll.count()
    except Exception:
        count = None
    return {
        "status": "ok",
        "docs_count": count,
        "persist_dir": os.path.abspath(PERSIST_DIR),
        "gen_model": GEN_MODEL,
        "embed_model": EMBED_MODEL,
        "top_k": TOP_K,
    }

@app.post("/chat")
def chat(q: Query):
    # 1) Embedding de la consulta
    qvec = embed(q.q)

    # 2) Recuperación en Chroma
    hits = coll.query(query_embeddings=[qvec], n_results=TOP_K)
    docs = hits.get("documents", [[]])[0] if hits else []
    metas = hits.get("metadatas", [[]])[0] if hits else []

    # Asegura contexto (evita None)
    context = "\n".join(docs or [])

    # 3) Prompt con contexto
    prompt = (
        "Responde de forma concisa y precisa usando SOLO el contexto. "
        "Si no hay información suficiente en el contexto, dilo explícitamente.\n\n"
        f"Contexto:\n{context}\n\nPregunta: {q.q}\nRespuesta:"
    )
    logger.info("Prompt:\n%s\n", prompt)

    # 4) Generación
    answer = generate(prompt)
    print(f"\033[32mRespuesta Generada: \033[33m{answer}\033[0m \n")
    return {"answer": answer, "sources": metas}
