import glob, os, requests, chromadb, tiktoken

# --- PERSISTENCIA EN data/.chroma ---
PERSIST_DIR = os.path.join("data", ".chroma")
os.makedirs(PERSIST_DIR, exist_ok=True)
client = chromadb.PersistentClient(path=PERSIST_DIR)

# Fuerza a guardar la métrica de similitud: cosine
# Nota: si la colección ya existía con otra métrica, hay que elimínarla y se debe vuelver a indexar.
coll = client.get_or_create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"}  # "cosine" | "l2" | "ip"
)
# ------------------------------------

def chunk_text(text: str, chunk_size_tokens=400, chunk_overlap_tokens=60, encoding_name="cl100k_base"):
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    chunks, i = [], 0
    step = max(1, chunk_size_tokens - chunk_overlap_tokens)
    while i < len(tokens):
        window = tokens[i:i+chunk_size_tokens]
        chunks.append(enc.decode(window))
        i += step
    return chunks

def embed(text: str):
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    }, timeout=120)
    r.raise_for_status()
    return r.json()["embedding"]

def main():
    files = glob.glob("./data/*.txt")
    if not files:
        print("No se encontraron archivos en ./data/. Agrega .txt")
    for path in files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        parts = chunk_text(content, 400, 60)
        batch_docs, batch_embs, batch_ids, metas = [], [], [], []

        for idx, part in enumerate(parts):
            vec = embed(part)
            batch_docs.append(part)
            batch_embs.append(vec)
            batch_ids.append(f"{os.path.basename(path)}#{idx:04d}")
            metas.append({"file": os.path.basename(path), "chunk": idx})

        if batch_docs:
            coll.add(
                documents=batch_docs,
                embeddings=batch_embs,
                ids=batch_ids,
                metadatas=metas
            )
            print(f"Indexado {len(batch_docs)} chunks de {os.path.basename(path)}")

    print("Indexado OK (persistencia):", os.path.abspath(PERSIST_DIR))
    print("Total docs:", coll.count())

if __name__ == "__main__":
    main()
