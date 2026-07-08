"""
routers/chat.py
================
Endpoint POST /chat — flujo RAG completo.

Flujo:
  1. Valida el request
  2. Genera embedding de la pregunta
  3. Busca fragmentos relevantes en AI Search
  4. Recupera historial de Cosmos DB
  5. Llama a GPT-4o con contexto enriquecido
  6. Persiste el nuevo turno en Cosmos DB
  7. Retorna la respuesta con fuentes y métricas
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, SourceDocument

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse, summary="Enviar pregunta al chatbot")
async def chat(request: Request, body: ChatRequest):
    """
    Endpoint principal del chatbot de soporte IT.

    - Implementa el patrón RAG completo.
    - Mantiene historial de conversación por session_id.
    - Registra métricas en Azure Monitor (latencia, tokens).
    """
    openai_svc = request.app.state.openai_service
    search_svc = request.app.state.search_service
    cosmos_svc = request.app.state.cosmos_service

    try:
        # ── Paso 1: Embedding de la pregunta ──────────────────────────────
        logger.info("Generando embedding para session_id=%s", body.session_id)
        query_vector = openai_svc.get_embedding(body.question)

        # ── Paso 2: Búsqueda vectorial en AI Search ───────────────────────
        raw_docs = search_svc.vector_search(query_vector, top_k=body.top_k)

        if not raw_docs:
            logger.warning("No se encontraron documentos relevantes.")

        # ── Paso 3: Construir contexto para el LLM ────────────────────────
        context_parts = []
        sources = []
        for doc in raw_docs:
            context_parts.append(
                f"[{doc['title']}]\n{doc['content']}"
            )
            sources.append(SourceDocument(
                title=doc["title"],
                content=doc["content"][:200] + "...",  # Preview en la respuesta
                score=round(doc["score"], 4),
                source_file=doc["source_file"],
            ))
        context = "\n\n---\n\n".join(context_parts) or "No se encontró información relevante."

        # ── Paso 4: Recuperar historial de conversación ───────────────────
        history = await cosmos_svc.get_history(body.session_id)

        # ── Paso 5: Llamar a GPT-4o ───────────────────────────────────────
        answer, tokens, latency_ms = openai_svc.chat_completion(
            question=body.question,
            context=context,
            conversation_history=history,
        )

        # ── Paso 6: Persistir en Cosmos DB ────────────────────────────────
        await cosmos_svc.save_turn(
            session_id=body.session_id,
            user_id=body.user_id,
            question=body.question,
            answer=answer,
            tokens=tokens,
        )

        return ChatResponse(
            answer=answer,
            session_id=body.session_id,
            sources=sources,
            tokens_used=tokens,
            latency_ms=round(latency_ms, 2),
        )

    except Exception as exc:
        logger.exception("Error en el flujo RAG: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(exc)}")
