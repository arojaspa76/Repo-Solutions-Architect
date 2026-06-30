# 🦙 Guía Completa de Ollama — LLMs Locales
## Sesión 3 | BSG Institute

> **¿Qué es Ollama?**  
> Ollama es una herramienta open-source que permite ejecutar LLMs directamente en tu computadora, sin conexión a internet ni API keys. Perfecta para aprender y desarrollar sin costos.

---

## 📥 Instalación

### Linux / WSL2
```bash
curl -fsSL https://ollama.ai/install.sh | sh

# Verificar instalación
ollama --version
```

### macOS
```bash
# Con Homebrew
brew install ollama

# O descargar desde https://ollama.ai/download
```

### Windows (nativo)
1. Descargar el instalador desde: https://ollama.ai/download
2. Ejecutar `OllamaSetup.exe`
3. Ollama corre como servicio en background

### Iniciar el servidor manualmente
```bash
ollama serve
# Output esperado:
# time=... level=INFO source=server.go msg="Listening on 127.0.0.1:11434"
```

---

## 🤖 Modelos Disponibles

### Recomendados para clase (ordenados por RAM requerida)

| Modelo | RAM | Uso recomendado |
|--------|-----|-----------------|
| `phi3:mini` | ~2 GB | Preguntas simples, muy rápido |
| `llama3.2:3b` | ~2 GB | **RECOMENDADO para esta sesión** |
| `mistral:7b` | ~4 GB | Mejor calidad, equilibrado |
| `llama3.1:8b` | ~5 GB | Alta calidad en razonamiento |
| `codellama:7b` | ~4 GB | Especializado en código Python |
| `llama3.1:70b` | ~40 GB | Producción, requiere GPU |

### Descargar modelos
```bash
# Modelo recomendado para clase
ollama pull llama3.2:3b

# Ver todos los modelos disponibles
ollama list

# Información detallada de un modelo
ollama show llama3.2:3b
```

---

## 💬 Usar Ollama

### Desde la terminal (modo interactivo)
```bash
# Chat directo
ollama run llama3.2:3b

# Con prompt inicial
ollama run llama3.2:3b "¿Qué es Kubernetes en una oración?"

# Salir del chat interactivo
/bye
```

### Via API REST (sin Python)
```bash
# Chat básico
curl http://localhost:11434/api/generate \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "¿Qué es Docker?",
    "stream": false
  }'

# Chat con historial de conversación
curl http://localhost:11434/api/chat \
  -d '{
    "model": "llama3.2:3b",
    "messages": [
      {"role": "system", "content": "Eres un experto en cloud computing."},
      {"role": "user", "content": "¿Cuál es la diferencia entre AKS, GKE y EKS?"}
    ],
    "stream": false
  }'

# Embeddings
curl http://localhost:11434/api/embeddings \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Kubernetes orquesta contenedores Docker"
  }'

# Listar modelos
curl http://localhost:11434/api/tags

# Estado del servidor
curl http://localhost:11434/
```

### Via Python
```python
import ollama

# Chat simple
response = ollama.chat(
    model='llama3.2:3b',
    messages=[
        {'role': 'user', 'content': '¿Qué es un pod en Kubernetes?'}
    ]
)
print(response['message']['content'])

# Chat con streaming
for chunk in ollama.chat(
    model='llama3.2:3b',
    messages=[{'role': 'user', 'content': '¿Qué es Docker?'}],
    stream=True,
):
    print(chunk['message']['content'], end='', flush=True)

# Embeddings
result = ollama.embeddings(
    model='llama3.2:3b',
    prompt='Kubernetes orquesta contenedores'
)
print(f"Dimensiones del vector: {len(result['embedding'])}")
```

---

## 🐳 Ollama en Docker

```bash
# Correr Ollama en contenedor (CPU)
docker run -d \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# Con GPU NVIDIA
docker run -d \
  --gpus=all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# Descargar modelo dentro del contenedor
docker exec -it ollama ollama pull llama3.2:3b
```

---

## ☸️ Ollama en Kubernetes

```yaml
# Simplificado — ver kubernetes/local/deployment.yaml para versión completa
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
          resources:
            limits:
              memory: "8Gi"
              cpu: "4000m"
```

---

## 🔧 Comandos Útiles

```bash
# Ver uso de recursos
ollama ps

# Eliminar un modelo
ollama rm llama3.2:3b

# Crear modelo personalizado con Modelfile
cat > Modelfile << 'EOF'
FROM llama3.2:3b
SYSTEM "Eres un experto en infraestructura cloud para LATAM. 
Responde siempre en español. Sé técnico pero claro."
PARAMETER temperature 0.3
PARAMETER num_predict 512
EOF

ollama create mi-experto-cloud -f Modelfile
ollama run mi-experto-cloud "¿Cómo elijo entre AKS y GKE para mi empresa?"

# Ver logs del servidor
journalctl -u ollama -f    # Linux con systemd
# En Windows: Event Viewer o logs en %USERPROFILE%/.ollama/logs/
```

---

## ⚡ Comparativa: Ollama vs Cloud APIs

| Criterio | Ollama (Local) | Azure OpenAI | AWS Bedrock | Vertex AI |
|----------|---------------|-------------|-------------|-----------|
| **Costo/petición** | $0.00 | $0.005-0.015/1K tokens | $0.003-0.015/1K | $0.00125-0.005/1K |
| **Setup inicial** | 5 min | 30 min + aprobación | 15 min | 20 min |
| **Calidad (GPT-4 = 10)** | 6-7/10 | 10/10 | 9/10 | 8/10 |
| **Latencia** | 1-10 seg | 0.5-3 seg | 0.5-3 seg | 0.5-2 seg |
| **Privacy** | 100% local | Azure enterprise | AWS enterprise | Google enterprise |
| **Offline** | ✅ Sí | ❌ No | ❌ No | ❌ No |
| **GPU requerida** | Recomendada | No (cloud) | No (cloud) | No (cloud) |
| **Ideal para** | Dev/Testing | Producción enterprise | Producción AWS | Producción GCP |

---

## 🎓 Ejercicio Práctico de Clase

```bash
# 1. Instalar Ollama y descargar modelo
ollama pull llama3.2:3b

# 2. Iniciar la API FastAPI
uvicorn app.main:app --reload

# 3. Probar el endpoint de chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explica en 3 puntos por qué Kubernetes es importante para LLMs",
    "model": "llama3.2:3b",
    "system_prompt": "Eres un instructor técnico de BSG Institute. Responde concisamente."
  }'

# 4. Ver la documentación interactiva
# Abrir en browser: http://localhost:8000/docs
```

---

**BSG Institute** | Sesión 3: Kubernetes, Docker y Contenedores para LLMs
