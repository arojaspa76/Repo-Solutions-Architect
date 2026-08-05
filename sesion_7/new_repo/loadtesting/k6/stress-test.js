/**
 * k6 Stress Test — Agente LLM (Sesión 7)
 * ==========================================
 * Encontrar el punto de quiebre del agente bajo carga extrema.
 * 
 * Observar durante el test:
 *   Terminal 2: watch kubectl get hpa,pods -n llm-prod
 *   Terminal 3: watch curl -s localhost:8000/metrics | grep agent
 * 
 * Lo que esperar ver:
 *   - HPA escalando agresivamente (2 → 8+ pods)
 *   - Circuit breaker abriéndose bajo carga extrema
 *   - Latencia del agente aumentando (50s+ en el pico)
 *   - Rate limiter respondiendo con 429
 *   - Recovery gradual cuando la carga baja
 * 
 * ⚠️ ADVERTENCIA: Este test puede saturar el sistema.
 *    Solo ejecutar en entorno de pruebas.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const errorRate    = new Rate('errors');
const agentLatency = new Trend('agent_latency_ms', true);

export const options = {
  stages: [
    { duration: '1m',  target: 5   },  // Warmup suave
    { duration: '2m',  target: 15  },  // Carga normal del agente
    { duration: '2m',  target: 30  },  // Alta carga
    { duration: '2m',  target: 50  },  // Estrés — punto de quiebre esperado
    { duration: '2m',  target: 75  },  // Estrés extremo
    { duration: '2m',  target: 30  },  // Recovery
    { duration: '1m',  target: 0   },  // Ramp-down
  ],
  thresholds: {
    // Umbrales permisivos para stress test
    'http_req_duration': ['p(99)<120000'],  // P99 < 2 minutos
    'errors': ['rate<0.40'],                // Hasta 40% errores bajo estrés extremo
  },
};

const agentQueries = [
  '¿Cuánto es 999 * 888?',
  '¿Qué clima hay en Medellín?',
  '¿Qué es Kubernetes en 1 oración?',
  'Busca información sobre autoescalado.',
  '¿Cuánto es sqrt(10000)?',
];

let queryIdx = 0;

export default function () {
  const headers = { 'Content-Type': 'application/json' };
  const query = agentQueries[queryIdx++ % agentQueries.length];
  const start = Date.now();

  const res = http.post(
    `${BASE_URL}/agent/run`,
    JSON.stringify({
      input: query,
      session_id: `stress-${__VU}`,
      model: 'llama3.2:3b',
    }),
    { headers, timeout: '120s', tags: { name: 'agent_stress' } }
  );

  agentLatency.add(Date.now() - start);

  // En stress test, 503 (circuit breaker) y 429 (rate limit) son ESPERADOS
  const ok = check(res, {
    'respuesta válida': (r) => [200, 429, 503].includes(r.status),
    'sin 500 inesperado': (r) => r.status !== 500,
  });

  if (!ok) errorRate.add(1);

  sleep(1); // Menos sleep = más presión
}

export function handleSummary(data) {
  const m = data.metrics;
  console.log('\n============================================');
  console.log('📊 STRESS TEST AGENTE — ANÁLISIS');
  console.log('============================================');
  console.log(`Total requests:    ${m['http_reqs']?.values?.count || 0}`);
  console.log(`Error rate:        ${((m['errors']?.values?.rate || 0) * 100).toFixed(2)}%`);
  console.log(`P50 latencia:      ${(m['agent_latency_ms']?.values?.['p(50)'] || 0).toFixed(0)}ms`);
  console.log(`P95 latencia:      ${(m['agent_latency_ms']?.values?.['p(95)'] || 0).toFixed(0)}ms`);
  console.log(`P99 latencia:      ${(m['agent_latency_ms']?.values?.['p(99)'] || 0).toFixed(0)}ms`);
  console.log(`Max latencia:      ${(m['agent_latency_ms']?.values?.max || 0).toFixed(0)}ms`);
  console.log('--------------------------------------------');
  console.log('🔍 Observar:');
  console.log('  • ¿En qué VU empezaron los errores?');
  console.log('  • ¿Cuántos pods escaló el HPA?');
  console.log('  • ¿Se abrió el circuit breaker?');
  console.log('  • ¿El P95 se disparó o se mantuvo?');
  console.log('============================================\n');
  return { stdout: '' };
}
