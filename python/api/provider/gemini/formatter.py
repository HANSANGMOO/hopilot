import logging
from typing import Iterator, List, Literal

from core.models import HOChunk, HopilotPayload, ToolOutputPayload

logger = logging.getLogger("GeminiFormatter")

from .types import (
    GEMINI_THOUGHT_SIGNATURE,
    GeminiContent,
    GeminiFunctionDeclaration,
    GeminiGenerationConfig,
    GeminiPayload,
    GeminiPart,
    GeminiTool,
)


def format_payload(payload: HopilotPayload, config: GeminiGenerationConfig) -> GeminiPayload:
    """HopilotPayload를 Gemini의 contents/parts 구조로 변환합니다."""
    gemini_payload: GeminiPayload = {}

    # 1. System Instruction
    if payload.context.system_instructions:
        gemini_payload["systemInstruction"] = {"parts": [{"text": payload.context.system_instructions}]}

    # 2. Contents 구성
    all_contents = [
        *_format_messages(payload.memory),
        *_format_messages(payload.query),
    ]

    # Gemini API는 요청의 마지막이 model turn으로 끝나는 것을 허용하지 않음 (400 에러 방지)
    while all_contents and all_contents[-1].get("role") == "model":
        all_contents.pop()

    gemini_payload["contents"] = all_contents

    # 3. Tools 맵핑
    logger.info(f"[GeminiFormatter] payload.tools({len(payload.tools)}): {[t.name for t in payload.tools]}")
    if payload.tools:
        gemini_payload["tools"] = _format_tool_declarations(payload.tools)

    # 4. Generation Config
    gemini_payload["generationConfig"] = config

    return gemini_payload


def _format_messages(messages) -> List[GeminiContent]:
    """HOMessage 리스트를 Gemini contents 배열로 변환합니다.
    Gemini API 스펙: functionResponse 턴에는 inlineData를 함께 담을 수 없으므로,
    도구 실행 결과에 미디어(media)가 포함된 경우 독립된 후속 user 턴으로 분리하여 전달합니다.
    """
    contents: List[GeminiContent] = []
    for msg in messages:
        if msg.role == "system":
            continue
        gemini_role: Literal["user", "model"] = "model" if msg.role == "ai" else "user"
        ##TODO 리팩토링 필요
        main_parts: List[GeminiPart] = []
        followup_media_parts: List[GeminiPart] = []

        for chunk in msg.chunks:
            p = chunk.payload
            if isinstance(p, ToolOutputPayload) and p.media:
                # 1. 도구 실행 결과 응답 (FunctionResponse)
                output_text = p.output or "success"
                main_parts.append({
                    "functionResponse": {
                        "name": p.tool_name,
                        "response": {"result": output_text},
                    }
                })
                # 2. 미디어 바이너리는 후속 턴을 위해 분리 수집 (data가 유효한 경우)
                for item in p.media:
                    if item.data:
                        followup_media_parts.append({
                            "inlineData": {
                                "mimeType": item.mime_type or "image/jpeg",
                                "data": item.data,
                            }
                        })
            else:
                main_parts.extend(_format_chunk(chunk))

        if main_parts:
            contents.append({"role": gemini_role, "parts": main_parts})

        # 도구 결과로 반환된 미디어가 있으면 바로 뒤에 독립된 user 턴으로 이미지 전달
        if followup_media_parts:
            contents.append({"role": "user", "parts": followup_media_parts})

    return contents


def _format_chunk(chunk: HOChunk) -> Iterator[GeminiPart]:
    """단일 HOChunk를 0개 이상의 Gemini 요청 파트로 배출합니다."""
    payload = chunk.payload

    if payload.type == "text":
        yield {"text": payload.text}

    elif payload.type == "thought":
        yield {"text": payload.thought, "thought": True}

    elif payload.type == "tool_call":
        part: GeminiPart = {
            "functionCall": {
                "name": payload.tool_name,
                "args": payload.tool_args,
            }
        }
        if payload.model_extra and GEMINI_THOUGHT_SIGNATURE in payload.model_extra:
            part["thoughtSignature"] = payload.model_extra[GEMINI_THOUGHT_SIGNATURE]
        yield part

    elif payload.type == "tool_output":
        output = payload.output
        if payload.truncated:
            output += "\n[결과가 너무 길어 잘렸습니다. 더 좁은 범위로 재시도하거나 다른 방법을 사용하세요.]"
        yield {
            "functionResponse": {
                "name": payload.tool_name,
                "response": {"result": output or "success"},
            }
        }

    elif payload.type == "image":
        if payload.data is not None:
            yield {
                "inlineData": {
                    "mimeType": payload.mime_type or "image/jpeg",
                    "data": payload.data,
                }
            }

    elif payload.type == "document":
        if payload.data is not None:
            if payload.encoding == "base64":
                yield {
                    "inlineData": {
                        "mimeType": payload.mime_type or "application/octet-stream",
                        "data": payload.data,
                    }
                }
            else:
                yield {"text": payload.data}


def _format_tool_declarations(tools) -> List[GeminiTool]:
    """ToolSchema 리스트를 Gemini functionDeclarations 구조로 변환합니다."""
    declarations: List[GeminiFunctionDeclaration] = [
        GeminiFunctionDeclaration(
            name=t.name,
            description=t.description,
            parameters=_sanitize_schema(t.parameters),
        )
        for t in tools
    ]
    return [GeminiTool(functionDeclarations=declarations)]


_GEMINI_ALLOWED_SCHEMA_KEYS = {"type", "properties", "required", "description", "enum", "items", "nullable", "anyOf"}


def _sanitize_schema(schema: dict) -> dict:
    """Gemini가 허용하지 않는 JSON Schema 필드($schema, title, $defs 등)를 재귀적으로 제거합니다."""
    result = {}
    for key, value in schema.items():
        if key not in _GEMINI_ALLOWED_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            result[key] = {k: _sanitize_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            result[key] = _sanitize_schema(value)
        elif key == "anyOf" and isinstance(value, list):
            result[key] = [_sanitize_schema(v) if isinstance(v, dict) else v for v in value]
        elif key == "type" and isinstance(value, list):
            non_null_types = [v for v in value if v != "null"]
            result[key] = non_null_types[0] if non_null_types else value[0]
            if "null" in value:
                result["nullable"] = True
        else:
            result[key] = value

    if result.get("type") == "array" and "items" not in result:
        result["items"] = {"type": "string"}

    return result
