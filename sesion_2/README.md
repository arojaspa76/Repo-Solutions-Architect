LLM Local — Guía rápida

1) Requisitos
- Python 3.11+, pip
- (Opción A) Ollama instalado y modelos:
  - ollama pull llama3
  - ollama pull nomic-embed-text
- (Opción B) OPENAI_API_KEY en .env si vas a usar OpenAI

2) API sin RAG (Ollama)
- pip install -r requirements.txt
- uvicorn app:app --host 0.0.0.0 --port 8080

3) API con RAG (Ollama + Chroma + chunking)
- pip install -r requirements_rag.txt
- python index.py
- uvicorn app_rag:app --host 0.0.0.0 --port 8080

4) API con OpenAI
- pip install -r requirements_openai.txt
- copy .env.example .env   # agrega tu clave
- uvicorn app_openai:app --host 0.0.0.0 --port 8080

5) Benchmark opcional
- pip install tiktoken requests statistics python-dotenv openai
- python benchmark.py

6) RAG con Scores en powershell de windows
- asegurarse que ollama esta en ejecucion
- ejecutar uvicorn app_rag_local_scores:app --host 0.0.0.0 --port 8080
- crear el json para enviar el request de la pregunta: $body = @{ q = "¿Donde agrego archivos para indexar?" } | ConvertTo-Json
- generar el request: `$r = Invoke-RestMethod -Uri "http://localhost:8080/chat" -Method POST -Body $body -ContentType 'application/json; charset=utf-8'`
- para ver la respuestas: `$r.answer`
- para ver los scores: `$r.sources`
