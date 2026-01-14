-- =============================================================================
-- Migration 002: Disable RLS for Development
-- =============================================================================
-- Row Level Security를 비활성화하거나 모든 접근을 허용하는 정책 추가
-- 개발 환경에서 사용하며, 프로덕션에서는 적절한 정책으로 교체 필요
--
-- 실행 방법:
-- 1. Supabase Dashboard → SQL Editor 접속
-- 2. 아래 SQL 복사/붙여넣기 후 실행
-- =============================================================================

-- Option 1: RLS 완전 비활성화 (개발 환경 권장)
ALTER TABLE rule_files DISABLE ROW LEVEL SECURITY;
ALTER TABLE rules DISABLE ROW LEVEL SECURITY;
ALTER TABLE validation_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE validation_errors DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_interpretation_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE false_positive_feedback DISABLE ROW LEVEL SECURITY;
ALTER TABLE rule_accuracy_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_corrections DISABLE ROW LEVEL SECURITY;

-- Option 2: RLS 활성화 상태에서 모든 작업 허용 정책 추가 (보안이 필요한 경우)
-- 위의 Option 1 대신 아래 코드를 사용하세요

/*
-- rule_files 테이블 정책
ALTER TABLE rule_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on rule_files"
ON rule_files
FOR ALL
USING (true)
WITH CHECK (true);

-- rules 테이블 정책
ALTER TABLE rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on rules"
ON rules
FOR ALL
USING (true)
WITH CHECK (true);

-- validation_sessions 테이블 정책
ALTER TABLE validation_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on validation_sessions"
ON validation_sessions
FOR ALL
USING (true)
WITH CHECK (true);

-- validation_errors 테이블 정책
ALTER TABLE validation_errors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on validation_errors"
ON validation_errors
FOR ALL
USING (true)
WITH CHECK (true);

-- ai_interpretation_logs 테이블 정책
ALTER TABLE ai_interpretation_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on ai_interpretation_logs"
ON ai_interpretation_logs
FOR ALL
USING (true)
WITH CHECK (true);

-- false_positive_feedback 테이블 정책
ALTER TABLE false_positive_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on false_positive_feedback"
ON false_positive_feedback
FOR ALL
USING (true)
WITH CHECK (true);

-- rule_accuracy_metrics 테이블 정책
ALTER TABLE rule_accuracy_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on rule_accuracy_metrics"
ON rule_accuracy_metrics
FOR ALL
USING (true)
WITH CHECK (true);

-- user_corrections 테이블 정책
ALTER TABLE user_corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on user_corrections"
ON user_corrections
FOR ALL
USING (true)
WITH CHECK (true);
*/

-- =============================================================================
-- 확인 쿼리 (실행 후 RLS 상태 확인)
-- =============================================================================

SELECT
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'rule_files',
    'rules',
    'validation_sessions',
    'validation_errors',
    'ai_interpretation_logs',
    'false_positive_feedback',
    'rule_accuracy_metrics',
    'user_corrections'
)
ORDER BY tablename;
