from .types import ClaudePayload


def add_cache_breakpoints(payload: ClaudePayload) -> ClaudePayload:
    """
    Claude prompt caching을 위해 cache_control 마커를 추가합니다.

    [Breakpoint #1] system 프롬프트
    - 모든 요청에서 동일한 prefix → 가장 안정적인 캐시 후보.
    - system을 문자열에서 배열 형식으로 변환하고 cache_control 마킹.

    [Breakpoint #2] 마지막 AI 메시지의 끝
    - 대화 히스토리는 다음 요청에서도 prefix가 동일 → 두 번째 캐시 후보.
    - 마지막 AI 메시지의 마지막 non-thinking 블록에 마커 부착.
    - thinking 블록에는 cache_control 불가 (Anthropic 제약).
    """
    # Breakpoint #1: system
    system = payload.get("system")
    if isinstance(system, str):
        payload["system"] = [{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }]

    # Breakpoint #2: 마지막 AI 메시지
    messages = payload.get("messages", [])
    last_ai_idx = -1
    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant":
            last_ai_idx = i

    if last_ai_idx >= 0:
        blocks = messages[last_ai_idx].get("content", [])
        for block in reversed(blocks):
            if block.get("type") not in ("thinking",):
                block["cache_control"] = {"type": "ephemeral"}
                break

    return payload
