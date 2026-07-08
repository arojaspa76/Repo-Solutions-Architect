/**
 * k6 Load Test — Carga Normal
 * ================================
 * Simula carga realista de producción con ramping gradual.
 * Objetivo: validar comportamiento bajo carga esperada y
 * observar el autoescalado del HPA en acción.
 *
 * Escenario (perfil de carga):
 *   0:00 → 2:00  —  Ramp-up:  0 → 50 usuarios
 *   2:00 → 7:00  —  Sostenido: 50 usuarios
 *   7:00 → 8:00  —  Spike:    50 → 100 usuarios (pico)
 *   8:00 → 9:00  —  Reducción: 100 → 50 usuarios
 *   9:00 → 10:00 —  Ramp-down: 50 → 0 usuarios
 *
 * Uso:
 *   k6 run loadtesting/k6/load-test.js
 *   k6 run -e BASE_URL=http://mi-cluster-ip loadtesting/k6/load-test.js
 *
 * Mientras corre, en otra terminal observar el HPA:
 *   watch kubectl get hpa -n llm-prod
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// ── Métricas personalizadas ────────────────────────────────────────────────
const errorRate      = new Rate('errors');
const chatP95        = new Trend('chat_p95_ms', true);
const summarizeP95   = new Trend('summarize_p95_ms', true);
const cacheHits      = new Counter('cache_hits_count');
const cacheMisses    = new Counter('cache_misses_count');

// ── Configuración ─────────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '2m',  target: 50  },  // Ramp-up gradual
    { duration: '5m',  target: 50  },  // Carga sostenida — HPA mantiene pods
    { duration: '1m',  target: 100 },  // Spike — HPA escala hacia arriba
    { duration: '1m',  target: 50  },  // Reducción
    { duration: '1m',  target: 0   },  // Ramp-down — HPA reduce pods (tras 5min)
  ],
  thresholds: {
    'http_req_duration':    ['p(95)<5000'],    // P95 < 5s (LLMs son lentos)
    'http_req_duration{name:"health"}': ['p(95)<200'],  // Health < 200ms
    'errors':               ['rate<0.05'],     // <5% errores
  },
};

// ── Datos de prueba ────────────────────────────────────────────────────────
const chatMessages = [
  '¿Qué es el autoescalado horizontal en Kubernetes?',
  'Explica el patrón Circuit Breaker.',
  '¿Cuándo usar serverless vs contenedores para LLMs?',
  '¿Qué es KEDA y cómo mejora el autoescalado?',
  'Define alta disponibilidad en sistemas distribuidos.',
  '¿Qué métricas usar para el HPA en aplicaciones LLM?',
];

const textsToSummarize = [
  `Kubernetes es un sistema open source de orquestación de contenedores 
   que automatiza el despliegue, escalado y operación de aplicaciones 
   contenerizadas. Fue originalmente diseñado por Google y donado a la 
   Cloud Native Computing Foundation (CNCF) en 2014. Kubernetes agrupa 
   los contenedores que forman una aplicación en unidades lógicas para 
   facilitar su gestión y descubrimiento.`,

  `Los modelos de lenguaje grandes (LLMs) como GPT-4, Claude y Llama 
   requieren infraestructura especializada para funcionar eficientemente 
   en producción. Los principales desafíos incluyen la alta latencia de 
   inferencia, los grandes requerimientos de memoria, la necesidad de 
   GPUs especializadas y la gestión de picos de demanda variables.`,
];

// ── Escenario principal ────────────────────────────────────────────────────
export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // Distribución de carga realista:
  // 40% health checks, 40% chat, 20% summarize
  const rand = Math.random();

  if (rand < 0.4) {
    // ── Health Check (rápido) ────────────────────────────────────────────
    group('health', () => {
      const res = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
      check(res, { 'health 200': (r) => r.status === 200 }) || errorRate.add(1);
    });
    sleep(0.1);

  } else if (rand < 0.8) {
    // ── Chat con LLM ──────────────────────────────────────────────────────
    group('chat', () => {
      const message = randomItem(chatMessages);
      const start = Date.now();

      const res = http.post(
        `${BASE_URL}/chat`,
        JSON.stringify({ message, model: 'llama3.2:3b', use_cache: true }),
        { headers, timeout: '60s', tags: { name: 'chat' } }
      );

      chatP95.add(Date.now() - start);

      const ok = check(res, {
        'chat: status 200': (r) => r.status === 200,
        'chat: tiene mensaje': (r) => {
          try { return JSON.parse(r.body).message?.length > 0; }
          catch { return false; }
        },
      });

      if (!ok) errorRate.add(1);

      // Contabilizar cache
      try {
        const body = JSON.parse(res.body);
        body.cached ? cacheHits.add(1) : cacheMisses.add(1);
      } catch { }
    });
    sleep(2); // LLMs son lentos — dar tiempo para procesar

  } else {
    // ── Summarize (ejercicio serverless-like) ─────────────────────────────
    group('summarize', () => {
      const text = randomItem(textsToSummarize);
      const start = Date.now();

      const res = http.post(
        `${BASE_URL}/summarize`,
        JSON.stringify({ text, language: 'es', max_length: 80 }),
        { headers, timeout: '60s', tags: { name: 'summarize' } }
      );

      summarizeP95.add(Date.now() - start);

      check(res, {
        'summarize: status 200': (r) => r.status === 200,
        'summarize: compression >10%': (r) => {
          try { return JSON.parse(r.body).compression_ratio > 0.1; }
          catch { return false; }
        },
      }) || errorRate.add(1);
    });
    sleep(1);
  }
}

// ── Resumen enriquecido ────────────────────────────────────────────────────
export function handleSummary(data) {
  const m = data.metrics;

  const totalReqs    = m['http_reqs']?.values?.count || 0;
  const errRate      = m['errors']?.values?.rate || 0;
  const p95          = m['http_req_duration']?.values?.['p(95)'] || 0;
  const p99          = m['http_req_duration']?.values?.['p(99)'] || 0;
  const avgDur       = m['http_req_duration']?.values?.avg || 0;
  const cacheHitsCnt = m['cache_hits_count']?.values?.count || 0;
  const cacheMissCnt = m['cache_misses_count']?.values?.count || 0;
  const totalCache   = cacheHitsCnt + cacheMissCnt;
  const hitRate      = totalCache > 0 ? (cacheHitsCnt / totalCache * 100).toFixed(1) : '0.0';

  console.log('\n============================================');
  console.log('📊 LOAD TEST — RESUMEN COMPLETO');
  console.log('============================================');
  console.log(`Total requests:     ${totalReqs}`);
  console.log(`Error rate:         ${(errRate * 100).toFixed(2)}%`);
  console.log(`Latencia promedio:  ${avgDur.toFixed(0)}ms`);
  console.log(`P95 latencia:       ${p95.toFixed(0)}ms`);
  console.log(`P99 latencia:       ${p99.toFixed(0)}ms`);
  console.log(`Cache hit rate:     ${hitRate}% (${cacheHitsCnt}/${totalCache})`);
  console.log('--------------------------------------------');
  const pass = errRate < 0.05 && p95 < 5000;
  console.log(`Resultado:          ${pass ? '✅ PASS' : '❌ FAIL'}`);
  if (!pass) {
    if (errRate >= 0.05) console.log(`  ❌ Error rate ${(errRate*100).toFixed(1)}% supera límite 5%`);
    if (p95 >= 5000) console.log(`  ❌ P95 ${p95.toFixed(0)}ms supera límite 5000ms`);
  }
  console.log('============================================\n');

  return { stdout: '' };
}
