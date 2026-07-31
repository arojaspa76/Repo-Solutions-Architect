# Project:     GenAIDemo
# Component:   Cosmos DB service
# Description: Conversation CRUD against genaidemo-db/conversations (async)
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

DATABASE_NAME = "genaidemo-db"
CONTAINER_NAME = "conversations"


class CosmosRepository:
    """Async CRUD repository for conversation documents in Cosmos DB."""

    def __init__(self, connection_string: str) -> None:
        self.client: CosmosClient = CosmosClient.from_connection_string(connection_string)
        self.container: ContainerProxy = self.client.get_database_client(
            DATABASE_NAME
        ).get_container_client(CONTAINER_NAME)

    async def close(self) -> None:
        """Close the underlying Cosmos client."""
        await self.client.close()

    async def get_conversation(self, conversation_id: str, user_id: str) -> dict | None:
        """Get a conversation by ID. Returns None if not found."""
        try:
            return await self.container.read_item(item=conversation_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return None

    async def list_conversations(
        self, user_id: str, tenant_id: str, limit: int = 50
    ) -> list[dict]:
        """List conversations for a user, ordered by updated_at desc."""
        query = (
            "SELECT * FROM c WHERE c.user_id = @user_id AND c.tenant_id = @tenant_id "
            "ORDER BY c.updated_at DESC OFFSET 0 LIMIT @limit"
        )
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@limit", "value": limit},
        ]
        items = self.container.query_items(query=query, parameters=parameters)
        return [item async for item in items]

    async def upsert_conversation(self, conversation: dict) -> dict:
        """Create or update a conversation document."""
        return await self.container.upsert_item(conversation)

    async def append_message(self, conversation_id: str, user_id: str, message: dict) -> None:
        """Append a message to the conversation's messages array."""
        conversation = await self.get_conversation(conversation_id, user_id)
        if conversation is None:
            raise CosmosResourceNotFoundError(message=f"Conversation {conversation_id} not found")
        conversation["messages"].append(message)
        await self.upsert_conversation(conversation)

    async def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        """Permanently delete a conversation document."""
        await self.container.delete_item(item=conversation_id, partition_key=user_id)

    async def search_conversations(self, user_id: str, query: str, limit: int = 20) -> list[dict]:
        """Full-text search in conversation titles and message content."""
        cosmos_query = (
            "SELECT * FROM c WHERE c.user_id = @user_id AND "
            "(CONTAINS(c.title, @query, true) OR "
            "EXISTS(SELECT VALUE m FROM m IN c.messages WHERE CONTAINS(m.content, @query, true))) "
            "OFFSET 0 LIMIT @limit"
        )
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@query", "value": query},
            {"name": "@limit", "value": limit},
        ]
        items = self.container.query_items(query=cosmos_query, parameters=parameters)
        return [item async for item in items]
