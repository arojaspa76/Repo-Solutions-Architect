"""
routers/admin.py
=================
Endpoints administrativos para gestión del índice de conocimiento.
En producción, proteger con API Key o Azure AD (APIM policy).
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import IndexRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index", summary="Indexar un documento en Azure AI Search")
async def index_document(request: Request, body: IndexRequest):
    """
    Genera el embedding del contenido y lo sube al índice vectorial.
    Usar para agregar manuales IT a la base de conocimiento.
    """
    openai_svc = request.app.state.openai_service
    search_svc = request.app.state.search_service

    try:
        embedding = openai_svc.get_embedding(body.document_content)
        search_svc.index_document(
            title=body.document_title,
            content=body.document_content,
            source_file=body.source_file,
            embedding=embedding,
        )
        return {"status": "ok", "message": f"Documento '{body.document_title}' indexado."}
    except Exception as exc:
        logger.exception("Error al indexar: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/create-index", summary="Crear el índice vectorial si no existe")
async def create_index(request: Request):
    """
    Crea el índice en Azure AI Search con configuración HNSW vectorial.
    Solo necesario en el primer despliegue.
    """
    search_svc = request.app.state.search_service
    try:
        search_svc.create_index_if_not_exists()
        return {"status": "ok", "message": "Índice listo."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
