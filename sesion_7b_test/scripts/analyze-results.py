#!/usr/bin/env python3
"""
Analizador de Resultados de Pruebas de Carga — Sesión 7
=========================================================
Lee archivos JSON exportados por k6 y genera un análisis
visual con tablas, percentiles y recomendaciones.

Uso:
    # Primero correr k6 con output JSON:
    k6 run --out json=loadtesting/results/load-$(date +%Y%m%d-%H%M).json \\
        loadtesting/k6/load-test.js

    # Luego analizar:
    python scripts/analyze-results.py
    python scripts/analyze-results.py --file loadtesting/results/load-20241201-1430.json
    python scripts/analyze-results.py --dir loadtesting/results/  # Todos los archivos
"""

import json
import argparse
import glob
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Instalar rich para mejor visualización: pip install rich")

console = Console() if RICH_AVAILABLE else None


# ── Parseo de resultados k6 JSON ──────────────────────────────────────────────
def parse_k6_json(filepath: str) -> dict:
    """
    Parsear archivo JSON de k6.

    k6 exporta una línea JSON por cada evento/métrica.
    Formato: {"type": "Metric", "data": {...}}
    """
    metrics = {}
    points = {}  # {metric_name: [values]}

    with open(filepath, "r") as f:
        for line in f:
            try:
                event = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            if event.get("type") == "Metric":
                name = event["data"]["name"]
                metrics[name] = event["data"]

            elif event.get("type") == "Point":
                name = event["data"]["metric"]
                value = event["data"]["value"]
                if name not in points:
                    points[name] = []
                points[name].append(value)

    return {"metrics": metrics, "points": points}


