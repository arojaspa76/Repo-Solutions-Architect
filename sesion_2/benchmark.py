import time, statistics, requests, os
from typing import List
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

def count_tokens(text: str, enc_name="cl100k_base"):
    enc = tiktoken.get_encoding(enc_name)
    return len(enc.encode(text))

def bench_local_ollama(prompt: str, runs=5):
    latencies, toks = [], []
    for _ in range(runs):
        t0 = time.time()
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        })
        t1 = time.time()
        r.raise_for_status()
        resp = r.json().get("response","")
        lat = t1 - t0
        tok_out = count_tokens(resp)
        latencies.append(lat)
        toks.append(tok_out / lat if lat > 0 else 0)
    return latencies, toks

def bench_openai(prompt: str, runs=5):
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    latencies, toks = [], []
    for _ in range(runs):
        t0 = time.time()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )
        t1 = time.time()
        out = resp.choices[0].message.content
        lat = t1 - t0
        tok_out = count_tokens(out)
        latencies.append(lat)
        toks.append(tok_out / lat if lat > 0 else 0)
    return latencies, toks

def summarize(label: str, latencies: List[float], toksps: List[float]):
    print(f"=== {label} ===")
    print(f"runs={len(latencies)}")
    print("latency (s): min={:.3f} p50={:.3f} p95={:.3f} max={:.3f}".format(
        min(latencies), sorted(latencies)[len(latencies)//2],
        sorted(latencies)[int(0.95*len(latencies))-1], max(latencies)))
    print("tokens/s:    min={:.1f} p50={:.1f} p95={:.1f} max={:.1f}".format(
        min(toksps), sorted(toksps)[len(toksps)//2],
        sorted(toksps)[int(0.95*len(toksps))-1], max(toksps)))

if __name__ == "__main__":
    prompt = "Explica RAG en 3 puntos concisos."
    try:
        lat, tps = bench_local_ollama(prompt, runs=5)
        summarize("Ollama (llama3)", lat, tps)
    except Exception as e:
        print("Ollama bench error:", e)
    try:
        lat, tps = bench_openai(prompt, runs=5)
        summarize("OpenAI (gpt-4o-mini)", lat, tps)
    except Exception as e:
        print("OpenAI bench error:", e)