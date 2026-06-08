import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from core.models import SCHEMA_VERSION

logger = logging.getLogger(__name__)


class DBManager:
    """
    데이터베이스 연결, 트랜잭션 관리 및 쿼리 실행을 담당하는 비동기 인프라 클래스.
    """

    def __init__(self, db_path: str = "hopilot.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        """새로운 비동기 데이터베이스 연결을 반환합니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            # SQLite 동시성(성능) 향상 및 데이터 무결성 제약 활성화
            await conn.execute("PRAGMA journal_mode = WAL;")
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute("PRAGMA busy_timeout = 30000;")

            conn.row_factory = aiosqlite.Row
            yield conn

    async def initialize(self):
        """
        애플리케이션 초기화 시 호출되어 필요한 테이블을 생성합니다.
        schema.sql 파일을 읽어와 데이터베이스 스키마를 구성합니다.
        """
        logger.info("Initializing database from schema.sql...")
        schema_path = Path(__file__).parent / "schema.sql"

        if not schema_path.exists():
            logger.warning(f"Schema file not found at {schema_path}")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_script = f.read()

        async with self.get_connection() as conn:
            await conn.executescript(schema_script)
            await conn.commit()

        # 스키마 구성이 끝난 후 마이그레이션 로직 실행
        await self._run_migrations()
        logger.info("Database initialized successfully.")

    async def _run_migrations(self):
        """저장된 MIGRATIONS 딕셔너리를 기반으로 순차적으로 마이그레이션을 수행합니다."""
        from .migrations import MIGRATIONS

        async with self.get_connection() as conn:
            # 현재 버전 조회
            async with conn.execute(
                "SELECT MAX(version) as current_version FROM schema_version"
            ) as cursor:
                row = await cursor.fetchone()
                current_version = row["current_version"] if row and row["current_version"] else 1

            target_version = SCHEMA_VERSION

            if current_version >= target_version:
                return

            logger.info(
                f"Running database migrations from v{current_version} to v{target_version}..."
            )

            for version in range(current_version + 1, target_version + 1):
                try:
                    if version in MIGRATIONS:
                        callback = MIGRATIONS[version]
                        await callback(conn)

                    await conn.execute(
                        "INSERT INTO schema_version (version) VALUES (?)", (version,)
                    )
                    await conn.commit()
                    logger.info(f"Successfully migrated to v{version}.")
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Migration to v{version} failed: {e}")
                    raise

    async def create(self, table: str, data: Dict[str, Any]) -> int | None:
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

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, values)
            await conn.commit()
            return cursor.lastrowid

    async def load(
        self, table: str, session_id: str, id_column: str = "id"
    ) -> Optional[aiosqlite.Row]:
        """
        특정 ID의 레코드를 로드(SELECT)합니다.

        Returns:
            레코드 데이터를 담은 aiosqlite.Row 객체 (존재하지 않으면 None)
        """
        query = f"SELECT * FROM {table} WHERE {id_column} = ?"

        async with self.get_connection() as conn:
            async with conn.execute(query, (session_id,)) as cursor:
                return await cursor.fetchone()

    async def save(
        self, table: str, session_id: str, data: Dict[str, Any], id_column: str = "id"
    ) -> int:
        """
        기존 레코드를 업데이트(UPDATE)하여 저장합니다.

        Returns:
            업데이트된 행(Row)의 수
        """
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        values = tuple(data.values()) + (session_id,)

        query = f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?"

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, values)
            await conn.commit()
            return cursor.rowcount

    async def delete(self, table: str, session_id: str, id_column: str = "id") -> int:
        """
        특정 ID의 레코드를 삭제(DELETE)합니다.

        Returns:
            삭제된 행(Row)의 수
        """
        query = f"DELETE FROM {table} WHERE {id_column} = ?"

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (session_id,))
            await conn.commit()
            return cursor.rowcount

    async def execute_query(self, query: str, parameters: Tuple = ()) -> List[aiosqlite.Row]:
        """임의의 복잡한 SELECT 쿼리를 실행할 때 사용합니다."""
        async with self.get_connection() as conn:
            async with conn.execute(query, parameters) as cursor:
                rows = await cursor.fetchall()
                return list(rows)
