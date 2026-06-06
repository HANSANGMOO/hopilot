import logging

logger = logging.getLogger(__name__)

# DB 스키마 및 데이터 마이그레이션 콜백 함수들을 정의합니다.

# 예시: v1에서 v2로 넘어갈 때 필요한 비동기 작업
# async def _migrate_v1_to_v2(conn: aiosqlite.Connection):
#     logger.info("Migrating schema to v2...")
#     # SQL 스키마 변경
#     # await conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT;")
#     # JSON 데이터 내부 가공
#     # ...

# 버전 번호를 키로 하고, 해당 버전이 되기 위해 실행할 비동기 콜백 함수를 매핑합니다.
MIGRATIONS = {
    # 2: _migrate_v1_to_v2,
}
