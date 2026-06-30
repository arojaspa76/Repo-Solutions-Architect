# 💰 Análisis de Costos y ROI — Infraestructura LLM Multi-Cloud
## Sesión 3 | BSG Institute

---

## Marco de Evaluación de Proveedores Cloud

Para seleccionar el proveedor cloud adecuado, evaluamos **7 criterios clave**:

### 1. Criterios de Evaluación

| # | Criterio | Peso | Descripción |
|---|----------|------|-------------|
| 1 | **Costo total** | 25% | TCO: cómputo + API + storage + red + soporte |
| 2 | **Ecosistema** | 20% | Integración con servicios actuales de la empresa |
| 3 | **Latencia** | 15% | Distancia a regiones en LATAM |
| 4 | **Compliance** | 15% | GDPR, ISO 27001, SOC 2, regulaciones locales |
| 5 | **Escalabilidad** | 10% | Capacidad de crecer de 100 a 1M requests/día |
| 6 | **SLA** | 10% | Disponibilidad garantizada (99.9% a 99.99%) |
| 7 | **Vendor lock-in** | 5% | Posibilidad de migrar o usar multi-cloud |

### 2. Scorecard Comparativo (1-10)

| Criterio | Azure | GCP | AWS | Local (Ollama) |
|----------|-------|-----|-----|----------------|
| Costo | 7 | 9 | 7 | 10 |
| Ecosistema Microsoft | 10 | 5 | 6 | N/A |
| Regiones LATAM | 8 | 7 | 9 | 10 |
| Compliance | 9 | 8 | 9 | 10 |
| Escalabilidad LLM | 9 | 8 | 8 | 4 |
| SLA | 9 | 9 | 9 | N/A |
| Portabilidad | 8 | 8 | 7 | 10 |
| **Puntaje total** | **8.4** | **7.8** | **7.9** | **7.3*** |

> *Ollama local tiene puntaje alto por costo cero, pero no aplica para producción enterprise a escala.

---

## Análisis de Costos Detallado

### Escenario de Referencia
- **Peticiones/mes**: 100,000
- **Tokens promedio/petición**: 500 entrada + 300 salida
- **Almacenamiento**: 50 GB (modelos + logs)
- **Nodos Kubernetes**: 2 nodos estándar
- **Entorno**: Producción enterprise

### Costo Mensual por Componente (USD)

```
┌─────────────────┬──────────┬──────────┬──────────┬──────────────┐
│ Componente      │  Azure   │   GCP    │   AWS    │ Local/Ollama │
├─────────────────┼──────────┼──────────┼──────────┼──────────────┤
│ Cómputo (K8s)   │ $140.16  │  $97.82  │ $121.18  │    $0.00     │
│ K8s mgmt fee    │  $73.00  │  $73.00  │  $73.00  │    $0.00     │
│ LLM API         │  $45.00  │  $37.50  │  $29.70  │    $0.00     │
│ Storage         │   $0.90  │   $1.00  │   $1.15  │    $0.00     │
│ Red (egress)    │   $0.44  │   $0.43  │   $0.45  │    $0.00     │
├─────────────────┼──────────┼──────────┼──────────┼──────────────┤
│ TOTAL/mes       │ $259.50  │ $209.75  │ $225.48  │    ~$2.00    │
│ TOTAL/año       │$3,114.00 │$2,517.00 │$2,705.76 │   ~$24.00    │
└─────────────────┴──────────┴──────────┴──────────┴──────────────┘
```

> ⚠️ Nota: Precios aproximados. Siempre verificar en las calculadoras oficiales:
> - Azure: https://azure.microsoft.com/pricing/calculator/
> - GCP: https://cloud.google.com/products/calculator
> - AWS: https://calculator.aws/

---

## Análisis de Costos a Corto y Largo Plazo

### Corto Plazo (0-6 meses): Fase de Desarrollo

**Recomendación: Ollama Local + Azure for Students**

| Item | Costo |
|------|-------|
| Ollama (desarrollo local) | $0/mes |
| Azure for Students ($100 crédito) | $0 (primeros 2-4 meses) |
| GitHub (repos privados) | $4/mes |
| **Total fase desarrollo** | **~$4-50/mes** |

**Acciones clave:**
- Usar Ollama para todo el desarrollo y testing
- Azure for Students para validar la arquitectura cloud
- Minikube local para pruebas de Kubernetes

### Mediano Plazo (6-18 meses): Fase Producción

