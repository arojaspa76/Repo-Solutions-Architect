#!/usr/bin/env python3
"""
============================================================
cost-calculator.py — Calculadora de costos multi-cloud
Sesión 3: Kubernetes, Docker y Contenedores para LLMs
BSG Institute
============================================================

Compara los costos de desplegar la misma aplicación LLM
en Azure, GCP y AWS, considerando:
- Cómputo (VMs/contenedores)
- Almacenamiento (imágenes Docker, modelos)
- Red (egress de datos)
- LLM API calls (tokens)
- Kubernetes (servicios gestionados)

Uso:
    python scripts/cost-calculator.py
    python scripts/cost-calculator.py --requests 1000000
"""

import argparse
from dataclasses import dataclass
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ── Modelos de datos ──────────────────────────────────────────────────────────

@dataclass
class ComputeCost:
    """Costos de cómputo mensual."""
    provider: str
    service: str               # AKS / GKE / EKS
    node_type: str             # Tipo de VM
    nodes: int
    cost_per_node_hour: float  # USD/hora por nodo
    
    @property
    def monthly_cost(self) -> float:
        return self.nodes * self.cost_per_node_hour * 730  # ~730h/mes


@dataclass
class LLMAPICost:
    """Costos de llamadas a LLM APIs."""
    provider: str
    model: str
    input_price_per_1k: float   # USD por 1K tokens de entrada
    output_price_per_1k: float  # USD por 1K tokens de salida
    
    def calculate(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1000) * self.input_price_per_1k +
            (output_tokens / 1000) * self.output_price_per_1k
        )


@dataclass
class StorageCost:
    """Costos de almacenamiento."""
    provider: str
    service: str
    cost_per_gb_month: float
    
    def calculate(self, gb: float) -> float:
        return gb * self.cost_per_gb_month


# ── Precios (aproximados, verificar en los portales para valores actuales) ────

COMPUTE_COSTS = [
    ComputeCost("Azure", "AKS", "D2s v3 (2vCPU, 8GB)", 2, 0.096),
    ComputeCost("GCP",   "GKE", "e2-standard-2 (2vCPU, 8GB)", 2, 0.067),
    ComputeCost("AWS",   "EKS", "t3.large (2vCPU, 8GB)", 2, 0.083),
]

LLM_API_COSTS = [
    LLMAPICost("Azure", "GPT-4o",          input_price_per_1k=0.005,  output_price_per_1k=0.015),
    LLMAPICost("Azure", "GPT-4o-mini",     input_price_per_1k=0.00015, output_price_per_1k=0.0006),
    LLMAPICost("GCP",   "Gemini 1.5 Pro",  input_price_per_1k=0.00125, output_price_per_1k=0.005),
    LLMAPICost("GCP",   "Gemini 1.5 Flash",input_price_per_1k=0.000075, output_price_per_1k=0.0003),
    LLMAPICost("AWS",   "Claude 3.5 Sonnet",input_price_per_1k=0.003, output_price_per_1k=0.015),
    LLMAPICost("AWS",   "Llama 3.1 70B",   input_price_per_1k=0.00099, output_price_per_1k=0.00099),
    # Ollama local: costo 0 en API calls (solo costo de hardware/electricidad)
    LLMAPICost("Ollama", "llama3.2:3b (local)", input_price_per_1k=0.0, output_price_per_1k=0.0),
]

STORAGE_COSTS = [
    StorageCost("Azure", "Azure Blob Storage", 0.018),  # USD/GB/mes
    StorageCost("GCP",   "Cloud Storage",      0.020),
    StorageCost("AWS",   "S3",                 0.023),
    StorageCost("Local", "SSD Local",          0.0),    # Costo de hardware amortizado
]

KUBERNETES_SERVICE_FEES = {
    "Azure": 0.10,   # USD/hora por clúster AKS gestionado
    "GCP":   0.10,   # GKE Autopilot: $0.10/hr
    "AWS":   0.10,   # EKS: $0.10/hr por clúster
}


# ── Funciones de cálculo ──────────────────────────────────────────────────────

