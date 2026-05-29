import json
from utils import get_logger

logger = get_logger("CopilotHandler")

class CopilotHandler:
    async def handle_message(self, raw_text: str) -> dict:
        """프레임워크 종속성이 전혀 없는 순수 파이썬 로직"""
        try:
            request_data = json.loads(raw_text)
            user_message = request_data.get("message", "내용 없음")
            
            logger.info(f"Processing user message: {user_message}")
            
            # 임시 에코 응답 (추후 EventBus와 DTO 로직이 들어갈 자리)
            return {"type": "ECHO", "content": f"처리 완료: {user_message}"}
        except json.JSONDecodeError:
            logger.error(f"Received invalid JSON format: {raw_text}")
            return {"type": "ERROR", "content": "잘못된 JSON 형식입니다."}
