import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DBManager:
    """
    데이터베이스 연결, 트랜잭션 관리 및 쿼리 실행을 담당하는 인프라 클래스.
    """
    def __init__(self, db_path: str = "hopilot.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    def get_connection(self) -> sqlite3.Connection:
        """새로운 데이터베이스 연결을 반환합니다."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        return conn

    def init_db(self):
        """애플리케이션 초기화 시 호출되어 필요한 테이블을 생성합니다."""
        logger.info("Initializing database...")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 기본 세션 테이블 예시
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        logger.info("Database initialized successfully.")

    def create(self, table: str, data: Dict[str, Any]) -> int:
        """
        새로운 레코드를 생성(INSERT)합니다.
        
        Args:
            table: 데이터를 추가할 테이블 이름
            data: 컬럼명과 값을 매핑한 딕셔너리
            
        Returns:
            생성된 레코드의 기본 키(Primary Key) id 또는 행(row) ID
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid

    def load(self, table: str, record_id: str, id_column: str = "id") -> Optional[sqlite3.Row]:
        """
        특정 ID의 레코드를 로드(SELECT)합니다.
        
        Returns:
            레코드 데이터를 담은 sqlite3.Row 객체 (존재하지 않으면 None)
        """
        query = f"SELECT * FROM {table} WHERE {id_column} = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (record_id,))
            return cursor.fetchone()

    def save(self, table: str, record_id: str, data: Dict[str, Any], id_column: str = "id") -> int:
        """
        기존 레코드를 업데이트(UPDATE)하여 저장합니다.
        
        Returns:
            업데이트된 행(Row)의 수
        """
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        values = tuple(data.values()) + (record_id,)
        
        query = f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount

    def delete(self, table: str, record_id: str, id_column: str = "id") -> int:
        """
        특정 ID의 레코드를 삭제(DELETE)합니다.
        
        Returns:
            삭제된 행(Row)의 수
        """
        query = f"DELETE FROM {table} WHERE {id_column} = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (record_id,))
            conn.commit()
            return cursor.rowcount

    def execute_query(self, query: str, parameters: Tuple = ()) -> List[sqlite3.Row]:
        """임의의 복잡한 SELECT 쿼리를 실행할 때 사용합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            return cursor.fetchall()
