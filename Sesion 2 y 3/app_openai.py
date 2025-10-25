import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

class Query(BaseModel):
    q: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Query):
    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": q.q}]
    )
    return {"answer": resp.choices[0].message.content}