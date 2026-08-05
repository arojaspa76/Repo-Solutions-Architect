"""
Herramienta: Search — Sesión 7
==================================
Herramienta de búsqueda de información para el agente LLM.

NOTA PEDAGÓGICA: Implementación MOCK para la clase.
En producción conectarías a:
  - Google Custom Search API
  - Bing Search API
  - SerpAPI
  - Brave Search API (económico y sin censura)
  - Tavily (optimizado para LLMs/agentes)

Esta herramienta simula búsquedas sobre temas de infraestructura
cloud y LLMs — relevante para el contexto del curso.
"""

import asyncio
import logging
import random
from datetime import date

logger = logging.getLogger(__name__)

# Base de conocimiento simulada sobre temas del curso
_KNOWLEDGE_BASE: list[dict] = [
    {
        "keywords": ["kubernetes", "k8s", "hpa", "autoescalado"],
        "result": (
            "Kubernetes HPA (HorizontalPodAutoscaler) ajusta automáticamente el número "
            "de réplicas de un Deployment según métricas de CPU/RAM u otras métricas "
            "personalizadas. Fórmula: replicas = ceil(actual × (metrica_actual / objetivo)). "
            "Tiempo de reacción: ~30 segundos. Cooldown de scale-down: 5 minutos."
        ),
    },
    {
        "keywords": ["keda", "event-driven", "scale to zero"],
        "result": (
            "KEDA (Kubernetes Event-Driven Autoscaling) extiende HPA para escalar desde "
            "y hasta 0 réplicas. Soporta >60 triggers: HTTP, Redis, Kafka, Azure Service Bus, "
            "SQS, etc. Instalación: helm install keda kedacore/keda. "
            "Ahorro típico: 40-60% en cargas variables."
        ),
    },
    {
        "keywords": ["llm", "modelo", "language model", "gpt", "llama"],
        "result": (
            "Los LLMs (Large Language Models) como GPT-4o, Claude 3.5, Llama 3.2 y Gemini 1.5 "
            "son modelos de transformer entrenados con billones de parámetros. "
            "Para inferencia en producción: GPU A100 80GB para modelos >70B, "
            "GPU T4 para modelos 7-13B, CPU suficiente para modelos ≤3B (con Ollama)."
        ),
    },
    {
        "keywords": ["react", "agente", "agent", "reasoning"],
        "result": (
            "ReAct (Reasoning + Acting) es un framework para agentes LLM que alterna entre "
            "razonamiento (Thought) y acción (Action/Observation). Publicado por Yao et al. 2022. "
            "Mejora significativamente la precisión vs chain-of-thought simple, especialmente "
            "en tareas que requieren información externa o herramientas."
        ),
    },
    {
        "keywords": ["azure", "aks", "azure kubernetes"],
        "result": (
            "Azure Kubernetes Service (AKS) es el servicio gestionado de K8s en Azure. "
            "Características destacadas: KEDA addon oficial, integración con Azure OpenAI, "
            "Node Autoprovision (NAP) como alternativa a Cluster Autoscaler, "
            "Azure Monitor para observabilidad nativa. Precio: solo pagas por los nodos."
        ),
    },
    {
        "keywords": ["gke", "google cloud", "gcp", "autopilot"],
        "result": (
            "GKE Autopilot es el modo 'serverless' de Kubernetes en Google Cloud. "
            "No gestionas nodos — pagas por pods (CPU + RAM solicitados). "
            "Nodos escalan en <2 minutos. VPA (Vertical Pod Autoscaler) preinstalado. "
            "Ideal para equipos sin DevOps dedicado."
        ),
    },
    {
        "keywords": ["eks", "aws", "karpenter", "amazon"],
        "result": (
            "EKS (Elastic Kubernetes Service) con Karpenter provisionan nodos en <2 min "
            "(vs 5-10 min con Cluster Autoscaler). Karpenter elige el tipo de instancia "
            "óptimo por costo y capacidad. Spot instances: hasta 90% de ahorro. "
            "Instalación: helm install karpenter oci://public.ecr.aws/karpenter/karpenter."
        ),
    },
    {
        "keywords": ["k6", "locust", "prueba de carga", "load testing", "performance"],
        "result": (
            "k6 es la herramienta de pruebas de carga más popular para APIs. Open source (Grafana). "
            "Define tests en JavaScript. Métricas clave: p95 latency, error rate, RPS. "
            "Tipos: smoke (5 VUs, sanidad), load (50-100 VUs, normal), "
            "stress (200+ VUs, límite), spike (pico súbito). "
            "Locust es la alternativa en Python."
        ),
    },
    {
        "keywords": ["ollama", "local", "llm local"],
        "result": (
            "Ollama permite ejecutar LLMs localmente sin API keys ni costo de nube. "
            "Modelos disponibles: llama3.2:3b (2GB RAM), llama3.1:8b (5GB), "
            "mistral:7b (4GB), phi3:mini (2GB), codellama:7b (4GB). "
            "API compatible con OpenAI: POST /api/chat. "
            "Perfecto para desarrollo, testing y demos sin internet."
        ),
    },
]


class SearchTool:
    """
    Herramienta de búsqueda para el agente LLM.

    Uso por el agente:
        Action: search
        Action Input: ¿qué es KEDA en Kubernetes?
        Observation: KEDA (Kubernetes Event-Driven Autoscaling) extiende HPA...
    """

    name = "search"
    description = (
        "Busca información sobre temas de infraestructura cloud, LLMs y K8s. "
        "Input: pregunta o tema a buscar (en español). "
        "Retorna información técnica relevante."
    )

    async def run(self, query: str) -> str:
        """
        Buscar información sobre el query.

        Args:
            query: Pregunta o tema a buscar

        Returns:
            Resultado de la búsqueda
        """
        # Simular latencia de API (80-200ms)
        await asyncio.sleep(random.uniform(0.08, 0.2))

        query_lower = query.lower()

        # Buscar en la base de conocimiento
        best_match = None
        best_score = 0

        for entry in _KNOWLEDGE_BASE:
            score = sum(1 for kw in entry["keywords"] if kw in query_lower)
            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score > 0:
            logger.info(f"🔍 Search: encontrado resultado para '{query[:40]}...'")
            return f"{best_match['result']} [Fuente: BSG Knowledge Base, {date.today()}]"

        # No encontrado — respuesta genérica
        logger.info(f"🔍 Search: sin resultado específico para '{query[:40]}...'")
        return (
            f"No encontré información específica sobre '{query}'. "
            f"Temas disponibles: Kubernetes/K8s, KEDA, LLMs, agentes ReAct, "
            f"Azure/GKE/EKS, k6/Locust, Ollama. "
            f"Para información más detallada, consulta la documentación oficial."
        )