def calculate_percentile(values: list[float], p: float) -> float:
    """Calcular percentil de una lista de valores."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def analyze_results(data: dict, filename: str) -> dict:
    """Calcular estadísticas de los resultados."""
    points = data["points"]
    stats = {"filename": filename}

    # HTTP requests generales
    http_dur = points.get("http_req_duration", [])
    http_failed = points.get("http_req_failed", [])

    stats["total_requests"] = len(http_dur)
    stats["error_rate"] = sum(http_failed) / len(http_failed) if http_failed else 0

    if http_dur:
        stats["http_p50"]  = calculate_percentile(http_dur, 50)
        stats["http_p90"]  = calculate_percentile(http_dur, 90)
        stats["http_p95"]  = calculate_percentile(http_dur, 95)
        stats["http_p99"]  = calculate_percentile(http_dur, 99)
        stats["http_avg"]  = sum(http_dur) / len(http_dur)
        stats["http_max"]  = max(http_dur)
        stats["http_min"]  = min(http_dur)

    # Métricas del agente
    agent_lat = points.get("agent_latency_ms", [])
    if agent_lat:
        # Convertir de ms a segundos para consistencia
        agent_lat_s = [v / 1000 for v in agent_lat]
        stats["agent_p50"] = calculate_percentile(agent_lat_s, 50)
        stats["agent_p95"] = calculate_percentile(agent_lat_s, 95)
        stats["agent_p99"] = calculate_percentile(agent_lat_s, 99)
        stats["agent_avg"] = sum(agent_lat_s) / len(agent_lat_s)
        stats["agent_max"] = max(agent_lat_s)

    # Cache
    cache_hits = points.get("cache_hits", [])
    stats["cache_hits"] = sum(cache_hits) if cache_hits else 0

    # Pasos del agente
    agent_steps = points.get("agent_steps_avg", [])
    if agent_steps:
        stats["avg_steps"] = sum(agent_steps) / len(agent_steps)

    # Tool calls
    tool_calls = points.get("agent_tool_calls", [])
    stats["tool_calls"] = sum(tool_calls) if tool_calls else 0

    return stats


# ── Evaluación de resultados ──────────────────────────────────────────────────
def evaluate_thresholds(stats: dict) -> list[dict]:
    """Evaluar si los resultados cumplen los umbrales esperados para el agente."""
    checks = []

    # Health check debe ser rápido
    http_p95 = stats.get("http_p95", 0)
    checks.append({
        "name": "P95 latencia HTTP general",
        "value": f"{http_p95:.0f}ms",
        "threshold": "< 45,000ms",
        "pass": http_p95 < 45000,
    })

    # Error rate
    err_rate = stats.get("error_rate", 0)
    checks.append({
        "name": "Tasa de errores",
        "value": f"{err_rate * 100:.2f}%",
        "threshold": "< 10%",
        "pass": err_rate < 0.10,
    })

    # Agente específico
    agent_p95 = stats.get("agent_p95", 0)
    if agent_p95 > 0:
        checks.append({
            "name": "P95 latencia agente",
            "value": f"{agent_p95:.1f}s",
            "threshold": "< 45s",
            "pass": agent_p95 < 45,
        })

        agent_p99 = stats.get("agent_p99", 0)
        checks.append({
            "name": "P99 latencia agente",
            "value": f"{agent_p99:.1f}s",
            "threshold": "< 90s",
            "pass": agent_p99 < 90,
        })

    return checks


def generate_recommendations(stats: dict, checks: list[dict]) -> list[str]:
    """Generar recomendaciones basadas en los resultados."""
    recs = []
    failed = [c for c in checks if not c["pass"]]

    agent_p95 = stats.get("agent_p95", 0)
    err_rate  = stats.get("error_rate", 0)
    cache_rate = stats.get("cache_hits", 0) / max(stats.get("total_requests", 1), 1)
    avg_steps  = stats.get("avg_steps", 0)

    if agent_p95 > 45:
        recs.append("⬆️  P95 > 45s: añadir más réplicas al HPA (aumentar maxReplicas)")
        recs.append("   → kubectl scale deployment llm-agent-gateway --replicas=6 -n llm-prod")

    if agent_p95 > 20:
        recs.append("⚡ P95 alto: reducir AGENT_MAX_STEPS en .env (actual probablemente 8, bajar a 5)")

    if err_rate > 0.10:
        recs.append("🔴 Error rate > 10%: revisar logs del agente")
        recs.append("   → docker-compose logs llm-agent | grep ERROR")

    if cache_rate < 0.30:
        recs.append("💾 Cache hit rate < 30%: los usuarios hacen preguntas muy variadas")
        recs.append("   → Considera aumentar CACHE_TTL_SECONDS en .env")

    if cache_rate > 0.70:
        recs.append("✅ Excelente cache hit rate (>70%) — el Redis está muy efectivo")

    if avg_steps > 4:
        recs.append("🔄 Promedio de pasos alto (>4): las queries son complejas")
        recs.append("   → Normal si los usuarios hacen preguntas multi-herramienta")

    if not failed:
        recs.append("🎉 Todos los umbrales superados — sistema saludable bajo esta carga")

    return recs if recs else ["✅ Resultados dentro de parámetros normales"]


# ── Output ────────────────────────────────────────────────────────────────────
def print_rich_report(stats: dict, checks: list[dict], recs: list[str]):
    """Imprimir reporte con formato Rich."""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📊 Análisis de Resultados — Agente LLM[/bold cyan]\n"
        f"[dim]Archivo: {stats['filename']}[/dim]",
        border_style="cyan"
    ))

    # Tabla de métricas principales
    table = Table(title="Métricas de Latencia", box=box.ROUNDED,
                  border_style="blue", header_style="bold cyan")
    table.add_column("Métrica", style="white")
    table.add_column("Valor", justify="right")
    table.add_column("Interpretación", style="dim")

    rows = [
        ("Total requests",    str(stats.get("total_requests", 0)),     "Volumen total del test"),
        ("Error rate",        f"{stats.get('error_rate', 0)*100:.2f}%","Porcentaje de fallos"),
        ("HTTP P50",          f"{stats.get('http_p50', 0):.0f}ms",      "Latencia mediana"),
        ("HTTP P95",          f"{stats.get('http_p95', 0):.0f}ms",      "SLA — 95% de usuarios"),
        ("HTTP P99",          f"{stats.get('http_p99', 0):.0f}ms",      "Peor 1% de usuarios"),
    ]
    if stats.get("agent_p50"):
        rows += [
            ("Agente P50",    f"{stats.get('agent_p50', 0):.1f}s",     "Latencia típica del agente"),
            ("Agente P95",    f"{stats.get('agent_p95', 0):.1f}s",     "SLA del agente"),
            ("Agente P99",    f"{stats.get('agent_p99', 0):.1f}s",     "Peor caso del agente"),
            ("Agente avg",    f"{stats.get('agent_avg', 0):.1f}s",     "Promedio (menos fiable)"),
        ]
    rows += [
        ("Cache hits",        str(stats.get("cache_hits", 0)),          "Requests desde Redis"),
        ("Avg pasos ReAct",   f"{stats.get('avg_steps', 0):.1f}",       "Pasos por ejecución"),
        ("Tool calls total",  str(stats.get("tool_calls", 0)),          "Herramientas usadas"),
    ]
    for metric, value, interp in rows:
        table.add_row(metric, value, interp)
    console.print(table)
    console.print()

    # Tabla de umbrales
    t2 = Table(title="Evaluación de Umbrales", box=box.ROUNDED,
               border_style="blue", header_style="bold cyan")
    t2.add_column("Check", style="white")
    t2.add_column("Resultado", justify="right")
    t2.add_column("Umbral", justify="right", style="dim")
    t2.add_column("Estado", justify="center")

    for check in checks:
        estado = "[green]✅ PASS[/green]" if check["pass"] else "[red]❌ FAIL[/red]"
        t2.add_row(check["name"], check["value"], check["threshold"], estado)
    console.print(t2)
    console.print()

    # Recomendaciones
    console.print(Panel(
        "\n".join(recs),
        title="[bold yellow]💡 Recomendaciones[/bold yellow]",
        border_style="yellow"
    ))
    console.print()


def print_plain_report(stats: dict, checks: list[dict], recs: list[str]):
    """Imprimir reporte en texto plano."""
    print("\n" + "="*55)
    print("📊 ANÁLISIS DE RESULTADOS — AGENTE LLM")
    print("="*55)
    print(f"Archivo: {stats['filename']}")
    print(f"Total requests:    {stats.get('total_requests', 0)}")
    print(f"Error rate:        {stats.get('error_rate', 0)*100:.2f}%")
    print(f"HTTP P50:          {stats.get('http_p50', 0):.0f}ms")
    print(f"HTTP P95:          {stats.get('http_p95', 0):.0f}ms")
    if stats.get("agent_p95"):
        print(f"Agente P50:        {stats.get('agent_p50', 0):.1f}s")
        print(f"Agente P95:        {stats.get('agent_p95', 0):.1f}s")
    print("-"*55)
    print("UMBRALES:")
    for check in checks:
        icon = "✅" if check["pass"] else "❌"
        print(f"  {icon} {check['name']}: {check['value']} (umbral: {check['threshold']})")
    print("-"*55)
    print("RECOMENDACIONES:")
    for rec in recs:
        print(f"  {rec}")
    print("="*55 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Analizar resultados de k6 para el Agente LLM"
    )
    parser.add_argument("--file", help="Archivo JSON de k6 a analizar")
    parser.add_argument("--dir",  default="loadtesting/results/",
                        help="Directorio con archivos JSON (default: loadtesting/results/)")
    args = parser.parse_args()

    # Determinar archivos a analizar
    if args.file:
        files = [args.file]
    else:
        pattern = os.path.join(args.dir, "*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            print(f"No se encontraron archivos JSON en: {args.dir}")
            print("Ejecutar k6 con: k6 run --out json=loadtesting/results/test.json ...")
            sys.exit(0)

    for filepath in files:
        if not os.path.exists(filepath):
            print(f"Archivo no encontrado: {filepath}")
            continue

        try:
            data     = parse_k6_json(filepath)
            stats    = analyze_results(data, Path(filepath).name)
            checks   = evaluate_thresholds(stats)
            recs     = generate_recommendations(stats, checks)

            if RICH_AVAILABLE:
                print_rich_report(stats, checks, recs)
            else:
                print_plain_report(stats, checks, recs)

        except Exception as e:
            print(f"Error analizando {filepath}: {e}")


if __name__ == "__main__":
    main()
