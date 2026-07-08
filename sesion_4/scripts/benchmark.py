#!/usr/bin/env python3
"""
Benchmark de Latencia Multi-Cloud — Sesión 4
=============================================
Compara la latencia del mismo endpoint desplegado en:
  - Local (Ollama)
  - Azure Functions / AKS
  - Google Cloud Functions / GKE
  - AWS Lambda / EKS

Uso:
    # Comparar local vs nube
    python scripts/benchmark.py \\
        --endpoints \\
        http://localhost:8000 \\
        https://mi-func.azurewebsites.net/api \\
        https://us-central1-mi-proyecto.cloudfunctions.net \\
        https://mi-lambda.execute-api.us-east-1.amazonaws.com/prod

    # Solo local
    python scripts/benchmark.py

    # Con más iteraciones
    python scripts/benchmark.py --iterations 20 --workers 5
"""

import asyncio
import argparse
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class BenchmarkResult:
    endpoint: str
    label: str
    iterations: int
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    cache_hits: int = 0

    @property
    def success_count(self):
        return len(self.latencies)

    @property
    def p50(self): return statistics.median(self.latencies) if self.latencies else 0
    @property
    def p95(self):
        if not self.latencies: return 0
        sorted_l = sorted(self.latencies)
        return sorted_l[int(len(sorted_l) * 0.95)]
    @property
    def p99(self):
        if not self.latencies: return 0
        sorted_l = sorted(self.latencies)
        return sorted_l[int(len(sorted_l) * 0.99)]
    @property
    def avg(self): return statistics.mean(self.latencies) if self.latencies else 0
    @property
    def min(self): return min(self.latencies) if self.latencies else 0
    @property
    def max(self): return max(self.latencies) if self.latencies else 0
    @property
    def error_rate(self): return self.errors / self.iterations if self.iterations > 0 else 0
    @property
    def cache_rate(self): return self.cache_hits / self.success_count if self.success_count > 0 else 0


