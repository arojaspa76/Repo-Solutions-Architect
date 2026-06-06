"""
TechCorp RAG Orchestrator - main.py
====================================
FastAPI application que implementa el patrón RAG (Retrieval-Augmented Generation)
para el chatbot de soporte IT de TechCorp Latinoamérica.

Flujo:
  1. Recibe pregunta del usuario vía HTTP POST /chat
  2. Genera embedding del texto con Azure OpenAI (text-embedding-3-small)
  3. Busca los fragmentos más relevantes en Azure AI Search (búsqueda vectorial)
  4. Construye un prompt enriquecido con el contexto recuperado
  5. Llama a GPT-4o y retorna la respuesta
  6. Guarda historial en Azure Cosmos DB
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from dotenv import load_dotenv

from app.routers import chat, health, admin
from app.services.cosmos_service import CosmosService
from app.services.search_service import SearchService
from app.services.openai_service import OpenAIService

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Azure Monitor (OpenTelemetry) ──────────────────────────────────────────────
if conn_str := os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor(connection_string=conn_str)
    logger.info("Azure Monitor habilitado.")


# ── Lifespan: inicializa servicios compartidos ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servicios de TechCorp RAG Orchestrator...")
    app.state.openai_service = OpenAIService()
    app.state.search_service = SearchService()
    app.state.cosmos_service = CosmosService()
    await app.state.cosmos_service.initialize()
    logger.info("Todos los servicios listos.")
    yield
    logger.info("Cerrando conexiones...")
    await app.state.cosmos_service.close()


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TechCorp RAG Orchestrator",
    description="Chatbot de Soporte IT con Azure OpenAI + AI Search",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En producción: dominio específico de TechCorp
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Infraestructura"])
app.include_router(chat.router,   prefix="/chat",  tags=["Chat"])
app.include_router(admin.router,  prefix="/admin", tags=["Administración"])

# ── Instrumentación OpenTelemetry ─────────────────────────────────────────────
FastAPIInstrumentor.instrument_app(app)
