from pathlib import Path

import yaml

from config import HOPILOT_DIR_NAME
from core.models import ContextDTO, ContextPaths
from utils import get_logger

logger = get_logger("ContextService")

_STATIC_TEMPLATE_PATH = Path(__file__).parent.parent / "template" / "static_template.yaml"


class ContextService:

    def __init__(self, default: ContextPaths) -> None:
        self._default = default
        self._registry: dict[str, ContextPaths] = {}

    def register(self, project_id: str, workspace: Path, name: str) -> None:
        paths = self._build_context_paths(workspace)
        static_context_path = paths.static
        dynamic_context_path = paths.dynamic

        static_context_path.parent.mkdir(parents=True, exist_ok=True)
        if not static_context_path.exists():
            self._scaffold_static(static_context_path, name, workspace)
        dynamic_context_path.touch(exist_ok=True)
        self._registry[project_id] = paths
        logger.info(f"Registered context for project '{project_id}'")

    def update(self, project_id: str, workspace: Path, name: str) -> None:
        old_paths = self._registry.get(project_id)
        new_paths = self._build_context_paths(workspace)

        if old_paths and old_paths.static != new_paths.static:
            self.unregister(project_id)
            self.register(project_id, workspace, name)

        if new_paths.static.exists():
            data = yaml.safe_load(new_paths.static.read_text(encoding="utf-8")) or {}
            data["name"] = name
            data["workspace"] = str(workspace)
            new_paths.static.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )

    def unregister(self, project_id: str) -> None:
        removed = self._registry.pop(project_id, None)
        if removed is None:
            logger.warning(f"Tried to unregister unknown project '{project_id}'")
            return
        logger.info(f"Unregistered context for project '{project_id}'")

    def resolve(self, project_id: str | None = None) -> ContextDTO:
        paths = self._registry.get(project_id) if project_id else None
        if project_id and paths is None:
            logger.warning(f"Tried to resolve unregistered project '{project_id}'")
        logger.debug(f"[resolve] project_id={project_id}, paths={paths}, registry={list(self._registry.keys())}")

        static = ""
        if self._default.static.exists():
            static = self._default.static.read_text(encoding="utf-8").strip()

        if paths and paths.static.exists():
            project_data = yaml.safe_load(paths.static.read_text(encoding="utf-8")) or {}
            project_static = self._render_static(project_data)
            if project_static:
                static = f"{static}\n\n{project_static}".strip()

        return ContextDTO(static=static, dynamic=paths.dynamic if paths else self._default.dynamic)

    @staticmethod
    def _build_context_paths(workspace: Path) -> ContextPaths:
        ctx_dir = workspace / HOPILOT_DIR_NAME / "context"
        return ContextPaths(static=ctx_dir / "static.yaml", dynamic=ctx_dir / "dynamic.jsonl")

    @staticmethod
    def _scaffold_static(path: Path, name: str, workspace: Path) -> None:
        with open(_STATIC_TEMPLATE_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["name"] = name
        data["workspace"] = str(workspace)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _render_static(data: dict) -> str:
        filtered = {k: v for k, v in data.items() if v}
        return yaml.safe_dump(filtered, allow_unicode=True, sort_keys=False).strip()
