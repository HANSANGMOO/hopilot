import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional
from core.models import HOSession, HOMessage
from db.db_manager import DBManager

logger = logging.getLogger(__name__)

class SessionService:
    """
    Session 상태 관리 및 DB 영속성을 담당하는 비동기 서비스 계층.
    비동기 환경에서의 동시성 문제를 해결하기 위해 active_sessions 딕셔너리로 상태를 관리합니다.
    """
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        # [완료된 상태] 활성화되어 메모리에 올라간 세션들
        self.active_sessions: Dict[str, HOSession] = {}
        # [대기 상태] 현재 DB에서 불러오고 있어 곧 활성화될 세션들 (동시성 충돌 방지용)
        self._pending_sessions: Dict[str, asyncio.Task] = {}
        
    async def create_session(self, title: str = "New Session") -> HOSession:
        """새로운 세션을 생성하고, 메모리에 올린 뒤 DB에 저장합니다."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        session = HOSession(session_id=session_id, title=title)
        
        # 메모리에 적재
        self.active_sessions[session_id] = session
        
        # DB에 초기 상태 저장
        await self.db.create("sessions", session.to_db_dict())
        logger.info(f"Created new session: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[HOSession]:
        """
        메모리에서 먼저 세션을 찾고, 없으면 DB에서 불러옵니다.
        동시성 문제(Cache Stampede)를 막기 위해 Promise(Task) Caching 패턴을 사용합니다.
        """
        # 1. 이미 완성된 세션이 메모리에 있는지 확인
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
            
        # 2. 누군가 이미 DB에서 불러오고 있는지 확인 (대기열에 합류)
        if session_id in self._pending_sessions:
            return await self._pending_sessions[session_id]
            
        # 3. 아무도 가져오고 있지 않다면, 직접 로딩 작업을 시작하고 전광판(_pending_sessions)에 등록
        pending_task = asyncio.create_task(self._load_session(session_id))
        self._pending_sessions[session_id] = pending_task
        
        # 4. 작업이 완료될 때까지 대기
        return await pending_task

    async def _load_session(self, session_id: str) -> Optional[HOSession]:
        """실제 DB에 접근하여 데이터를 가져오고 객체를 조립하는 내부 함수입니다."""
        try:
            row = await self.db.load("sessions", session_id)
            if not row:
                return None
                
            session = HOSession.from_db_dict(dict(row))
            self.active_sessions[session_id] = session
            return session
        finally:
            # 작업이 끝나면(성공하든 에러가 나든) 진행 중 목록에서 반드시 제거
            if session_id in self._pending_sessions:
                del self._pending_sessions[session_id]

    async def update_title(self, session_id: str, new_title: str):
        """세션의 제목을 변경하고 즉시 커밋합니다."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
            
        session.title = new_title
        session.updated_at = datetime.utcnow()
        await self.commit_session(session_id)

    async def add_message(self, session_id: str, message: HOMessage):
        """
        스트리밍 중 발생하는 중간 메시지들을 메모리의 active_session에만 일단 추가(버퍼링)합니다.
        React 사이클 도중 성능 저하를 막기 위해 매번 DB에 저장하지 않습니다.
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")
            
        session.messages.append(message)
        session.updated_at = datetime.utcnow()
        logger.debug(f"Added message to session {session_id} in memory.")

    async def commit_session(self, session_id: str):
        """
        메모리에 모아둔(버퍼링된) 해당 세션의 최종 상태를 DB에 영구 저장(Flush)합니다.
        React cycle이 끝나는 시점에 호출되어야 합니다.
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} is not active in memory to commit.")
            return
            
        session = self.active_sessions[session_id]
        await self.db.save("sessions", session_id, session.to_db_dict())
        logger.info(f"Committed session {session_id} to DB.")

    async def deactivate_session(self, session_id: str):
        """
        사용자가 다른 채팅방으로 이동하거나 창을 닫을 때, 메모리 누수를 막기 위해
        active_sessions 맵에서 해당 세션을 제거(GC)합니다.
        """
        if session_id in self.active_sessions:
            await self.commit_session(session_id)
            del self.active_sessions[session_id]
            logger.debug(f"Session {session_id} deactivated and removed from memory.")

    async def delete_session(self, session_id: str):
        """메모리와 DB 양쪽에서 세션을 완전히 삭제합니다."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
        await self.db.delete("sessions", session_id)
        logger.info(f"Session {session_id} fully deleted.")
