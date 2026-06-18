from typing import Any, Dict, List, Literal, Optional, TypedDict

from api.provider.base_provider import BaseProvider
from core.models import (
    HOChunk,
    HopilotPayload,
    StreamPayload,
    TextPayload,
    ThoughtPayload,
    ToolCallPayload,
)
from utils import get_logger

logger = get_logger("GeminiProvider")

GEMINI_THOUGHT_SIGNATURE = "thoughtSignature"


# --- Gemini Request TypedDicts ---
class GeminiFunctionCall(TypedDict, total=False):
    name: str
    args: Dict[str, Any]
    id: str


class GeminiFunctionResponse(TypedDict, total=False):
    name: str
    response: Any
    id: str


class GeminiPart(TypedDict, total=False):
    text: str
    thought: bool
    functionCall: GeminiFunctionCall
    functionResponse: GeminiFunctionResponse
    thoughtSignature: str
    # inlineData: dict (이미지용, 필요 시 확장)


class GeminiContent(TypedDict):
    role: Literal["user", "model"]
    parts: List[GeminiPart]


class GeminiSystemInstruction(TypedDict):
    parts: List[GeminiPart]


class GeminiThinkingConfig(TypedDict):
    thinkingLevel: str


class GeminiGenerationConfig(TypedDict, total=False):
    temperature: float
    thinkingConfig: GeminiThinkingConfig


class GeminiPayload(TypedDict, total=False):
    systemInstruction: GeminiSystemInstruction
    contents: List[GeminiContent]
    tools: List[Dict[str, Any]]
    generationConfig: GeminiGenerationConfig


# ---------------------------------


class GeminiProvider(BaseProvider, provider="gemini"):
    """
    Google Gemini REST API 공급자 구현체입니다.
    """

    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)

    def build_url(self) -> str:
        """Gemini SSE 스트리밍을 위한 엔드포인트 URL 생성 (alt=sse 필수)"""
        base = self.base_url.rstrip("/")
        return f"{base}/{self.model}:streamGenerateContent?alt=sse"

    def build_headers(self) -> Dict[str, str]:
        """Gemini API 인증 및 컨텐츠 타입 헤더 생성"""
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def format_payload(self, payload: HopilotPayload) -> GeminiPayload:
        """HopilotPayload를 Gemini의 contents/parts 구조로 변환합니다."""
        gemini_request: GeminiPayload = {}

        # 1. System Instruction
        if payload.system_instructions:
            gemini_request["systemInstruction"] = {"parts": [{"text": payload.system_instructions}]}

        # 2. Contents 구성
        contents: List[GeminiContent] = []
        for msg in payload.messages:
            if msg.role == "system":
                continue  # System prompt는 위에서 별도 처리됨

            gemini_role: Literal["user", "model"] = "model" if msg.role == "ai" else "user"
            parts: List[GeminiPart] = []

            for chunk in msg.chunks:
                part = self._format_chunk(chunk)
                if part:
                    parts.append(part)

            if parts:
                contents.append({"role": gemini_role, "parts": parts})

        gemini_request["contents"] = contents

        # 3. Tools 맵핑 (Context에 도구 명세가 있다면 추가)
        if payload.context and "tools" in payload.context:
            gemini_request["tools"] = payload.context["tools"]

        # 4. Generation Config (기본값)
        gemini_request["generationConfig"] = {
            "temperature": 1.0,
            # "thinkingConfig": {"thinkingLevel": "low"}  # 필요 시 활성화
        }

        return gemini_request

    def _format_chunk(self, chunk: HOChunk) -> GeminiPart:
        part: GeminiPart = {}
        payload = chunk.payload

        # Payload 타입별 매핑
        if payload.type == "text":
            part["text"] = payload.text
        elif payload.type == "thought":
            part["text"] = payload.thought
            part["thought"] = True
        elif payload.type == "tool_call":
            call_id = payload.model_extra.get("id") if payload.model_extra else None
            part["functionCall"] = {
                "name": payload.tool_name,
                "args": payload.tool_args,
            }
            if call_id:
                part["functionCall"]["id"] = call_id
        elif payload.type == "tool_output":
            output_id = payload.model_extra.get("id") if payload.model_extra else None
            # Gemini는 response에 객체 형태(Dict)를 요구합니다.
            part["functionResponse"] = {
                "name": payload.tool_name,
                "response": {"result": payload.output},
            }
            if output_id:
                part["functionResponse"]["id"] = output_id

        # 생각 서명(Thought Signature) 복원 로직
        if payload.model_extra and GEMINI_THOUGHT_SIGNATURE in payload.model_extra:
            part["thoughtSignature"] = payload.model_extra[GEMINI_THOUGHT_SIGNATURE]

        return part

    def parse_sse_event(self, event_line: str) -> List[HOChunk]:
        """Gemini SSE 문자열 파싱 및 변환"""
        line = event_line.strip()
        if not line or not line.startswith("data: "):
            return []

        data_str = line[len("data: ") :].strip()

        # Gemini API는 스트림 종료 시 빈 라인이나 특수한 마커를 보낼 수 있습니다.
        if not data_str or data_str == "[DONE]":
            return []

        try:
            import json

            data = json.loads(data_str)
            return self._parse_chunk(data)
        except Exception:
            return []

    def _parse_chunk(self, data: Dict[str, Any]) -> List[HOChunk]:
        """Gemini JSON 딕셔너리를 파싱하여 HOChunk 객체 리스트로 변환"""

        if "candidates" not in data or not data["candidates"]:
            return []
            
        candidate = data["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        
        chunks: List[HOChunk] = []
        
        for part in parts:
            payload = None
            extra = {}
            
            # thoughtSignature 복원 및 저장 준비
            if "thoughtSignature" in part:
                extra[GEMINI_THOUGHT_SIGNATURE] = part["thoughtSignature"]

            # TextPayload
            if "text" in part:
                if part.get("thought") is True:
                    payload = ThoughtPayload(thought=part["text"], **extra)
                else:
                    payload = TextPayload(text=part["text"], **extra)
                    
            # ToolCallPayload
            elif "functionCall" in part:
                call = part["functionCall"]
                if "id" in call:
                    extra["id"] = call["id"]
                payload = ToolCallPayload(
                    tool_name=call.get("name", ""),
                    tool_args=call.get("args", {}),
                    **extra
                )
                    
            if payload:
                chunks.append(HOChunk(payload=payload))
                    
        # 2. Finish Reason 확인 (스트림 종료)
        finish_reason = candidate.get("finishReason")
        if finish_reason:
            chunks.append(HOChunk(payload=StreamPayload(finish_reason=finish_reason)))
        
        return chunks
