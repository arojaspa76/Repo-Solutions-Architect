/**
 * k6 Spike Test — Agente LLM (Sesión 7)
 * ==========================================
 * Simula un pico súbito de tráfico: de 0 a muchos usuarios
 * en segundos, luego vuelta a 0 casi de inmediato.
 *
 * Casos reales de spike:
 *   - Campaña de marketing que arranca a medianoche
 *   - Notificación push a miles de usuarios simultáneos
 *   - Inicio de jornada laboral (todos se conectan a las 8am)
 *   - Evento en vivo donde todos preguntan al agente a la vez
 *
 * Lo que queremos verificar:
 *   1. ¿El sistema sobrevive el pico sin caerse?
 *   2. ¿El HPA reacciona a tiempo (30-60 seg)?
 *   3. ¿El circuit breaker protege Ollama bajo presión?
 *   4. ¿El sistema se recupera cuando baja el pico?
 *
 * Observar en otra terminal durante el test:
 *   watch -n 2 kubectl get hpa,pods -n llm-prod
 *
 * Uso:
 *   k6 run loadtesting/k6/spike-test.js
 *   k6 run -e BASE_URL=http://mi-aks-ip loadtesting/k6/spike-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const errorRate     = new Rate('errors');
const agentLatency  = new Trend('agent_latency_ms', true);
const circuitErrors = new Counter('circuit_breaker_opens');
const rateLimitHits = new Counter('rate_limit_hits');

export const options = {
  stages: [
    { duration: '30s', target: 2   },  // Baseline: 2 usuarios normales
    { duration: '10s', target: 50  },  // ← SPIKE: 0→50 en 10 segundos
    { duration: '1m',  target: 50  },  // Sostenido en el pico
    { duration: '10s', target: 2   },  // ← CAÍDA: 50→2 en 10 segundos
    { duration: '1m',  target: 2   },  // Recovery: ¿vuelve a la normalidad?
    { duration: '10s', target: 0   },  // Fin
  ],

  thresholds: {
    // Durante un spike, toleramos más errores
    'errors':           ['rate<0.50'],   // Hasta 50% errores en el pico
    // P99 puede dispararse pero no debe ser infinito
    'agent_latency_ms': ['p(99)<90000'], // P99 < 90 segundos
    // Health check debería seguir respondiendo
    'http_req_duration{name:"health"}': ['p(95)<2000'],
  },
};

// Queries simples — durante un spike priorizamos requests livianas
const spikeQueries = [
  '¿Cuánto es 100 * 200?',
  '¿Qué clima hay en Bogotá?',
  'Define HPA en una oración.',
  '¿Cuánto es sqrt(400)?',
];

let queryIdx = 0;

export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // Durante el spike, mezclamos health checks y requests al agente
  // Los health checks son baratos y ayudan a ver la disponibilidad
  const isHealthCheck = Math.random() < 0.3;

  if (isHealthCheck) {
    const res = http.get(`${BASE_URL}/health`, {
      tags: { name: 'health' },
      timeout: '5s',
    });
    check(res, { 'health responde': (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.1);
    return;
  }

  // Request al agente
  const query = spikeQueries[queryIdx++ % spikeQueries.length];
  const start = Date.now();

  const res = http.post(
    `${BASE_URL}/agent/run`,
    JSON.stringify({
      input: query,
      session_id: `spike-${__VU}`,
      model: 'llama3.2:3b',
    }),
    {
      headers,
      timeout: '90s',
      tags: { name: 'agent_spike' },
    }
  );

  agentLatency.add(Date.now() - start);

  // Durante spike, varios códigos son esperados:
  const ok = check(res, {
    '200 (éxito)':          (r) => r.status === 200,
    '503 (circuit breaker)':(r) => r.status === 503,
    '429 (rate limit)':     (r) => r.status === 429,
    'sin 500 inesperado':   (r) => r.status !== 500,
  });

  // Contabilizar tipos de error específicos
  if (res.status === 503) circuitErrors.add(1);
  if (res.status === 429) rateLimitHits.add(1);
  if (res.status >= 500 && res.status !== 503) errorRate.add(1);

  // Menos sleep = más presión durante el spike
  sleep(0.5);
}

export function handleSummary(data) {
  const m = data.metrics;

  const totalReqs   = m['http_reqs']?.values?.count || 0;
  const errRate     = m['errors']?.values?.rate || 0;
  const p50         = m['agent_latency_ms']?.values?.['p(50)'] || 0;
  const p95         = m['agent_latency_ms']?.values?.['p(95)'] || 0;
  const p99         = m['agent_latency_ms']?.values?.['p(99)'] || 0;
  const cbOpens     = m['circuit_breaker_opens']?.values?.count || 0;
  const rateLimits  = m['rate_limit_hits']?.values?.count || 0;

  console.log('\n============================================');
  console.log('📊 SPIKE TEST AGENTE LLM — RESUMEN');
  console.log('============================================');
  console.log(`Total requests:        ${totalReqs}`);
  console.log(`Error rate:            ${(errRate * 100).toFixed(2)}%`);
  console.log(`Agent P50:             ${p50.toFixed(0)}ms`);
  console.log(`Agent P95:             ${p95.toFixed(0)}ms`);
  console.log(`Agent P99:             ${p99.toFixed(0)}ms`);
  console.log(`Circuit breaker (503): ${cbOpens} veces`);
  console.log(`Rate limit (429):      ${rateLimits} veces`);
  console.log('--------------------------------------------');
  console.log('🔍 Preguntas clave del análisis:');
  console.log('  • ¿Cuántos 503 hubo en el pico? → Circuit breaker protegió Ollama');
  console.log('  • ¿Cuántos 429? → Rate limiter hizo su trabajo');
  console.log('  • ¿P95 en recovery bajó vs el pico? → HPA escaló correctamente');
  console.log('  • ¿El sistema volvió a P50 normal (~5s) después del pico?');
  console.log('============================================\n');

  return { stdout: '' };
}
