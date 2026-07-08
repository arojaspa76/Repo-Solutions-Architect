"""
services/search_service.py
===========================
Gestiona el índice vectorial en Azure AI Search.
Soporta:
  - Búsqueda vectorial pura (cosine similarity sobre embeddings)
  - Búsqueda híbrida (vectorial + BM25 keyword)
  - Indexación de nuevos documentos

Variables de entorno requeridas:
  AZURE_SEARCH_ENDPOINT  — ej: https://srch-techcorp.search.windows.net
  AZURE_SEARCH_KEY       — Admin key del recurso
  AZURE_SEARCH_INDEX     — Nombre del índice, ej: knowledge-base
"""

import os
import logging
import uuid
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


class SearchService:
    """Cliente para Azure AI Search con soporte vectorial."""

    def __init__(self):
        endpoint   = os.environ["AZURE_SEARCH_ENDPOINT"]
        key        = os.environ["AZURE_SEARCH_KEY"]
        self.index = os.getenv("AZURE_SEARCH_INDEX", "knowledge-base")

        credential = AzureKeyCredential(key)
        self.client = SearchClient(
            endpoint=endpoint,
            index_name=self.index,
            credential=credential,
        )
        self.index_client = SearchIndexClient(
            endpoint=endpoint,
            credential=credential,
        )
        logger.info("SearchService inicializado. Índice=%s", self.index)

    def create_index_if_not_exists(self):
        """
        Crea el índice vectorial en Azure AI Search si aún no existe.
        Se llama durante la inicialización del servicio admin.
        """
        existing = [i.name for i in self.index_client.list_indexes()]
        if self.index in existing:
            logger.info("Índice '%s' ya existe.", self.index)
            return

        index_definition = SearchIndex(
            name=self.index,
            fields=[
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                ),
                SearchableField(
                    name="title",
                    type=SearchFieldDataType.String,
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                ),
                SimpleField(
                    name="source_file",
                    type=SearchFieldDataType.String,
                    filterable=True,
                ),
                SearchField(
                    name="contentVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="techcorp-hnsw-profile",
                ),
            ],
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="techcorp-hnsw",
                        parameters={"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"},
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="techcorp-hnsw-profile",
                        algorithm_configuration_name="techcorp-hnsw",
                    )
                ],
            ),
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="techcorp-semantic",
                        prioritized_fields=SemanticPrioritizedFields(
                            content_fields=[SemanticField(field_name="content")],
                            keywords_fields=[SemanticField(field_name="title")],
                        ),
                    )
                ]
            ),
        )
        self.index_client.create_index(index_definition)
        logger.info("Índice '%s' creado exitosamente.", self.index)

    def vector_search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        Búsqueda vectorial pura usando cosine similarity.

        Args:
            query_embedding: Vector de 1536 dimensiones de la pregunta del usuario.
            top_k:           Número de resultados a retornar.

        Returns:
            Lista de diccionarios con title, content, source_file, score.
        """
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="contentVector",
        )

        results = self.client.search(
            search_text=None,        # Solo búsqueda vectorial
            vector_queries=[vector_query],
            select=["id", "title", "content", "source_file"],
            top=top_k,
        )

        documents = []
        for r in results:
            documents.append({
                "title":       r["title"],
                "content":     r["content"],
                "source_file": r["source_file"],
                "score":       r.get("@search.score", 0.0),
            })

        logger.info("Búsqueda vectorial: %d resultados encontrados.", len(documents))
        return documents

    def index_document(self, title: str, content: str, source_file: str, embedding: list[float]):
        """
        Indexa un nuevo fragmento de documento en Azure AI Search.
        """
        doc = {
            "id":            str(uuid.uuid4()),
            "title":         title,
            "content":       content,
            "source_file":   source_file,
            "contentVector": embedding,
        }
        self.client.upload_documents(documents=[doc])
        logger.info("Documento indexado: '%s'", title)
