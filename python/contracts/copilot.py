from core.event_bus import BaseEvent
from core.models import HOChunk

class ChunkGenerationEvent(BaseEvent):
    """
    LLM의 스트리밍 청크가 생성되었을 때 발생하는 이벤트입니다.
    """
    chunk: HOChunk
    msg_id: str
    session_id: str

