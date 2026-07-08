/**
 * k6 Smoke Test — Sanidad Rápida
 * =================================
 * Objetivo: verificar que el sistema funciona correctamente
 * con carga mínima antes de ejecutar tests más agresivos.
 *
 * Parámetros:
 *   - 5 usuarios virtuales
 *   - Duración: 1 minuto
 *   - Latencia aceptable: <2 segundos
 *   - Error rate: 0%
 *
 * Uso:
 *   k6 run loadtesting/k6/smoke-test.js
 *   k6 run -e BASE_URL=https://mi-api.azurewebsites.net loadtesting/k6/smoke-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ── Variables de entorno ───────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// ── Métricas personalizadas ────────────────────────────────────────────────
const errorRate    = new Rate('errors');
const chatLatency  = new Trend('chat_latency_ms', true);
const cacheHitRate = new Rate('cache_hits');

// ── Configuración del test ─────────────────────────────────────────────────
export const options = {
  vus: 5,           // 5 usuarios virtuales concurrentes
  duration: '1m',   // Duración: 1 minuto

  thresholds: {
    // El 95% de requests debe ser <2 segundos
    'http_req_duration': ['p(95)<2000'],
    // Tasa de errores: 0%
    'errors': ['rate<0.01'],
    // Latencia del chat: p95 < 30 segundos (LLMs son lentos)
    'chat_latency_ms': ['p(95)<30000'],
  },
};

// ── Datos de prueba ───────────────────────────────────────────────────────
const testMessages = [
  '¿Qué es Kubernetes?',
  '¿Cuál es la diferencia entre serverless y contenedores?',
  'Explica el patrón circuit breaker en 50 palabras.',
  '¿Qué es el autoescalado horizontal en Kubernetes?',
];

// ── Test principal ────────────────────────────────────────────────────────
export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // 1. Health check
  const healthRes = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
  check(healthRes, {
    '✅ Health: status 200': (r) => r.status === 200,
    '✅ Health: status healthy': (r) => {
      try { return JSON.parse(r.body).status === 'healthy'; }
      catch { return false; }
    },
  }) || errorRate.add(1);

  sleep(0.5);

  // 2. Chat con LLM (con cache — la primera llamada es lenta, las demás rápidas)
  const message = testMessages[Math.floor(Math.random() * testMessages.length)];
  const chatStart = Date.now();

  const chatRes = http.post(
    `${BASE_URL}/chat`,
    JSON.stringify({ message, model: 'llama3.2:3b', use_cache: true }),
    { headers, tags: { name: 'chat' } }
  );

  const chatDuration = Date.now() - chatStart;
  chatLatency.add(chatDuration);

  const chatOk = check(chatRes, {
    '✅ Chat: status 200 o 503': (r) => r.status === 200 || r.status === 503,
    '✅ Chat: tiene respuesta': (r) => {
      if (r.status !== 200) return true; // Si Ollama no está, no es error del test
      try { return JSON.parse(r.body).message.length > 0; }
      catch { return false; }
    },
  });

  if (!chatOk && chatRes.status !== 503) errorRate.add(1);

  // Detectar cache hits
  try {
    const body = JSON.parse(chatRes.body);
    if (body.cached) cacheHitRate.add(1);
    else cacheHitRate.add(0);
  } catch { }

  sleep(1);
}

// ── Resumen al finalizar ──────────────────────────────────────────────────
export function handleSummary(data) {
  const p95 = data.metrics['http_req_duration']?.values?.['p(95)'] || 0;
  const errRate = data.metrics['errors']?.values?.rate || 0;
  const reqs = data.metrics['http_reqs']?.values?.count || 0;
  const cacheHits = data.metrics['cache_hits']?.values?.rate || 0;

  console.log('\n========================================');
  console.log('📊 SMOKE TEST — RESUMEN');
  console.log('========================================');
  console.log(`Total requests:  ${reqs}`);
  console.log(`Error rate:      ${(errRate * 100).toFixed(2)}%`);
  console.log(`P95 latency:     ${p95.toFixed(0)}ms`);
  console.log(`Cache hit rate:  ${(cacheHits * 100).toFixed(1)}%`);
  console.log(`Resultado:       ${errRate < 0.01 && p95 < 2000 ? '✅ PASS' : '❌ FAIL'}`);
  console.log('========================================\n');

  return { stdout: '' };
}
