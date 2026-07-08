/**
 * k6 Stress Test — Prueba de Estrés
 * ====================================
 * Objetivo: encontrar el punto de quiebre del sistema.
 * Incrementa la carga progresivamente hasta que el sistema
 * falla o los umbrales se superan.
 *
 * Esto nos permite:
 * - Conocer la capacidad máxima real del sistema
 * - Validar que el HPA escala correctamente bajo presión
 * - Identificar el cuello de botella (CPU, memoria, Ollama, red)
 *
 * ADVERTENCIA: Este test puede saturar el sistema.
 * Ejecutar solo en entorno de pruebas, nunca en producción activa.
 *
 * Uso:
 *   k6 run loadtesting/k6/stress-test.js
 *   # Con output a JSON para análisis posterior:
 *   k6 run --out json=results/stress-$(date +%Y%m%d-%H%M).json loadtesting/k6/stress-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const errorRate = new Rate('errors');
const latency   = new Trend('latency_ms', true);

export const options = {
  stages: [
    { duration: '2m',  target: 10  },   // Warmup
    { duration: '2m',  target: 50  },   // Carga normal
    { duration: '2m',  target: 100 },   // Alta carga
    { duration: '2m',  target: 150 },   // Estrés moderado
    { duration: '2m',  target: 200 },   // Estrés severo ← punto de quiebre esperado
    { duration: '2m',  target: 100 },   // Recovery
    { duration: '2m',  target: 0   },   // Ramp-down
  ],
  thresholds: {
    // Umbrales MÁS PERMISIVOS para stress test (esperamos degradación)
    'http_req_duration': ['p(99)<60000'],  // P99 < 60s
    'errors': ['rate<0.30'],               // Hasta 30% de errores se tolera bajo estrés
  },
};

export default function () {
  const headers = { 'Content-Type': 'application/json' };
  const start = Date.now();

  const res = http.post(
    `${BASE_URL}/chat`,
    JSON.stringify({
      message: '¿Qué es Kubernetes?',
      model: 'llama3.2:3b',
      use_cache: true,  // Cache importante para no saturar el LLM
    }),
    { headers, timeout: '90s', tags: { name: 'stress_chat' } }
  );

  latency.add(Date.now() - start);

  // En stress test, 503 (circuit breaker) es ESPERADO bajo alta carga
  const ok = check(res, {
    'respuesta válida (200 o 503)': (r) => r.status === 200 || r.status === 503,
    'no 5xx inesperados': (r) => r.status !== 500 && r.status !== 502,
  });

  if (!ok) errorRate.add(1);

  sleep(0.5);
}

export function handleSummary(data) {
  const m = data.metrics;
  const stages = [10, 50, 100, 150, 200, 100, 0];

  console.log('\n============================================');
  console.log('📊 STRESS TEST — ANÁLISIS DE RESULTADOS');
  console.log('============================================');
  console.log(`Total requests:    ${m['http_reqs']?.values?.count || 0}`);
  console.log(`Error rate:        ${((m['errors']?.values?.rate || 0) * 100).toFixed(2)}%`);
  console.log(`P50 latencia:      ${(m['latency_ms']?.values?.['p(50)'] || 0).toFixed(0)}ms`);
  console.log(`P95 latencia:      ${(m['latency_ms']?.values?.['p(95)'] || 0).toFixed(0)}ms`);
  console.log(`P99 latencia:      ${(m['latency_ms']?.values?.['p(99)'] || 0).toFixed(0)}ms`);
  console.log(`Max latencia:      ${(m['latency_ms']?.values?.max || 0).toFixed(0)}ms`);
  console.log('--------------------------------------------');
  console.log('🔍 Interpretar resultados:');
  console.log('  - P95 se dispara → cuello de botella encontrado');
  console.log('  - Errores >30% → sistema sobrepasó capacidad');
  console.log('  - HPA debería haber escalado para mitigar');
  console.log('  - Cache hit rate alta → buena resiliencia al estrés');
  console.log('============================================\n');
  return { stdout: '' };
}
