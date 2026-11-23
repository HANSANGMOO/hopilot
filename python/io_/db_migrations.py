import logging

import aiosqlite

logger = logging.getLogger(__name__)


async def _migrate_v1_to_v2(conn: aiosqlite.Connection):
    logger.info("Migrating schema to v2: adding project_id to sessions...")
    # SQLite ALTER TABLE은 FK 제약을 지원하지 않으므로 컬럼만 추가
    await conn.execute(
        "ALTER TABLE sessions ADD COLUMN project_id TEXT"
    )


MIGRATIONS = {
    2: _migrate_v1_to_v2,
}
