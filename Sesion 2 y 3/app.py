from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class Query(BaseModel):
    q: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Query):
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": q.q,
        "stream": False
    })
    data = resp.json()
    return {"answer": data.get("response", "(sin respuesta)")}