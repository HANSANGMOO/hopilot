from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class HttpRequestSpec(BaseModel):
    """
    ApiManager가 httpx 클라이언트를 통해 통신할 
    최종 HTTP 네트워크 요청 명세(Specification)입니다.
    """
    method: str = Field(default="POST", description="HTTP 메서드 (예: POST)")
    url: str = Field(..., description="API 엔드포인트 URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP 요청 헤더")
    json_body: Any = Field(default=None, description="HTTP Body에 담길 JSON 페이로드")
