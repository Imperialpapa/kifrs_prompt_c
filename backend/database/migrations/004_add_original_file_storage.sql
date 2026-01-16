-- K-IFRS 1019 DBO Validation System
-- Migration: 004 - Add Original File Storage
-- Date: 2026-01-15
-- Purpose: 원본 규칙 파일 저장 기능 추가 (재해석 지원)

-- =============================================================================
-- 1. rule_files 테이블에 원본 파일 바이너리 저장 컬럼 추가
-- =============================================================================
ALTER TABLE rule_files
ADD COLUMN IF NOT EXISTS original_file_content BYTEA;

COMMENT ON COLUMN rule_files.original_file_content IS '원본 규칙 파일 바이너리 (재해석용)';

-- =============================================================================
-- 2. 해석 상태 추적 컬럼 추가
-- =============================================================================
ALTER TABLE rule_files
ADD COLUMN IF NOT EXISTS interpretation_status VARCHAR(20) DEFAULT 'pending';

ALTER TABLE rule_files
ADD COLUMN IF NOT EXISTS last_interpreted_at TIMESTAMP;

ALTER TABLE rule_files
ADD COLUMN IF NOT EXISTS interpretation_engine VARCHAR(20); -- 'local', 'openai', 'anthropic', 'gemini'

COMMENT ON COLUMN rule_files.interpretation_status IS 'pending, completed, failed';
COMMENT ON COLUMN rule_files.interpretation_engine IS '마지막 해석에 사용된 엔진';

-- =============================================================================
-- End of Migration
-- =============================================================================