def calculate_monthly_costs(
    requests_per_month: int = 100_000,
    avg_input_tokens: int = 500,
    avg_output_tokens: int = 300,
    storage_gb: float = 50.0,       # Modelos + datos
):
    """
    Calcula el costo mensual total para cada proveedor.
    
    Args:
        requests_per_month: Número de peticiones al LLM por mes
        avg_input_tokens: Tokens de entrada promedio por petición
        avg_output_tokens: Tokens de salida promedio por petición
        storage_gb: GB de almacenamiento requeridos
        
    Returns:
        Lista de dicts con el desglose de costos por proveedor
    """
    results = []
    
    total_input_tokens = requests_per_month * avg_input_tokens
    total_output_tokens = requests_per_month * avg_output_tokens
    
    providers = ["Azure", "GCP", "AWS"]
    
    for provider in providers:
        # Costo de cómputo (Kubernetes)
        compute = next(c for c in COMPUTE_COSTS if c.provider == provider)
        compute_cost = compute.monthly_cost
        
        # Cargo por clúster Kubernetes
        k8s_fee = KUBERNETES_SERVICE_FEES[provider] * 730
        
        # Costo de LLM API (modelo más económico de cada proveedor)
        provider_llm_costs = [c for c in LLM_API_COSTS if c.provider == provider]
        min_llm = min(provider_llm_costs, 
                      key=lambda c: c.calculate(avg_input_tokens, avg_output_tokens))
        llm_cost = min_llm.calculate(total_input_tokens, total_output_tokens)
        
        # Costo de almacenamiento
        storage = next(s for s in STORAGE_COSTS if s.provider == provider)
        storage_cost = storage.calculate(storage_gb)
        
        # Red (egress estimado: 10% del almacenamiento)
        # Precios aproximados de egress
        egress_prices = {"Azure": 0.087, "GCP": 0.085, "AWS": 0.090}
        network_cost = storage_gb * 0.1 * egress_prices[provider]
        
        total = compute_cost + k8s_fee + llm_cost + storage_cost + network_cost
        
        results.append({
            "provider": provider,
            "compute": compute_cost,
            "k8s_fee": k8s_fee,
            "llm_api": llm_cost,
            "llm_model": min_llm.model,
            "storage": storage_cost,
            "network": network_cost,
            "total": total,
        })
    
    # Agregar opción local (Ollama)
    results.append({
        "provider": "Local (Ollama)",
        "compute": 0.0,      # Asumiendo hardware existente
        "k8s_fee": 0.0,      # Minikube: gratis
        "llm_api": 0.0,      # Sin costo de API
        "llm_model": "llama3.2:3b",
        "storage": 2.0,      # ~$2/mes en electricidad estimada
        "network": 0.0,
        "total": 2.0,        # Costo mínimo (hardware + electricidad)
    })
    
    return results


