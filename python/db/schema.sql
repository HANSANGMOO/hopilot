-- 1. 메인 세션 테이블
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    schema_version INTEGER NOT NULL,
    meta TEXT,
    messages TEXT
);

-- 2. 데이터베이스 스키마 마이그레이션 버전 관리 테이블
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 초기 버전 세팅 (버전 1)
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
