import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from api.api_manager import ApiManager
from core.models import ModelInfo, HopilotPayload, HOMessage, HOChunk, TextPayload

# .env 파일 파싱 로직
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../assets/env/api_key.env"))
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")

# 파싱된 환경변수에서 키 가져오기
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

@pytest.mark.asyncio
async def test_gemini_integration():
    if not GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY가 assets/env/api_key.env 파일에 설정되지 않아 건너뜁니다.")

    manager = ApiManager()
    await manager.initialize()

    try:
        model_info = ModelInfo(
            id="gemini-3-flash-preview",
            provider="gemini",
            display_name="Test Gemini",
            api_key=GEMINI_API_KEY
        )

        payload = HopilotPayload(
            system_instructions="",
            messages=[
                HOMessage(
                    role="user",
                    chunks=[HOChunk(payload=TextPayload(text="Hello! Who are you? Please answer in 1 sentence."))]
                )
            ]
        )

        chunks_received = []
        async for chunk in manager.generate_stream(payload, model_info):
            chunks_received.append(chunk)

        assert len(chunks_received) > 0, "스트림에서 아무런 데이터도 받지 못했습니다."
        
        # 텍스트 청크 파싱 검증
        text_chunks = [c for c in chunks_received if c.payload.type == "text"]
        assert len(text_chunks) > 0, "텍스트 페이로드가 포함된 청크가 없습니다."

        full_text = "".join(c.payload.text for c in text_chunks)
        print("\n[Gemini 응답 전문]:", full_text)
        
        # 스트림 종료 마커 검증
        stream_chunks = [c for c in chunks_received if c.payload.type == "stream_end"]
        assert len(stream_chunks) > 0, "스트림 종료(StreamPayload) 청크가 수신되지 않았습니다."
        assert stream_chunks[-1].payload.finish_reason is not None

    finally:
        await manager.shutdown()