def calculate_roi(
    monthly_cloud_cost: float,
    daily_requests: int,
    value_per_request: float = 0.50,  # Valor estimado por petición en USD
    months: int = 12,
):
    """
    Calcula el ROI del sistema LLM.
    
    Args:
        monthly_cloud_cost: Costo mensual total en USD
        daily_requests: Peticiones procesadas por día
        value_per_request: Valor de negocio por petición
        months: Período de evaluación
    """
    monthly_value = daily_requests * 30 * value_per_request
    monthly_profit = monthly_value - monthly_cloud_cost
    annual_profit = monthly_profit * months
    
    roi_percentage = ((monthly_profit * months) / (monthly_cloud_cost * months)) * 100
    payback_months = monthly_cloud_cost / monthly_profit if monthly_profit > 0 else float('inf')
    
    return {
        "monthly_value": monthly_value,
        "monthly_cost": monthly_cloud_cost,
        "monthly_profit": monthly_profit,
        "annual_profit": annual_profit,
        "roi_percentage": roi_percentage,
        "payback_months": payback_months,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def print_results_rich(results: list, requests: int, input_tokens: int, output_tokens: int):
    """Visualización con Rich (si está disponible)."""
    console = Console()
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]💰 Análisis de Costos Multi-Cloud — LLM Infrastructure[/bold cyan]\n"
        f"[dim]BSG Institute | Sesión 3[/dim]",
        border_style="cyan"
    ))
    
    # Parámetros
    console.print(f"\n[bold]Parámetros de evaluación:[/bold]")
    console.print(f"  • Peticiones/mes: [cyan]{requests:,}[/cyan]")
    console.print(f"  • Tokens entrada (promedio): [cyan]{input_tokens:,}[/cyan]")
    console.print(f"  • Tokens salida (promedio): [cyan]{output_tokens:,}[/cyan]")
    
    # Tabla de costos
    table = Table(
        title="\n📊 Costo Mensual por Proveedor (USD)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    
    table.add_column("Proveedor", style="bold", width=18)
    table.add_column("Cómputo", justify="right", width=12)
    table.add_column("K8s Fee", justify="right", width=10)
    table.add_column("LLM API", justify="right", width=14)
    table.add_column("Modelo", width=22)
    table.add_column("Storage", justify="right", width=10)
    table.add_column("Red", justify="right", width=8)
    table.add_column("TOTAL/mes", justify="right", style="bold green", width=12)
    table.add_column("TOTAL/año", justify="right", style="bold yellow", width=12)
    
    for r in sorted(results, key=lambda x: x["total"]):
        provider_color = {
            "Azure": "blue", "GCP": "red", "AWS": "orange1",
            "Local (Ollama)": "green"
        }.get(r["provider"], "white")
        
        table.add_row(
            f"[{provider_color}]{r['provider']}[/{provider_color}]",
            f"${r['compute']:,.2f}",
            f"${r['k8s_fee']:,.2f}",
            f"${r['llm_api']:,.2f}",
            r["llm_model"][:22],
            f"${r['storage']:,.2f}",
            f"${r['network']:,.2f}",
            f"${r['total']:,.2f}",
            f"${r['total']*12:,.2f}",
        )
    
    console.print(table)
    
    # ROI para el caso Azure (ejemplo)
    azure_cost = next(r for r in results if r["provider"] == "Azure")
    roi = calculate_roi(
        monthly_cloud_cost=azure_cost["total"],
        daily_requests=requests // 30,
        value_per_request=0.50,
    )
    
    console.print(Panel(
        f"[bold]Ejemplo ROI — Azure (estimado)[/bold]\n\n"
        f"  Valor mensual generado: [green]${roi['monthly_value']:,.2f}[/green]\n"
        f"  Costo mensual:          [red]${roi['monthly_cost']:,.2f}[/red]\n"
        f"  Ganancia mensual:       [green]${roi['monthly_profit']:,.2f}[/green]\n"
        f"  ROI anual:              [bold yellow]{roi['roi_percentage']:.1f}%[/bold yellow]\n"
        f"  Payback:                [cyan]{roi['payback_months']:.1f} meses[/cyan]",
        title="📈 Análisis ROI",
        border_style="green",
    ))
    
    # Criterios de decisión
    console.print(Panel(
        "[bold]Criterios de selección de proveedor:[/bold]\n\n"
        "  1. [cyan]Costo[/cyan]: GCP generalmente el más económico en cómputo\n"
        "  2. [cyan]Ecosistema[/cyan]: Integración con servicios existentes de la empresa\n"
        "  3. [cyan]Latencia[/cyan]: Región más cercana a los usuarios\n"
        "  4. [cyan]Compliance[/cyan]: GDPR, ISO, SOC2 según industria\n"
        "  5. [cyan]SLA[/cyan]: 99.9% a 99.99% disponibilidad garantizada\n"
        "  6. [cyan]Soporte técnico[/cyan]: Enterprise support y SLAs de respuesta\n"
        "  7. [cyan]Lock-in[/cyan]: Posibilidad de migración multi-cloud con Kubernetes\n\n"
        "[dim]💡 Ollama local: ideal para desarrollo y testing. Costo: ~$0/mes en API calls.[/dim]",
        title="🎯 Criterios de Decisión",
        border_style="blue",
    ))


def print_results_plain(results: list, requests: int):
    """Output sin Rich (fallback)."""
    print("\n" + "="*80)
    print("ANÁLISIS DE COSTOS MULTI-CLOUD — LLM INFRASTRUCTURE")
    print("BSG Institute | Sesión 3")
    print("="*80)
    print(f"Peticiones/mes: {requests:,}")
    print()
    print(f"{'Proveedor':<20} {'Cómputo':>12} {'LLM API':>12} {'Total/mes':>12} {'Total/año':>12}")
    print("-"*70)
    for r in sorted(results, key=lambda x: x["total"]):
        print(
            f"{r['provider']:<20} "
            f"${r['compute']:>10,.2f} "
            f"${r['llm_api']:>10,.2f} "
            f"${r['total']:>10,.2f} "
            f"${r['total']*12:>10,.2f}"
        )
    print("="*80)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Calculadora de costos multi-cloud para LLM infrastructure"
    )
    parser.add_argument(
        "--requests", type=int, default=100_000,
        help="Peticiones al LLM por mes (default: 100,000)"
    )
    parser.add_argument(
        "--input-tokens", type=int, default=500,
        help="Tokens de entrada promedio (default: 500)"
    )
    parser.add_argument(
        "--output-tokens", type=int, default=300,
        help="Tokens de salida promedio (default: 300)"
    )
    parser.add_argument(
        "--storage-gb", type=float, default=50.0,
        help="GB de almacenamiento (default: 50 GB)"
    )
    args = parser.parse_args()
    
    results = calculate_monthly_costs(
        requests_per_month=args.requests,
        avg_input_tokens=args.input_tokens,
        avg_output_tokens=args.output_tokens,
        storage_gb=args.storage_gb,
    )
    
    if RICH_AVAILABLE:
        print_results_rich(results, args.requests, args.input_tokens, args.output_tokens)
    else:
        print_results_plain(results, args.requests)
        print("\nInstala 'rich' para una visualización mejorada: pip install rich")


if __name__ == "__main__":
    main()
