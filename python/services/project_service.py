import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import HOPILOT_DIR_NAME
from core.errors import HopilotError
from core.models import HOProject, KST
from io_.db_manager import DBManager
from utils import get_logger

logger = get_logger("ProjectService")


class ProjectNotFoundError(HopilotError):
    pass


class ProjectService:
    def __init__(self, db_manager: DBManager) -> None:
        self._db = db_manager

    async def create(self, name: str, workspace: Path) -> HOProject:
        project = HOProject(name=name, workspace=workspace)
        await self._db.create("projects", project.to_db_dict())
        logger.info(f"Created project: {project.project_id}")
        return project

    async def get(self, project_id: str) -> Optional[HOProject]:
        row = await self._db.load("projects", project_id)
        if not row:
            return None
        return HOProject.from_db_dict(dict(row))

    async def list(self) -> List[HOProject]:
        rows = await self._db.execute_query(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        )
        return [HOProject.from_db_dict(dict(row)) for row in rows]

    async def update(self, project_id: str, patch: dict) -> HOProject:
        project = await self.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found.")
        if "name" in patch:
            project.name = patch["name"]
        if "workspace" in patch:
            old_workspace = project.workspace
            new_workspace = Path(patch["workspace"])
            self._move_workspace(old_workspace, new_workspace)
            project.workspace = new_workspace
        project.updated_at = datetime.now(KST)
        return await self._commit_workspace(project)

    async def delete(self, project_id: str) -> None:
        await self._db.delete("projects", project_id)
        logger.info(f"Deleted project: {project_id}")

    async def resolve(self, project_id: str | None) -> Optional[HOProject]:
        if not project_id:
            return None
        return await self.get(project_id)

    def _move_workspace(self, old_workspace: Path, new_workspace: Path) -> None:
        old_hopilot_dir = old_workspace / HOPILOT_DIR_NAME
        new_hopilot_dir = new_workspace / HOPILOT_DIR_NAME
        if old_hopilot_dir.exists():
            shutil.move(str(old_hopilot_dir), str(new_hopilot_dir))

    async def _commit_workspace(self, project: HOProject) -> HOProject:
        project.workspace.mkdir(parents=True, exist_ok=True)
        await self._db.save("projects", project.project_id, project.to_db_dict())
        return project
