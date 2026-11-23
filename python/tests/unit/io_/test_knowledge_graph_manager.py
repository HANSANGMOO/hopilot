import asyncio
import json
import pytest

from core.models import Entity, Relation
from io_.knowledge_graph_manager import KnowledgeGraphManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def kg_jsonl(tmp_path):
    path = tmp_path / "dynamic.jsonl"
    rows = [
        {"type": "entity", "id": "ent_00000001", "name": "Alice", "entityType": "person", "observations": []},
        {"type": "entity", "id": "ent_00000002", "name": "Bob",   "entityType": "person", "observations": []},
        {"type": "relation", "id": "rel_00000001", "from": "Alice", "to": "Bob", "relationType": "knows"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


# ── Tests ─────────────────────────────────────────────────────────────────────

class DescribeKnowledgeGraphManager:
    class DescribeLoad:
        @pytest.mark.anyio(backend="asyncio")
        async def it_loads_entities_from_jsonl(self, kg_jsonl):
            manager = KnowledgeGraphManager()
            graph = await manager.load(kg_jsonl)

            assert len(graph.entities) == 2
            assert graph.entities[0].name == "Alice"
            assert graph.entities[1].name == "Bob"

        @pytest.mark.anyio(backend="asyncio")
        async def it_loads_relations_from_jsonl(self, kg_jsonl):
            manager = KnowledgeGraphManager()
            graph = await manager.load(kg_jsonl)

            assert len(graph.relations) == 1
            assert graph.relations[0].from_ == "Alice"
            assert graph.relations[0].to == "Bob"

        @pytest.mark.anyio(backend="asyncio")
        async def it_returns_empty_graph_when_file_not_found(self, tmp_path):
            manager = KnowledgeGraphManager()
            graph = await manager.load(tmp_path / "nonexistent.jsonl")

            assert graph.entities == []
            assert graph.relations == []

    class DescribeSave:
        @pytest.mark.anyio(backend="asyncio")
        async def it_saves_graph_to_jsonl(self, tmp_path):
            path = tmp_path / "dynamic.jsonl"
            manager = KnowledgeGraphManager()
            graph = await manager.load(path)
            graph.add_entities([Entity(name="Alice", entityType="person")])
            graph.add_relations([Relation(**{"from": "Alice", "to": "Bob", "relationType": "knows"})])

            await manager.save(graph, path)

            lines = path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["type"] == "entity"
            assert json.loads(lines[1])["type"] == "relation"

        @pytest.mark.anyio(backend="asyncio")
        async def it_saves_both_entities_on_concurrent_request(self, tmp_path):
            path = tmp_path / "dynamic.jsonl"
            manager = KnowledgeGraphManager()

            async def add_entity(name):
                async with manager.lock(path):
                    graph = await manager.load(path)
                    graph.add_entities([Entity(name=name, entityType="person")])
                    await manager.save(graph, path)

            task1 = asyncio.create_task(add_entity("Alice"))
            task2 = asyncio.create_task(add_entity("Bob"))
            await asyncio.gather(task1, task2)

            final = await manager.load(path)
            assert len(final.entities) == 2