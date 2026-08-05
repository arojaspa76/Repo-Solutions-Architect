/**
 * k6 Load Test — Agente LLM (Sesión 7)
 * =========================================
 * Test de carga realista para el agente LLM.
 * 
 * Mientras este test corre, observar en otra terminal:
 *   watch -n 2 kubectl get hpa,pods -n llm-prod
 * 
 * El HPA debería escalar de 2 a 4-6 pods durante la carga sostenida.
 * 
 * Mix de requests (simula uso real):
 *   35% - Salud del sistema (rápidos)
 *   35% - Chat directo con LLM (medio: cache ayuda mucho)
 *   20% - Agente con herramientas (lento: múltiples pasos)
 *   10% - Agente con múltiples herramientas (muy lento)
 * 
 * Uso:
 *   k6 run loadtesting/k6/load-test.js
 *   k6 run -e BASE_URL=http://mi-aks-ip loadtesting/k6/load-test.js
 *   k6 run --out json=loadtesting/results/load-$(date +%Y%m%d).json loadtesting/k6/load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Métricas personalizadas
const errorRate       = new Rate('errors');
const agentLatency    = new Trend('agent_latency_ms', true);
const chatLatency     = new Trend('chat_latency_ms', true);
const cacheHits       = new Counter('cache_hits');
const agentToolCalls  = new Counter('agent_tool_calls');
const agentSteps      = new Trend('agent_steps_avg');

export const options = {
  stages: [
    { duration: '2m',  target: 10  },  // Ramp-up gradual
    { duration: '5m',  target: 25  },  // Carga sostenida — HPA escala
    { duration: '1m',  target: 40  },  // Pico moderado
    { duration: '1m',  target: 25  },  // Reducción
    { duration: '1m',  target: 0   },  // Ramp-down
  ],
  thresholds: {
    // Health debe ser rápido siempre
    'http_req_duration{name:"health"}': ['p(95)<300'],
    // Chat con cache puede ser muy rápido
    'chat_latency_ms':  ['p(95)<10000'],
    // El agente es inherentemente lento (múltiples LLM calls)
    'agent_latency_ms': ['p(95)<45000'],
    // Error rate global
    'errors':           ['rate<0.10'],
  },
};

// Queries para el chat directo (sin agente)
const chatQueries = [
  'Define alta disponibilidad en 2 oraciones.',
  '¿Qué es el patrón Circuit Breaker?',
  'Diferencia entre HPA y KEDA en K8s.',
  '¿Qué es Ollama y para qué sirve?',
  'Explica el patrón ReAct para agentes LLM.',
  '¿Cuándo usar serverless vs contenedores?',
];

// Queries para el agente — una herramienta
const agentSimpleQueries = [
  { input: '¿Cuánto es 1234 * 5678?', expected: 'calculator' },
  { input: '¿Qué clima hay en Bogotá hoy?', expected: 'weather' },
  { input: 'Busca información sobre KEDA', expected: 'search' },
  { input: '¿Cuánto es sqrt(2025)?', expected: 'calculator' },
  { input: '¿Cómo está el clima en Madrid?', expected: 'weather' },
];

// Queries para el agente — múltiples herramientas (más costoso)
const agentComplexQueries = [
  '¿Cuánto es 365 * 24 * 60? También dime el clima en Lima.',
  '¿Cuántos segundos tiene un año (365 * 24 * 3600) y qué clima hay en Buenos Aires?',
  'Calcula 100 * 200 y busca información sobre autoescalado en Kubernetes.',
];

export default function () {
  const headers = { 'Content-Type': 'application/json' };
  const rand = Math.random();

  if (rand < 0.35) {
    // ── Health check ───────────────────────────────────────────────────────
    group('health', () => {
      const res = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
      check(res, { 'health 200': (r) => r.status === 200 }) || errorRate.add(1);
    });
    sleep(0.2);

  } else if (rand < 0.70) {
    // ── Chat directo (con cache — alta probabilidad de hit) ───────────────
    group('chat', () => {
      const message = randomItem(chatQueries);
      const start = Date.now();

      const res = http.post(
        `${BASE_URL}/chat`,
        JSON.stringify({ message, model: 'llama3.2:3b', use_cache: true }),
        { headers, timeout: '30s', tags: { name: 'chat' } }
      );

      chatLatency.add(Date.now() - start);

      check(res, {
        'chat 200': (r) => r.status === 200,
        'chat tiene mensaje': (r) => {
          try { return JSON.parse(r.body).message?.length > 0; }
          catch { return false; }
        },
      }) || errorRate.add(1);

      try {
        if (JSON.parse(res.body).cached) cacheHits.add(1);
      } catch { }
    });
    sleep(1);

  } else if (rand < 0.90) {
    // ── Agente con una herramienta ─────────────────────────────────────────
    group('agent_simple', () => {
      const query = randomItem(agentSimpleQueries);
      const start = Date.now();

      const res = http.post(
        `${BASE_URL}/agent/run`,
        JSON.stringify({
          input: query.input,
          session_id: `load-${__VU}-simple`,
          model: 'llama3.2:3b',
        }),
        { headers, timeout: '60s', tags: { name: 'agent_run' } }
      );

      agentLatency.add(Date.now() - start);

      const ok = check(res, {
        'agent 200 o 503': (r) => r.status === 200 || r.status === 503,
        'agent tiene output': (r) => {
          if (r.status !== 200) return true;
          try { return JSON.parse(r.body).output?.length > 0; }
          catch { return false; }
        },
      });

      if (!ok && res.status !== 503) errorRate.add(1);

      try {
        const b = JSON.parse(res.body);
        agentSteps.add(b.total_steps || 0);
        const toolCalls = b.steps?.filter(s => s.action).length || 0;
        if (toolCalls > 0) agentToolCalls.add(toolCalls);
      } catch { }
    });
    sleep(4); // El agente necesita más pausa entre requests

  } else {
    // ── Agente con múltiples herramientas (más costoso — 10%) ─────────────
    group('agent_complex', () => {
      const query = randomItem(agentComplexQueries);
      const start = Date.now();

      const res = http.post(
        `${BASE_URL}/agent/run`,
        JSON.stringify({
          input: query,
          session_id: `load-${__VU}-complex`,
          model: 'llama3.2:3b',
        }),
        { headers, timeout: '90s', tags: { name: 'agent_complex' } }
      );

      agentLatency.add(Date.now() - start);

      check(res, {
        'agent complex 200 o 503': (r) => r.status === 200 || r.status === 503,
      }) || errorRate.add(1);

      try {
        const b = JSON.parse(res.body);
        agentSteps.add(b.total_steps || 0);
      } catch { }
    });
    sleep(6);
  }
}

export function handleSummary(data) {
  const m = data.metrics;

  const totalReqs   = m['http_reqs']?.values?.count || 0;
  const errRate     = m['errors']?.values?.rate || 0;
  const agentP50    = m['agent_latency_ms']?.values?.['p(50)'] || 0;
  const agentP95    = m['agent_latency_ms']?.values?.['p(95)'] || 0;
  const chatP95     = m['chat_latency_ms']?.values?.['p(95)'] || 0;
  const avgSteps    = m['agent_steps_avg']?.values?.avg || 0;
  const cacheTotal  = m['cache_hits']?.values?.count || 0;
  const toolsTotal  = m['agent_tool_calls']?.values?.count || 0;

  console.log('\n============================================');
  console.log('📊 LOAD TEST AGENTE LLM — RESUMEN');
  console.log('============================================');
  console.log(`Total requests:          ${totalReqs}`);
  console.log(`Error rate:              ${(errRate * 100).toFixed(2)}%`);
  console.log(`Agent P50 latencia:      ${agentP50.toFixed(0)}ms`);
  console.log(`Agent P95 latencia:      ${agentP95.toFixed(0)}ms`);
  console.log(`Chat P95 latencia:       ${chatP95.toFixed(0)}ms`);
  console.log(`Pasos promedio agente:   ${avgSteps.toFixed(1)}`);
  console.log(`Cache hits totales:      ${cacheTotal}`);
  console.log(`Tool calls totales:      ${toolsTotal}`);
  console.log('--------------------------------------------');
  const pass = errRate < 0.10 && agentP95 < 45000;
  console.log(`Resultado:               ${pass ? '✅ PASS' : '❌ FAIL'}`);
  if (!pass) {
    if (errRate >= 0.10) console.log(`  ❌ Error rate ${(errRate*100).toFixed(1)}% > 10%`);
    if (agentP95 >= 45000) console.log(`  ❌ Agent P95 ${agentP95.toFixed(0)}ms > 45000ms`);
  }
  console.log('============================================\n');
  return { stdout: '' };
}
