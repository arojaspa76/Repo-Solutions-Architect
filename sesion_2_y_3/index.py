import glob, os, requests, chromadb, tiktoken

PERSIST_DIR = os.path.join("data", ".chroma")
os.makedirs(PERSIST_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=PERSIST_DIR)


def chunk_text(text: str, chunk_size_tokens=400, chunk_overlap_tokens=60, encoding_name="cl100k_base"):
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    print (f"Tokens: {tokens}")
    
    chunks, i = [], 0
    step = max(1, chunk_size_tokens - chunk_overlap_tokens)
    while i < len(tokens):
        window = tokens[i:i+chunk_size_tokens]
        chunks.append(enc.decode(window))
        i += step
    return chunks

def embed(text: str):
    # Requiere: ollama pull nomic-embed-text
    r = requests.post("http://localhost:11434/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    r.raise_for_status()
    return r.json()["embedding"]

def main():
    chroma = chromadb.Client()
    coll = chroma.get_or_create_collection("docs")
    files = glob.glob("./data/*.txt")
    if not files:
        print("No se encontraron archivos en ./data/. Agrega .txt")
    for path in files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        parts = chunk_text(content, 400, 60)
        batch_docs, batch_embs, batch_ids = [], [], []
        for idx, part in enumerate(parts):
            vec = embed(part)
            batch_docs.append(part)
            batch_embs.append(vec)
            batch_ids.append(f"{os.path.basename(path)}#{idx:04d}")
        if batch_docs:
            coll.add(
                documents=batch_docs,
                embeddings=batch_embs,
                ids=batch_ids,
                metadatas=[{"file": os.path.basename(path)}]*len(batch_docs)
            )
            print(f"Indexado {len(batch_docs)} chunks de {os.path.basename(path)}")
    print("Indexado OK (con chunking).")

if __name__ == "__main__":
    main()