# ── Benchmark de un endpoint ───────────────────────────────────────────────────
async def benchmark_endpoint(
    endpoint: str,
    label: str,
    iterations: int = 10,
    workers: int = 3,
    prompt: str = "¿Qué es el autoescalado en Kubernetes? Responde en 2 oraciones.",
    chat_path: str = "/chat",
) -> BenchmarkResult:
    """Benchmark async de un endpoint con workers concurrentes."""

    result = BenchmarkResult(endpoint=endpoint, label=label, iterations=iterations)
    semaphore = asyncio.Semaphore(workers)

    async def single_request(i: int):
        async with semaphore:
            payload = {
                "message": prompt,
                "model": "llama3.2:3b",
                "use_cache": i > 2,  # Las primeras 2 iteraciones sin cache (fuerza miss)
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    start = time.perf_counter()
                    resp = await client.post(
                        f"{endpoint}{chat_path}",
                        json=payload,
                    )
                    elapsed_ms = (time.perf_counter() - start) * 1000

                    if resp.status_code == 200:
                        result.latencies.append(elapsed_ms)
                        try:
                            data = resp.json()
                            if data.get("cached"):
                                result.cache_hits += 1
                        except Exception:
                            pass
                    else:
                        result.errors += 1
                        console.print(f"  [red]Error {resp.status_code} en {label}[/red]")

            except Exception as e:
                result.errors += 1
                console.print(f"  [red]Exception en {label}: {type(e).__name__}[/red]")

    tasks = [single_request(i) for i in range(iterations)]
    await asyncio.gather(*tasks)
    return result


# ── Reporte en tabla ───────────────────────────────────────────────────────────
def print_report(results: list[BenchmarkResult]):
    console.print("\n")

    # Tabla principal
    table = Table(
        title="📊 Benchmark de Latencia Multi-Cloud — LLM Gateway",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )

    table.add_column("Endpoint", style="white", min_width=20)
    table.add_column("N", justify="right", style="dim")
    table.add_column("Errores", justify="right", style="red")
    table.add_column("P50 (ms)", justify="right", style="green")
    table.add_column("P95 (ms)", justify="right", style="yellow")
    table.add_column("P99 (ms)", justify="right", style="red")
    table.add_column("Avg (ms)", justify="right", style="cyan")
    table.add_column("Cache Hit%", justify="right", style="magenta")
    table.add_column("Veredicto", justify="center")

    for r in results:
        verdict = ""
        if r.error_rate > 0.5:
            verdict = "❌ Sin servicio"
        elif r.p95 < 1000:
            verdict = "🚀 Excelente"
        elif r.p95 < 5000:
            verdict = "✅ Bueno"
        elif r.p95 < 15000:
            verdict = "⚠️  Lento"
        else:
            verdict = "🐢 Muy lento"

        table.add_row(
            r.label,
            str(r.iterations),
            f"{r.errors} ({r.error_rate*100:.0f}%)" if r.errors > 0 else "0",
            f"{r.p50:,.0f}",
            f"{r.p95:,.0f}",
            f"{r.p99:,.0f}",
            f"{r.avg:,.0f}",
            f"{r.cache_rate*100:.0f}%",
            verdict,
        )

    console.print(table)

    # Análisis comparativo
    if len(results) > 1:
        successful = [r for r in results if r.success_count > 0]
        if successful:
            fastest = min(successful, key=lambda r: r.p95)
            slowest = max(successful, key=lambda r: r.p95)

            console.print(f"\n🏆 [bold green]Más rápido:[/bold green] {fastest.label} (P95: {fastest.p95:.0f}ms)")
            if fastest != slowest:
                ratio = slowest.p95 / fastest.p95 if fastest.p95 > 0 else 0
                console.print(f"🐢 [bold red]Más lento:[/bold red] {slowest.label} (P95: {slowest.p95:.0f}ms, {ratio:.1f}x más lento)")

    # Interpretación pedagógica
    console.print("\n[bold cyan]💡 Interpretación:[/bold cyan]")
    console.print("  • P50 = latencia mediana (50% de requests son más rápidos)")
    console.print("  • P95 = latencia del percentil 95 (el 5% más lento)")
    console.print("  • P99 = latencia del percentil 99 (importante para SLA)")
    console.print("  • Cache Hit% alto → muy pocos LLM calls reales → latencia baja")
    console.print("  • En producción, apuntar a P95 < 3s para chat interactivo\n")


# ── CLI ────────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark de latencia multi-cloud para LLM Gateway"
    )
    parser.add_argument(
        "--endpoints", nargs="*",
        default=["http://localhost:8000"],
        help="URLs de los endpoints a comparar"
    )
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--prompt", default="¿Qué es el autoescalado en Kubernetes? Responde en 2 oraciones.",
        help="Prompt a enviar en cada request"
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    # Labels automáticos basados en la URL
    def get_label(url: str) -> str:
        if "localhost" in url or "127.0.0.1" in url:
            return "🖥  Local (Ollama)"
        elif "azure" in url or "azurewebsites" in url or "azurecr" in url:
            return "🔵 Azure"
        elif "cloudfunctions" in url or "run.app" in url or "appspot" in url:
            return "🟡 GCP"
        elif "amazonaws" in url or "execute-api" in url:
            return "🟠 AWS"
        else:
            return f"🌐 {url[:30]}..."

    console.print("\n[bold cyan]🔬 Benchmark Multi-Cloud — LLM Gateway[/bold cyan]")
    console.print(f"[dim]Endpoints: {len(args.endpoints)} | Iteraciones: {args.iterations} | Workers: {args.workers}[/dim]\n")

    results = []
    for endpoint in args.endpoints:
        label = get_label(endpoint)
        console.print(f"[cyan]⏱  Benchmarking {label}...[/cyan]")

        result = await benchmark_endpoint(
            endpoint=endpoint,
            label=label,
            iterations=args.iterations,
            workers=args.workers,
            prompt=args.prompt,
        )
        results.append(result)

        if result.success_count > 0:
            console.print(f"   ✅ {result.success_count}/{result.iterations} exitosos, P95={result.p95:.0f}ms")
        else:
            console.print(f"   ❌ Sin respuestas exitosas")

    print_report(results)


if __name__ == "__main__":
    asyncio.run(main())
