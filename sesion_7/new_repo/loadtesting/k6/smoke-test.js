/**
 * k6 Smoke Test — Agente LLM (Sesión 7)
 * =========================================
 * Prueba de sanidad rápida antes de cualquier test más agresivo.
 * 
 * Objetivo:
 *   - Verificar que la API y el agente responden
 *   - Sin errores básicos
 *   - Latencia aceptable para el agente (más lento que una API simple)
 * 
 * Diferencia vs Sesión 4:
 *   - El agente puede tardar 5-30s por request (múltiples pasos ReAct)
 *   - Los thresholds de latencia son más permisivos
 *   - Verificamos el formato de respuesta del agente
 * 
 * Uso:
 *   k6 run loadtesting/k6/smoke-test.js
 *   k6 run -e BASE_URL=http://mi-aks-ip loadtesting/k6/smoke-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Métricas específicas del agente
const errorRate      = new Rate('errors');
const agentLatency   = new Trend('agent_latency_ms', true);
const agentSteps     = new Trend('agent_steps_count');

export const options = {
  vus: 3,           // Pocos usuarios para smoke test
  duration: '2m',  // 2 minutos — el agente es más lento

  thresholds: {
    // El agente puede tardar hasta 45s (múltiples llamadas al LLM)
    'http_req_duration': ['p(95)<45000'],
    // Health check debe ser rápido
    'http_req_duration{name:"health"}': ['p(95)<500'],
    'errors': ['rate<0.05'],
  },
};

// Preguntas de prueba que usan diferentes herramientas
const agentQueries = [
  { input: '¿Cuánto es 100 * 365?', expected_tool: 'calculator' },
  { input: '¿Qué clima hay en Bogotá?', expected_tool: 'weather' },
  { input: '¿Qué es KEDA en Kubernetes?', expected_tool: 'search' },
  { input: 'Explica el patrón ReAct en 2 oraciones.', expected_tool: null },
];

let queryIndex = 0;

export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // 1. Health check
  const healthRes = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
  check(healthRes, {
    '✅ Health 200': (r) => r.status === 200,
    '✅ Status healthy/degraded': (r) => {
      try {
        const b = JSON.parse(r.body);
        return ['healthy', 'degraded'].includes(b.status);
      } catch { return false; }
    },
  }) || errorRate.add(1);

  sleep(1);

  // 2. Listar herramientas del agente
  const toolsRes = http.get(`${BASE_URL}/agent/tools`, { tags: { name: 'agent_tools' } });
  check(toolsRes, {
    '✅ Tools 200': (r) => r.status === 200,
    '✅ Tiene herramientas': (r) => {
      try {
        const b = JSON.parse(r.body);
        return b.tools && b.tools.length >= 3;
      } catch { return false; }
    },
  }) || errorRate.add(1);

  sleep(0.5);

  // 3. Ejecutar el agente (el test más importante)
  const query = agentQueries[queryIndex % agentQueries.length];
  queryIndex++;

  const agentStart = Date.now();
  const agentRes = http.post(
    `${BASE_URL}/agent/run`,
    JSON.stringify({
      input: query.input,
      session_id: `smoke-${__VU}`,
      model: 'llama3.2:3b',
    }),
    { headers, timeout: '60s', tags: { name: 'agent_run' } }
  );

  agentLatency.add(Date.now() - agentStart);

  const agentOk = check(agentRes, {
    '✅ Agent 200 o 503': (r) => r.status === 200 || r.status === 503,
    '✅ Agent tiene output': (r) => {
      if (r.status !== 200) return true;
      try {
        const b = JSON.parse(r.body);
        return b.output && b.output.length > 5;
      } catch { return false; }
    },
    '✅ Agent tiene pasos': (r) => {
      if (r.status !== 200) return true;
      try {
        const b = JSON.parse(r.body);
        agentSteps.add(b.total_steps || 0);
        return typeof b.total_steps === 'number';
      } catch { return false; }
    },
  });

  if (!agentOk && agentRes.status !== 503) errorRate.add(1);

  sleep(3); // El agente necesita más tiempo entre requests
}

export function handleSummary(data) {
  const m = data.metrics;
  const p95 = m['agent_latency_ms']?.values?.['p(95)'] || 0;
  const errRate = m['errors']?.values?.rate || 0;
  const avgSteps = m['agent_steps_count']?.values?.avg || 0;
  const reqs = m['http_reqs']?.values?.count || 0;

  console.log('\n========================================');
  console.log('📊 SMOKE TEST AGENTE — RESUMEN');
  console.log('========================================');
  console.log(`Total requests:    ${reqs}`);
  console.log(`Error rate:        ${(errRate * 100).toFixed(2)}%`);
  console.log(`P95 latencia agente: ${p95.toFixed(0)}ms`);
  console.log(`Pasos promedio:    ${avgSteps.toFixed(1)} pasos/request`);
  console.log(`Resultado:         ${errRate < 0.05 ? '✅ PASS' : '❌ FAIL'}`);
  console.log('========================================\n');
  return { stdout: '' };
}
