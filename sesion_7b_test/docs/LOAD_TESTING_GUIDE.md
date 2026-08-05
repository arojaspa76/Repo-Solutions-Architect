# 📖 Guía de Pruebas de Carga — Agente LLM (Sesión 7)

## ¿Por qué las pruebas del agente son diferentes?

Un agente LLM **no es una API REST normal**. Diferencias clave:

| Característica | API REST | Agente LLM |
|----------------|----------|-----------|
| Latencia típica | 50–500ms | 5–45 segundos |
| Llamadas internas | 1 | 2–8 (pasos ReAct) |
| Estado por request | Sin estado | Memoria de sesión |
| Timeout recomendado | 10s | 60–90s |
| VUs razonables | 100–500 | 10–50 |
| Error rate aceptable | <1% | <10% (bajo carga) |

---

## Tipos de Test — Orden obligatorio

### 1. Smoke Test (`smoke-test.js`)
**Cuándo:** Siempre, antes de cualquier otro test.
**Duración:** 2 minutos, 3 VUs.
**Objetivo:** ¿Funciona? ¿El agente responde? ¿Las herramientas ejecutan?

```bash
k6 run loadtesting/k6/smoke-test.js
```

Si el smoke falla → no correr el siguiente. Revisar logs primero:
```bash
docker-compose logs llm-agent | tail -50
```

### 2. Load Test (`load-test.js`)
**Cuándo:** Después de que el smoke pase.
**Duración:** 10 minutos, 25–40 VUs.
**Objetivo:** ¿Aguanta la carga normal de producción? ¿El HPA escala?

```bash
# Terminal 1: Load test
k6 run loadtesting/k6/load-test.js

# Terminal 2: Observar HPA en tiempo real
watch -n 2 kubectl get hpa,pods -n llm-prod
```

Mix de requests simulado:
- 35% health checks (rápidos, para ver disponibilidad)
- 35% chat directo con LLM (cache ayuda mucho aquí)
- 20% agente con 1 herramienta (5–15s por request)
- 10% agente con 2+ herramientas (15–40s por request)

### 3. Stress Test (`stress-test.js`)
**Cuándo:** Para encontrar el límite máximo.
**Duración:** 10 minutos, hasta 75 VUs.
**Objetivo:** ¿Cuándo empieza a fallar? ¿El circuit breaker protege Ollama?

```bash
k6 run loadtesting/k6/stress-test.js
```

Bajo estrés extremo, estos códigos son **esperados y correctos**:
- `503` — Circuit breaker abierto (protege Ollama de sobrecarga)
- `429` — Rate limiter activo (60 req/min por IP)

### 4. Spike Test (`spike-test.js`)
**Cuándo:** Para simular picos súbitos de tráfico.
**Duración:** ~3 minutos, 0 → 50 → 0 VUs.
**Objetivo:** ¿Sobrevive el sistema un pico? ¿Se recupera?

```bash
k6 run loadtesting/k6/spike-test.js
```

---

## Instalación de k6

```bash
# macOS
brew install k6

# Ubuntu/Debian
sudo apt-get install k6

# Windows
choco install k6
# o descargar desde: https://k6.io/downloads

# Docker (sin instalar)
docker run --rm -i grafana/k6 run - <loadtesting/k6/smoke-test.js
```

---

## Exportar resultados para análisis

```bash
# Exportar a JSON
k6 run \
    --out json=loadtesting/results/load-$(date +%Y%m%d-%H%M).json \
    loadtesting/k6/load-test.js

# Analizar con el script Python
python scripts/analyze-results.py

# Analizar un archivo específico
python scripts/analyze-results.py \
    --file loadtesting/results/load-20241201-1430.json

# Comparar todos los resultados en la carpeta
python scripts/analyze-results.py --dir loadtesting/results/
```

---

## Locust — Alternativa Python

```bash
# Instalar
pip install locust

# Modo headless (sin UI)
locust -f loadtesting/locust/locustfile.py \
    --headless -u 20 -r 2 -t 10m \
    --host http://localhost:8000 \
    --csv=loadtesting/results/locust-$(date +%Y%m%d)

# Con UI web (abrir http://localhost:8089)
locust -f loadtesting/locust/locustfile.py \
    --host http://localhost:8000
```

---

## Métricas clave y cómo leerlas

### P50 (Percentil 50 = Mediana)
La mitad de los usuarios tuvo esta latencia o menos. Es la **experiencia típica** del usuario.

Para el agente: P50 de 5–10 segundos es normal con Ollama en CPU.

### P95 (Percentil 95)
El 95% de usuarios tuvo esta latencia o menos. Es el número que va en el **SLA**.

Para el agente: P95 debe estar bajo 45 segundos. Si supera ese umbral, añadir réplicas.

### P99 (Percentil 99)
Solo el 1% más lento. Usuarios con mala suerte (queries complejas, LLM bajo carga).

Para el agente: P99 puede llegar a 60–90 segundos en carga alta — es aceptable.

### Error Rate
Porcentaje de requests que fallaron. Para el agente, umbrales distintos según el test:

| Test | Error rate aceptable |
|------|---------------------|
| Smoke | 0% |
| Load | < 10% |
| Stress | < 40% |
| Spike | < 50% |

### Cache Hit Rate
Porcentaje de requests respondidas desde Redis (< 80ms). Mayor cache hit → menor carga real al LLM → mejor P95.

Si el cache hit rate es < 20%, los usuarios hacen preguntas muy variadas. Considera aumentar el TTL del cache en `.env`.

---

## Demo en clase: ver el HPA escalando

```bash
# Abrir 3 terminales

# Terminal 1 — Desplegar
kubectl apply -f kubernetes/local/
kubectl wait --for=condition=ready pod -l app=llm-agent-gateway \
    -n llm-prod --timeout=120s

# Terminal 2 — Monitorear HPA
watch -n 2 "kubectl get hpa,pods -n llm-prod"

# Terminal 3 — Generar carga
k6 run loadtesting/k6/load-test.js
```

**Lo que verás en Terminal 2:**

```
# Sin carga (inicio):
NAME             TARGETS    MINPODS  MAXPODS  REPLICAS
llm-agent-hpa   12%/60%    2        15       2

# Después de 2 minutos de k6 (ramp-up):
llm-agent-hpa   68%/60%    2        15       2   ← supera threshold

# 30 segundos después (HPA reacciona):
llm-agent-hpa   68%/60%    2        15       3   ← escala!

# Carga sostenida:
llm-agent-hpa   55%/60%    2        15       4   ← estable

# 5 minutos después de terminar k6 (cooldown):
llm-agent-hpa   12%/60%    2        15       2   ← vuelve al mínimo
```

El HPA tarda ~30 segundos en reaccionar (frecuencia de evaluación) y 5 minutos en bajar (stabilizationWindowSeconds del scaleDown).
