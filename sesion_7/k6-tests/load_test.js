/**
 * k6-tests/load_test.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Prueba de carga para el chatbot TechCorp.
 * Capítulo 5 — Reducción de latencia y alta disponibilidad.
 *
 * Instalar k6: https://k6.io/docs/get-started/installation/
 * Ejecutar:    k6 run load_test.js --out json=results.json
 *
 * Etapas:
 *   0 → 100 usuarios en 2 min  (calentamiento)
 *   100 → 1,000 usuarios en 5 min  (pico de lunes 9am)
 *   1,000 → 0 en 2 min  (bajada)
 *
 * SLA de TechCorp:
 *   p95 de latencia < 2,000ms
 *   Tasa de error < 1%
 */

import http    from 'k6/http';
import { sleep, check, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ── Métricas personalizadas ──────────────────────────────────────────────────
const ragLatency   = new Trend('rag_latency_ms',    true);
const tokenCounter = new Counter('total_tokens_used');
const errorRate    = new Rate('error_rate');

// ── Configuración del test ────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '2m',  target: 100  },   // Rampa: 0 → 100 usuarios
    { duration: '5m',  target: 1000 },   // Pico:  100 → 1,000 usuarios
    { duration: '2m',  target: 0    },   // Bajada: 1,000 → 0
  ],
  thresholds: {
    // SLA de TechCorp: latencia p95 bajo 2 segundos
    http_req_duration:   ['p(95)<2000'],
    // Tasa de error menor al 1%
    http_req_failed:     ['rate<0.01'],
    // Métrica personalizada: latencia RAG p95 bajo 1.8s
    'rag_latency_ms':    ['p(95)<1800'],
    // Tasa de error personalizada
    'error_rate':        ['rate<0.01'],
  },
  // Resumen final en JSON y HTML
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ── Variables de entorno ──────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || 'https://api-techcorp.azure-api.net';
const API_KEY  = __ENV.API_KEY  || '';

// Banco de preguntas realistas de soporte IT TechCorp
const QUESTIONS = [
  '¿Cómo configuro la VPN en Windows 11?',
  'No puedo abrir Outlook, me da error de autenticación.',
  '¿Cuál es el proceso para solicitar un nuevo equipo de cómputo?',
  '¿Cómo reseteo mi contraseña del dominio corporativo?',
  'Mi impresora no aparece en la red, ¿qué hago?',
  '¿Cómo accedo a SharePoint desde casa?',
  'Necesito instalar Adobe Acrobat, ¿cómo lo solicito?',
  '¿Cuánto espacio tengo en mi OneDrive corporativo?',
  'Tengo el equipo lento desde la última actualización.',
  '¿Cómo conecto dos monitores a mi laptop Dell?',
  '¿Cuál es el servidor de correo saliente de TechCorp?',
  'Olvidé mi PIN de Windows Hello, ¿cómo lo recupero?',
];

// ── Función principal (se ejecuta por cada VU en cada iteración) ─────────────
export default function () {
  const question    = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const sessionId   = `session-${__VU}-${__ITER}`;       // VU + iteración = sesión única

  const headers = {
    'Content-Type':  'application/json',
    'x-functions-key': API_KEY,              // API Key de Azure API Management
  };

  group('POST /chat — RAG completo', () => {
    const payload = JSON.stringify({
      question,
      session_id: sessionId,
      user_id:    `vu-${__VU}`,
      top_k:      5,
    });

    const start    = Date.now();
    const response = http.post(`${BASE_URL}/chat/`, payload, {
      headers,
      timeout: '10s',
    });
    const elapsed  = Date.now() - start;

    // Registrar métricas personalizadas
    ragLatency.add(elapsed);
    errorRate.add(response.status !== 200);

    // Verificaciones de la respuesta
    const ok = check(response, {
      'status 200':          (r) => r.status === 200,
      'tiene campo answer':  (r) => {
        try { return JSON.parse(r.body).answer !== undefined; }
        catch { return false; }
      },
      'latencia < 3s':       (r) => r.timings.duration < 3000,
    });

    if (!ok) {
      console.error(`[VU=${__VU}] Error: status=${response.status} body=${response.body.slice(0, 200)}`);
    } else {
      try {
        const body = JSON.parse(response.body);
        tokenCounter.add(body.tokens_used || 0);
      } catch (_) {}
    }
  });

  // Pausa realista entre preguntas (simula lectura y escritura del usuario)
  sleep(Math.random() * 2 + 1);   // 1-3 segundos
}

// ── Reporte final personalizado ───────────────────────────────────────────────
export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration?.values?.['p(95)'] || 0;
  const errors = data.metrics.http_req_failed?.values?.rate || 0;

  const report = {
    timestamp:    new Date().toISOString(),
    sla_pass:     p95 < 2000 && errors < 0.01,
    results: {
      p95_latency_ms:  Math.round(p95),
      error_rate_pct:  (errors * 100).toFixed(2),
      total_requests:  data.metrics.http_reqs?.values?.count || 0,
      tokens_used:     data.metrics.total_tokens_used?.values?.count || 0,
    },
    thresholds_passed: Object.fromEntries(
      Object.entries(data.thresholds || {}).map(([k, v]) => [k, v.ok])
    ),
  };

  console.log('\n=== RESULTADO PRUEBA DE CARGA TECHCORP ===');
  console.log(JSON.stringify(report, null, 2));

  return {
    'results/load_test_summary.json': JSON.stringify(report, null, 2),
    stdout: JSON.stringify(report, null, 2),
  };
}
