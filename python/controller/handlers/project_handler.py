from pathlib import Path

from contracts.project import (
    ProjectCreateSignal,
    ProjectDeleteSignal,
    ProjectDetailDTO,
    ProjectListSignal,
    ProjectLoadSignal,
    ProjectMetaDTO,
    ProjectUpdateSignal,
)
from core.models import HOProject
from services.context_service import ContextService
from services.project_service import ProjectNotFoundError, ProjectService
from services.session_service import SessionService
from utils import get_logger

logger = get_logger("ProjectHandler")


class ProjectHandler:
    def __init__(self, project_service: ProjectService, session_service: SessionService, context_service: ContextService):
        self.project_service = project_service
        self.session_service = session_service
        self.context_service = context_service

    async def handle_list(self, signal: ProjectListSignal) -> list:
        projects = await self.project_service.list()
        for project in projects:
            self.context_service.register(project.project_id, project.workspace, project.name)
        return [self._to_meta_dto(p).model_dump() for p in projects]

    async def handle_load(self, signal: ProjectLoadSignal) -> dict:
        project = await self.project_service.get(signal.params["project_id"])
        if not project:
            raise ProjectNotFoundError(f"Project {signal.params['project_id']} not found.")
        self.context_service.register(project.project_id, project.workspace, project.name)
        return self._to_detail_dto(project).model_dump()

    async def handle_create(self, signal: ProjectCreateSignal) -> dict:
        project = await self.project_service.create(
            name=signal.params["name"],
            workspace=Path(signal.params["workspace"]),
        )
        self.context_service.register(project.project_id, project.workspace, project.name)
        return self._to_meta_dto(project).model_dump()

    async def handle_update(self, signal: ProjectUpdateSignal) -> dict:
        project_id = signal.params["project_id"]
        patch = signal.params["patch"]

        project = await self.project_service.update(project_id=project_id, patch=patch)
        self.context_service.update(project.project_id, project.workspace, project.name)

        return self._to_meta_dto(project).model_dump()

    async def handle_delete(self, signal: ProjectDeleteSignal) -> dict:
        await self.project_service.delete(signal.params["project_id"])
        self.context_service.unregister(signal.params["project_id"])
        return {}

    # ── DTO 변환 헬퍼 ──────────────────────────────────────────────────────────

    def _to_meta_dto(self, project: HOProject) -> ProjectMetaDTO:
        return ProjectMetaDTO(
            id=project.project_id,
            name=project.name,
            workspace=str(project.workspace),
            updated_at=project.updated_at.isoformat(),
        )

    def _to_detail_dto(self, project: HOProject) -> ProjectDetailDTO:
        return ProjectDetailDTO(
            id=project.project_id,
            name=project.name,
            workspace=str(project.workspace),
            updated_at=project.updated_at.isoformat(),
        )
