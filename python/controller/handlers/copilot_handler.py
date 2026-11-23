from typing import AsyncGenerator

from contracts.copilot import CopilotRunStreamDTO, CopilotRunStreamSignal
from core.models import CopilotInput, ToolParameters
from services.attachment_service import AttachmentService
from services.context_service import ContextService
from services.copilot_service import CopilotService
from services.llm_model_service import LlmModelService
from services.session_service import SessionService
from services.tool_service import ToolService
from utils import get_logger

logger = get_logger("CopilotHandler")


class CopilotHandler:
    def __init__(
        self,
        copilot_service: CopilotService,
        session_service: SessionService,
        llm_model_service: LlmModelService,
        attachment_service: AttachmentService,
        context_service: ContextService,
        tool_service: ToolService,
    ):
        self.copilot_service = copilot_service
        self.session_service = session_service
        self.llm_model_service = llm_model_service
        self.attachment_service = attachment_service
        self.context_service = context_service
        self.tool_service = tool_service

    async def handle_user_request(self, signal: CopilotRunStreamSignal) -> AsyncGenerator[CopilotRunStreamDTO, None]:
        params         = signal.params or {}
        ask            = params.get("query", "")
        session_id     = params.get("session_id")
        model_id       = params.get("model_id")
        project_id     = params.get("project_id")
        attachment_ids = params.get("attachment_ids", [])
        tool_ids       = params.get("tool_ids", [])

        logger.info(f"Processing user request: '{ask}' for session {session_id}, project_id={project_id}")

        session     = await self.session_service.resolve(session_id)
        model_info  = self.llm_model_service.resolve(model_id)
        attachments = await self.attachment_service.resolve(attachment_ids)
        context     = self.context_service.resolve(project_id)
        tool_params = ToolParameters(kg_jsonl_path=context.dynamic)
        tool_set    = self.tool_service.resolve(tool_ids, params=tool_params)

        input_dto = CopilotInput(
            session=session, ask=ask, model=model_info,
            attachments=attachments or None,
            tool_set=tool_set,
            context=context,
        )

        try:
            async for chunk in self.copilot_service.process_user_request(input_dto):
                yield chunk
        finally:
            await self.session_service.commit_session(session.session_id)
