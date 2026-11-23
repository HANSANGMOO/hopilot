import asyncio
import json
from pathlib import Path

import aiofiles

from core.models import Entity, KnowledgeGraph, Relation
from utils import get_logger

logger = get_logger("KnowledgeGraphManager")


class KnowledgeGraphManager:
    """
    KnowledgeGraph의 JSONL 파일 I/O를 담당하는 인프라 클래스.
    path별 Lock으로 concurrent load→save를 직렬화한다.
    """

    def __init__(self) -> None:
        self._locks: dict[Path, asyncio.Lock] = {}

    def lock(self, path: Path) -> asyncio.Lock:
        if path not in self._locks:
            self._locks[path] = asyncio.Lock()
        return self._locks[path]

    async def initialize(self) -> None:
        logger.info("KnowledgeGraphManager initialized.")

    async def shutdown(self) -> None:
        logger.info("KnowledgeGraphManager shutdown.")

    async def load(self, path: Path) -> KnowledgeGraph:
        """JSONL 파일을 읽어 KnowledgeGraph를 복원합니다."""
        if not path.exists():
            return KnowledgeGraph()

        entities: list[Entity] = []
        relations: list[Relation] = []

        async with aiofiles.open(path, encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "entity":
                    entities.append(Entity.model_validate(obj))
                elif obj.get("type") == "relation":
                    relations.append(Relation.model_validate(obj))

        logger.info(f"Loaded {len(entities)} entities, {len(relations)} relations from {path}")
        return KnowledgeGraph(entities=entities, relations=relations)

    async def save(self, graph: KnowledgeGraph, path: Path) -> None:
        """KnowledgeGraph를 JSONL 파일에 씁니다."""
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            for entity in graph.entities:
                row = {"type": "entity", **entity.model_dump()}
                await f.write(json.dumps(row, ensure_ascii=False) + "\n")
            for relation in graph.relations:
                row = {"type": "relation", **relation.model_dump(by_alias=True)}
                await f.write(json.dumps(row, ensure_ascii=False) + "\n")

        logger.info(f"Saved graph to {path}")
