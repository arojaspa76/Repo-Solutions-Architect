#!/usr/bin/env python3
"""
Benchmark del Agente LLM — Multi-Cloud (Sesión 7)
====================================================
Compara latencia del agente en local vs Azure/GCP/AWS.

El agente hace múltiples llamadas al LLM por request,
por eso las latencias son significativamente más altas
que un API gateway simple.

Uso:
    python scripts/benchmark-agent.py
    python scripts/benchmark-agent.py --endpoints \\
        http://localhost:8000 \\
        http://mi-aks-ip \\
        http://mi-gke-ip \\
        http://mi-eks-ip
"""

import asyncio
import argparse
import json
import statistics
import time
from dataclasses import dataclass, field
import httpx
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class BenchmarkResult:
    endpoint: str
    label: str
    iterations: int
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    total_steps: list[int] = field(default_factory=list)
    tools_used: dict = field(default_factory=dict)

    @property
    def success_count(self): return len(self.latencies)
    @property
    def p50(self): return statistics.median(self.latencies) if self.latencies else 0
    @property
    def p95(self):
        if not self.latencies: return 0
        return sorted(self.latencies)[int(len(self.latencies) * 0.95)]
    @property
    def p99(self):
        if not self.latencies: return 0
        return sorted(self.latencies)[int(len(self.latencies) * 0.99)]
    @property
    def avg(self): return statistics.mean(self.latencies) if self.latencies else 0
    @property
    def avg_steps(self): return statistics.mean(self.total_steps) if self.total_steps else 0
    @property
    def error_rate(self): return self.errors / self.iterations if self.iterations > 0 else 0


BENCHMARK_QUERIES = [
    {"input": "¿Cuánto es 1234 * 5678?", "session_id": "bench-1"},
    {"input": "¿Qué clima hay en Bogotá?", "session_id": "bench-2"},
    {"input": "¿Qué es KEDA en Kubernetes?", "session_id": "bench-3"},
]


async def benchmark_endpoint(
    endpoint: str,
    label: str,
    iterations: int = 5,
    workers: int = 2,
) -> BenchmarkResult:
    result = BenchmarkResult(endpoint=endpoint, label=label, iterations=iterations)
    semaphore = asyncio.Semaphore(workers)

    async def single_request(i: int):
        async with semaphore:
            query = BENCHMARK_QUERIES[i % len(BENCHMARK_QUERIES)]
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    start = time.perf_counter()
                    resp = await client.post(
                        f"{endpoint}/agent/run",
                        json={**query, "model": "llama3.2:3b"},
                    )
                    elapsed = (time.perf_counter() - start) * 1000

                    if resp.status_code == 200:
                        result.latencies.append(elapsed)
                        data = resp.json()
                        result.total_steps.append(data.get("total_steps", 0))
                        for step in data.get("steps", []):
                            if step.get("action"):
                                t = step["action"]
                                result.tools_used[t] = result.tools_used.get(t, 0) + 1
                    else:
                        result.errors += 1
            except Exception as e:
                result.errors += 1
                console.print(f"  [red]{label}: {type(e).__name__}[/red]")

    tasks = [single_request(i) for i in range(iterations)]
    await asyncio.gather(*tasks)
    return result


def print_report(results: list[BenchmarkResult]):
    console.print("\n")

    table = Table(
        title="📊 Benchmark Agente LLM — Multi-Cloud (Sesión 7)",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )
    table.add_column("Endpoint", style="white", min_width=18)
    table.add_column("N", justify="right", style="dim")
    table.add_column("Errores", justify="right", style="red")
    table.add_column("P50 (ms)", justify="right", style="green")
    table.add_column("P95 (ms)", justify="right", style="yellow")
    table.add_column("P99 (ms)", justify="right", style="red")
    table.add_column("Avg Pasos", justify="right", style="cyan")
    table.add_column("Herramientas", justify="left", style="magenta")

    for r in results:
        tools_str = ", ".join(f"{k}:{v}" for k, v in r.tools_used.items()) or "N/A"
        table.add_row(
            r.label,
            str(r.iterations),
            f"{r.errors}" if r.errors else "0",
            f"{r.p50:,.0f}",
            f"{r.p95:,.0f}",
            f"{r.p99:,.0f}",
            f"{r.avg_steps:.1f}",
            tools_str[:30],
        )

    console.print(table)

    console.print("\n[bold cyan]💡 Interpretación para agentes LLM:[/bold cyan]")
    console.print("  • P50 alto (5-15s) es NORMAL — el agente hace múltiples LLM calls")
    console.print("  • P95 muy alto (>30s) indica sobrecarga — añadir más réplicas")
    console.print("  • Avg Pasos > 3 → queries complejas con múltiples herramientas")
    console.print("  • En K8s con HPA: P95 debe mejorar bajo carga (más réplicas)")
    console.print("  • Cache ayuda para preguntas repetidas (reduce 90%+ la latencia)\n")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark del Agente LLM multi-cloud")
    parser.add_argument("--endpoints", nargs="*", default=["http://localhost:8000"])
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    def get_label(url: str) -> str:
        if "localhost" in url or "127.0.0.1" in url: return "🖥  Local"
        elif "azure" in url or "azurewebsites" in url: return "🔵 Azure AKS"
        elif "cloudfunctions" in url or "run.app" in url: return "🟡 GCP GKE"
        elif "amazonaws" in url or "execute-api" in url: return "🟠 AWS EKS"
        return f"🌐 {url[:25]}..."

    console.print("\n[bold cyan]🤖 Benchmark Multi-Cloud — Agente LLM (Sesión 7)[/bold cyan]")
    console.print(f"[dim]Endpoints: {len(args.endpoints)} | Iteraciones: {args.iterations}[/dim]\n")

    results = []
    for ep in args.endpoints:
        label = get_label(ep)
        console.print(f"[cyan]⏱  Benchmarking {label}...[/cyan]")
        r = await benchmark_endpoint(ep, label, args.iterations, args.workers)
        results.append(r)
        if r.success_count > 0:
            console.print(f"   ✅ {r.success_count}/{r.iterations} exitosos | P95={r.p95:.0f}ms | avg_pasos={r.avg_steps:.1f}")
        else:
            console.print(f"   ❌ Sin respuestas exitosas")

    print_report(results)


if __name__ == "__main__":
    asyncio.run(main())