**Recomendación: Proveedor único según ecosistema**

| Volumen | Azure | GCP | AWS |
|---------|-------|-----|-----|
| 10K req/mes | $89 | $71 | $82 |
| 100K req/mes | $260 | $210 | $225 |
| 1M req/mes | $1,850 | $1,420 | $1,680 |
| 10M req/mes | $16,200 | $12,800 | $14,900 |

### Largo Plazo (18+ meses): Optimización

**Estrategias de reducción de costos:**

1. **Reserved Instances**: 30-72% de descuento pagando 1-3 años por adelantado
2. **Spot/Preemptible**: 60-90% descuento para cargas no críticas
3. **Committed Use**: GCP ofrece hasta 70% descuento con compromiso anual
4. **Auto-scaling**: Ajustar automáticamente la capacidad a la demanda real
5. **Modelo más pequeño**: Usar llama3.2:3b en lugar de GPT-4 donde sea suficiente
6. **Caching**: Redis/Memcached para respuestas frecuentes (reduce llamadas LLM)
7. **Batch processing**: Agrupar peticiones para procesar en horarios valle

---

## Análisis de ROI

### Metodología de Cálculo

```
ROI = (Beneficios - Costos) / Costos × 100%

Beneficios = Reducción de tiempo × Costo de tiempo humano
           + Nuevas capacidades × Valor de negocio generado
           + Reducción de errores × Costo de errores

Costos = Infraestructura + Desarrollo + Mantenimiento + Capacitación
```

### Caso de Estudio: Sistema de Soporte IT con LLM

**Contexto**: Empresa con 500 empleados, 200 tickets de soporte IT/mes

| Métrica | Sin LLM | Con LLM | Diferencia |
|---------|---------|---------|------------|
| Tiempo promedio por ticket | 45 min | 12 min | -73% |
| Tickets resueltos sin escalar | 40% | 75% | +87% |
| Costo por ticket | $22.50 | $6.00 + $0.26 API | -71% |
| Satisfacción usuario (1-10) | 6.2 | 8.4 | +35% |
| Tickets/mes procesados | 200 | 450 | +125% |

**Cálculo ROI Anual:**
```
Ahorro en tiempo agente: (200 tickets × 33 min × $30/hr) × 12 = $39,600/año
Nuevas capacidades: 250 tickets adicionales × $6 × 12 = $18,000/año
Total beneficios: $57,600/año

Costos infraestructura (Azure): $3,114/año
Desarrollo inicial: $12,000 (one-time)
Mantenimiento: $2,400/año
Total costos año 1: $17,514

ROI año 1: ($57,600 - $17,514) / $17,514 × 100% = 229%
Payback: 3.6 meses
```

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Aumento de precios cloud | Media | Alto | Contratos reserved, multi-cloud |
| Dependencia de proveedor | Alta | Alto | Kubernetes = portabilidad |
| Calidad de respuestas LLM | Media | Alto | RAGAS, monitoreo, human-in-loop |
| Seguridad de datos | Baja | Muy Alto | VPC, encriptación, RBAC |
| Disponibilidad (outages) | Baja | Alto | Multi-región, health checks |
| Costos inesperados | Alta | Medio | Alertas de presupuesto, rate limiting |
| Cambio de modelos/APIs | Media | Medio | Abstracción via LangChain |

---

## Recomendaciones por Sector LATAM

| Sector | Recomendación | Razón |
|--------|--------------|-------|
| **Banca/Finanzas** | Azure | Compliance BBVA, Santander; FedRAMP, SOC2 |
| **Salud** | Azure o AWS | HIPAA compliance, certificaciones médicas |
| **Gobierno** | Azure Gov o AWS GovCloud | Soberanía de datos |
| **Retail** | AWS | Integración con eCommerce, mejor costo |
| **Educación** | GCP | Precios académicos, Google Workspace |
| **Startups** | Ollama + GCP | Costo mínimo inicial, escalabilidad |

---

## Calculadora Interactiva

```bash
# Ejecutar la calculadora para tu caso específico
python scripts/cost-calculator.py \
  --requests 500000 \       # Peticiones al mes
  --input-tokens 800 \      # Tokens de entrada promedio
  --output-tokens 400 \     # Tokens de salida promedio
  --storage-gb 100          # GB de almacenamiento
```

---

**BSG Institute** | Sesión 3: Kubernetes, Docker y Contenedores para LLMs
