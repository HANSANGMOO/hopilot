import json
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from core.models import BaseTool, Entity, Relation, ToolSchema
from io_.knowledge_graph_manager import KnowledgeGraphManager


class CreateEntitiesInput(BaseModel):
    entities: List[Entity] = Field(..., description="List of entities to create.")


class DeleteEntitiesInput(BaseModel):
    ids: List[str] = Field(..., description="List of entity IDs to delete.")


class AddObservationsInput(BaseModel):
    entity_id: str = Field(..., description="ID of the entity to add observations to.")
    observations: List[str] = Field(..., description="List of observations to add.")


class DeleteObservationsInput(BaseModel):
    entity_id: str = Field(..., description="ID of the entity to delete observations from.")
    observations: List[str] = Field(..., description="List of observations to delete.")


class SearchNodesInput(BaseModel):
    query: str = Field(..., description="Search query to match against entity name, type, and observations.")


class OpenNodesInput(BaseModel):
    names: List[str] = Field(..., description="List of entity names to retrieve.")


class CreateRelationsInput(BaseModel):
    relations: List[Relation] = Field(..., description="List of relations to create.")


class DeleteRelationsInput(BaseModel):
    ids: List[str] = Field(..., description="List of relation IDs to delete.")


class ReadGraphInput(BaseModel):
    pass


# ── Tools ─────────────────────────────────────────────────────────────────────

class ReadGraphTool(BaseTool):
    id = "read_graph"
    name = "read_graph"
    description = "Read the entire knowledge graph, returning all entities and relations."
    input_schema = ReadGraphInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        graph = await self._kg.load(path)
        return graph.model_dump_json(by_alias=True)


class CreateEntitiesTool(BaseTool):
    id = "create_entities"
    name = "create_entities"
    description = "Create new entities in the knowledge graph. Existing entities (by ID) are skipped."
    input_schema = CreateEntitiesInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, entities: List[dict], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            new_items = graph.add_entities([Entity.model_validate(e) for e in entities])
            await self._kg.save(graph, path)
        return json.dumps([e.model_dump() for e in new_items], ensure_ascii=False)


class DeleteEntitiesTool(BaseTool):
    id = "delete_entities"
    name = "delete_entities"
    description = "Delete entities by ID. Also removes all relations involving those entities."
    input_schema = DeleteEntitiesInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, ids: List[str], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            graph.remove_entities(ids)
            await self._kg.save(graph, path)
        return json.dumps({"deleted": ids}, ensure_ascii=False)


class AddObservationsTool(BaseTool):
    id = "add_observations"
    name = "add_observations"
    description = "Add observations to an existing entity. Duplicate observations are skipped."
    input_schema = AddObservationsInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, entity_id: str, observations: List[str], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            entity = graph.resolve_entity(entity_id)
            entity.add_observations(observations)
            await self._kg.save(graph, path)
        return entity.model_dump_json()


class DeleteObservationsTool(BaseTool):
    id = "delete_observations"
    name = "delete_observations"
    description = "Delete specific observations from an entity."
    input_schema = DeleteObservationsInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, entity_id: str, observations: List[str], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            entity = graph.resolve_entity(entity_id)
            entity.remove_observations(observations)
            await self._kg.save(graph, path)
        return entity.model_dump_json()


class SearchNodesTool(BaseTool):
    id = "search_nodes"
    name = "search_nodes"
    description = "Search entities by matching query against name, entityType, and observations."
    input_schema = SearchNodesInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, query: str, **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        graph = await self._kg.load(path)
        return json.dumps([e.model_dump() for e in graph.search_nodes(query)], ensure_ascii=False)


class OpenNodesTool(BaseTool):
    id = "open_nodes"
    name = "open_nodes"
    description = "Retrieve entities by their names."
    input_schema = OpenNodesInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, names: List[str], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        graph = await self._kg.load(path)
        return json.dumps([e.model_dump() for e in graph.open_nodes(names)], ensure_ascii=False)


class CreateRelationsTool(BaseTool):
    id = "create_relations"
    name = "create_relations"
    description = "Create new relations between entities. Existing relations (by ID) are skipped."
    input_schema = CreateRelationsInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, relations: List[dict], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            new_items = graph.add_relations([Relation.model_validate(r) for r in relations])
            await self._kg.save(graph, path)
        return json.dumps([r.model_dump(by_alias=True) for r in new_items], ensure_ascii=False)


class DeleteRelationsTool(BaseTool):
    id = "delete_relations"
    name = "delete_relations"
    description = "Delete relations by ID."
    input_schema = DeleteRelationsInput
    dependencies = [KnowledgeGraphManager]
    required_kwargs = ["kg_jsonl_path"]

    def __init__(self, kg_manager: KnowledgeGraphManager) -> None:
        self._kg = kg_manager

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.input_schema.model_json_schema())

    async def execute(self, ids: List[str], **kwargs) -> str:
        path: Path = kwargs.get("kg_jsonl_path")
        async with self._kg.lock(path):
            graph = await self._kg.load(path)
            graph.remove_relations(ids)
            await self._kg.save(graph, path)
        return json.dumps({"deleted": ids}, ensure_ascii=False)
