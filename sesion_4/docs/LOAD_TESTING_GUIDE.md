# 📖 Guía de Pruebas de Carga — LLM Gateway

## ¿Por qué probar la carga?

Las pruebas de carga responden preguntas críticas **antes** de ir a producción:
- ¿Cuántos usuarios concurrentes puede manejar mi sistema?
- ¿El HPA responde a tiempo cuando sube la carga?
- ¿El cache reduce significativamente la latencia?
- ¿Cuál es el cuello de botella: CPU, RAM, Ollama, red?
- ¿Cuánto tarda el sistema en recuperarse después de un pico?

## Tipos de Test y Cuándo Usar Cada Uno

```
Usuarios
   │
200│                    ╭─────╮         ← Stress Test
   │                  ╭╯     ╰╮
100│           ╭──────╯       ╰──╮      ← Load Test
   │         ╭╯                  ╰╮
 50│    ╭────╯                    ╰──   ← Smoke Test (5 VUs)
   │   ╭╯
  5│──╯
   └──────────────────────────────── tiempo
        1m  2m  4m  6m  8m  10m  12m
```

| Test | Usuarios | Duración | Objetivo |
|------|----------|----------|----------|
| **Smoke** | 5 | 1 min | ¿Funciona? Sin errores básicos |
| **Load** | 50-100 | 10 min | ¿Rinde bajo carga normal? |
| **Stress** | 200+ | 15 min | ¿Dónde está el límite? |
| **Spike** | 0→200→0 | 5 min | ¿Maneja picos súbitos? |
| **Soak** | 50 | 2-4 horas | ¿Hay memory leaks? |

## Instalación de k6

```bash
# macOS
brew install k6

# Linux (Ubuntu/Debian)
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
    | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Windows
choco install k6
# O descargar desde: https://k6.io/downloads

# Verificar
k6 version
```

## Ejecución de Tests

### 1. Smoke Test (siempre primero)

```bash
# Local
k6 run loadtesting/k6/smoke-test.js

# Contra endpoint en nube
k6 run -e BASE_URL=https://mi-api.azurewebsites.net loadtesting/k6/smoke-test.js
```

**Salida esperada:**
```
✓ ✅ Health: status 200
✓ ✅ Chat: status 200 o 503
✓ ✅ Chat: tiene respuesta

checks.........................: 100.00% ✓ 180  ✗ 0
http_req_duration..............: avg=1.2s  p(95)=1.8s
```

### 2. Load Test con monitoreo de HPA

```bash
# Terminal 1: Load test
k6 run loadtesting/k6/load-test.js

# Terminal 2: Monitorear HPA (en otra pantalla)
watch -n 3 "kubectl get hpa,pods -n llm-prod"

# Terminal 3: Métricas en tiempo real
watch -n 2 "curl -s localhost:8000/cache/stats | python -m json.tool"
```

### 3. Test con exportación de resultados

```bash
# Exportar a JSON para análisis posterior
k6 run --out json=loadtesting/results/load-$(date +%Y%m%d-%H%M).json \
    loadtesting/k6/load-test.js

# Analizar con el script de Python
python scripts/latency-analyzer.py --results loadtesting/results/
```

## Análisis de Resultados

### Métricas clave de k6

```
http_req_duration    — Latencia total (el más importante)
http_req_waiting     — Time To First Byte (TTFB)
http_req_receiving   — Tiempo de descarga del response
vus                  — Usuarios virtuales activos
http_reqs            — Total de requests completados
http_req_failed      — % de requests fallidos
iterations           — Iteraciones completadas
```

### Histograma de latencia — cómo interpretar

```
p(50) = 800ms   → La mitad de los usuarios esperan <800ms
p(90) = 2000ms  → 9 de cada 10 usuarios esperan <2 seg
p(95) = 5000ms  → 19 de cada 20 usuarios esperan <5 seg
p(99) = 15000ms → 99% de usuarios esperan <15 seg

El 1% restante (los más lentos) puede ser:
- Cache misses (primera llamada sin cache)
- Picos de CPU/RAM
- GC pauses
- Red saturada
```

### Benchmarks de referencia para LLMs

| Métrica | Excelente | Bueno | Aceptable | Problemático |
|---------|-----------|-------|-----------|-------------|
| **P95 latencia chat** | <1s | <3s | <10s | >10s |
| **P95 latencia salud** | <50ms | <200ms | <500ms | >500ms |
| **Error rate** | 0% | <1% | <5% | >5% |
| **Cache hit rate** | >80% | >60% | >40% | <40% |
| **RPS sostenido** | >100 | >50 | >20 | <20 |

### ¿Por qué mis latencias son tan altas? (común con Ollama local)

```
P95 = 15 segundos → ¿es malo?

Para un LLM local (llama3.2:3b en CPU):
  - Generación: ~30-50 tokens/segundo
  - Respuesta de 100 tokens = 2-3 segundos ← NORMAL
  - Respuesta de 500 tokens = 10-15 segundos ← NORMAL en CPU

Para un LLM via API (Azure OpenAI gpt-4o):
  - P95 debería ser <3 segundos
  - Si es >5s → problema de red o throttling

Benchmark esperado en clase (CPU, llama3.2:3b):
  - P50: ~3s
  - P95: ~10s
  - Con cache hit rate >60%: P50 efectivo < 50ms
```

## Demo en Vivo: Observar el Autoescalado

```bash
# Setup en terminales separadas (usar tmux o múltiples ventanas)

# T1: Stack completo
docker-compose up llm-gateway redis  # Sin Ollama en Docker para el K8s demo

# T2: K8s local
minikube start --cpus=4 --memory=8192
kubectl apply -f kubernetes/local/

# T3: Monitoreo HPA
watch -n 2 "echo '=== HPA ===' && kubectl get hpa -n llm-prod && \
    echo '=== PODS ===' && kubectl get pods -n llm-prod"

# T4: Test de carga (después de que los pods estén listos)
sleep 30  # Esperar inicialización
k6 run loadtesting/k6/load-test.js

# Lo que observar:
# - T3 muestra HPA TARGETS aumentando (ej: 15%/70% → 85%/70%)
# - HPA agrega pods (REPLICAS: 2 → 4 → 6)
# - Después de 5 min sin carga, vuelve a 2 réplicas
```
