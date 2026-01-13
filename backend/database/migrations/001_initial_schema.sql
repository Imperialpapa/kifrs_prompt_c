-- K-IFRS 1019 DBO Validation System - Initial Database Schema
-- ============================================================
-- Run this SQL in Supabase SQL Editor or via pgAdmin
-- Migration: 001 - Initial Schema
-- Date: 2025-01-13

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table 1: rule_files - Rule File Metadata
-- =============================================================================
CREATE TABLE rule_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(255) NOT NULL,
    file_version VARCHAR(50),
    uploaded_by VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    file_size_bytes INTEGER,
    sheet_count INTEGER,
    total_rules_count INTEGER,
    status VARCHAR(20) DEFAULT 'active', -- active, archived, deprecated
    notes TEXT,
    original_file_url TEXT, -- Supabase Storage URL
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rule_files_status ON rule_files(status);
CREATE INDEX idx_rule_files_uploaded_at ON rule_files(uploaded_at DESC);

COMMENT ON TABLE rule_files IS '규칙 파일 메타데이터';
COMMENT ON COLUMN rule_files.status IS 'active, archived, deprecated 중 하나';

-- =============================================================================
-- Table 2: rules - Individual Rules with Versioning
-- =============================================================================
CREATE TABLE rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_file_id UUID REFERENCES rule_files(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,

    -- Rule metadata from Excel B
    sheet_name VARCHAR(255) NOT NULL,
    display_sheet_name VARCHAR(255),
    canonical_sheet_name VARCHAR(255), -- normalized for matching
    row_number INTEGER,
    column_letter VARCHAR(10),
    field_name VARCHAR(255) NOT NULL,

    -- Natural language rule
    rule_text TEXT NOT NULL,
    condition VARCHAR(500),
    note TEXT,

    -- AI Interpretation (cached)
    ai_rule_id VARCHAR(50), -- RULE_001, RULE_002, etc.
    ai_rule_type VARCHAR(50), -- required, no_duplicates, format, etc.
    ai_parameters JSONB, -- {format: "YYYYMMDD", regex: "..."}
    ai_error_message TEXT,
    ai_interpretation_summary TEXT,
    ai_confidence_score DECIMAL(3,2),
    ai_interpreted_at TIMESTAMP,
    ai_model_version VARCHAR(50),

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rules_file_id ON rules(rule_file_id);
CREATE INDEX idx_rules_sheet_name ON rules(canonical_sheet_name);
CREATE INDEX idx_rules_field_name ON rules(field_name);
CREATE INDEX idx_rules_active ON rules(is_active);
CREATE INDEX idx_rules_version ON rules(rule_file_id, version);

COMMENT ON TABLE rules IS '개별 검증 규칙 (AI 해석 캐시 포함)';
COMMENT ON COLUMN rules.canonical_sheet_name IS '공백 제거 정규화 시트명 (매칭용)';
COMMENT ON COLUMN rules.ai_parameters IS 'AI 해석 파라미터 (JSON 형식)';

-- =============================================================================
-- Table 3: validation_sessions - Validation History
-- =============================================================================
CREATE TABLE validation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_token VARCHAR(100) UNIQUE,

    -- File information
    employee_file_name VARCHAR(255),
    employee_file_url TEXT, -- optional: store in Supabase Storage
    rule_source_type VARCHAR(20) NOT NULL, -- 'file_upload' or 'database'
    rule_file_id UUID REFERENCES rule_files(id),

    -- Summary statistics
    total_rows INTEGER,
    valid_rows INTEGER,
    error_rows INTEGER,
    total_errors INTEGER,
    rules_applied_count INTEGER,
    validation_status VARCHAR(20), -- PASS, FAIL

    -- Metadata
    ai_processing_time_seconds DECIMAL(10,3),
    validation_processing_time_seconds DECIMAL(10,3),
    system_version VARCHAR(50),
    ai_model_version VARCHAR(50),

    -- Results (stored as JSON for flexibility)
    full_results JSONB, -- entire ValidationResponse

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_validation_sessions_created ON validation_sessions(created_at DESC);
CREATE INDEX idx_validation_sessions_rule_file ON validation_sessions(rule_file_id);
CREATE INDEX idx_validation_sessions_status ON validation_sessions(validation_status);

COMMENT ON TABLE validation_sessions IS '검증 세션 이력';
COMMENT ON COLUMN validation_sessions.rule_source_type IS 'file_upload 또는 database';

-- =============================================================================
-- Table 4: validation_errors - Individual Error Records
-- =============================================================================
CREATE TABLE validation_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES validation_sessions(id) ON DELETE CASCADE,

    -- Error details
    sheet_name VARCHAR(255),
    row_number INTEGER,
    column_name VARCHAR(255),
    rule_id VARCHAR(50),

    -- Error data
    error_message TEXT,
    actual_value TEXT,
    expected_value TEXT,
    source_rule_text TEXT,

    -- User correction tracking
    user_corrected BOOLEAN DEFAULT false,
    correction_timestamp TIMESTAMP,
    correction_type VARCHAR(50), -- 'false_positive', 'confirmed_error', 'rule_adjustment'
    correction_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_validation_errors_session ON validation_errors(session_id);
CREATE INDEX idx_validation_errors_rule ON validation_errors(rule_id);
CREATE INDEX idx_validation_errors_corrected ON validation_errors(user_corrected);

COMMENT ON TABLE validation_errors IS '개별 검증 오류 기록';

-- =============================================================================
-- Table 5: ai_interpretation_logs - AI Interpretation History
-- =============================================================================
CREATE TABLE ai_interpretation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_file_id UUID REFERENCES rule_files(id),

    -- Input
    natural_language_rule TEXT NOT NULL,
    sheet_name VARCHAR(255),
    field_name VARCHAR(255),

    -- AI Output
    interpreted_rule_type VARCHAR(50),
    interpreted_parameters JSONB,
    confidence_score DECIMAL(3,2),
    ai_model_version VARCHAR(50),
    processing_time_seconds DECIMAL(10,3),

    -- Quality tracking
    interpretation_quality VARCHAR(20), -- 'good', 'needs_review', 'poor'
    user_feedback TEXT,
    feedback_timestamp TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_logs_rule_file ON ai_interpretation_logs(rule_file_id);
CREATE INDEX idx_ai_logs_quality ON ai_interpretation_logs(interpretation_quality);
CREATE INDEX idx_ai_logs_created ON ai_interpretation_logs(created_at DESC);

COMMENT ON TABLE ai_interpretation_logs IS 'AI 규칙 해석 이력';

-- =============================================================================
-- Table 6: false_positive_feedback - False Positive Tracking
-- =============================================================================
CREATE TABLE false_positive_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_id UUID REFERENCES validation_errors(id),
    session_id UUID REFERENCES validation_sessions(id),

    -- Context
    rule_id VARCHAR(50),
    field_name VARCHAR(255),
    error_message TEXT,
    actual_value TEXT,

    -- Feedback
    is_false_positive BOOLEAN,
    user_explanation TEXT,
    suggested_rule_adjustment TEXT,
    feedback_by VARCHAR(100),

    -- Learning impact
    pattern_identified VARCHAR(255), -- e.g., "date_format_exception", "edge_case_handling"
    applied_to_improve_rules BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_false_positive_session ON false_positive_feedback(session_id);
CREATE INDEX idx_false_positive_rule ON false_positive_feedback(rule_id);
CREATE INDEX idx_false_positive_pattern ON false_positive_feedback(pattern_identified);

COMMENT ON TABLE false_positive_feedback IS 'False Positive 피드백';

-- =============================================================================
-- Table 7: rule_accuracy_metrics - Rule Performance Tracking
-- =============================================================================
CREATE TABLE rule_accuracy_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id VARCHAR(50) NOT NULL,
    rule_file_id UUID REFERENCES rule_files(id),
    metric_date DATE DEFAULT CURRENT_DATE,

    -- Usage statistics
    times_applied INTEGER DEFAULT 0,
    errors_detected INTEGER DEFAULT 0,
    false_positives_reported INTEGER DEFAULT 0,

    -- Calculated metrics
    false_positive_rate DECIMAL(5,4), -- errors_detected / false_positives_reported
    confidence_trend DECIMAL(3,2), -- moving average of confidence scores

    -- Quality score (0-100)
    accuracy_score DECIMAL(5,2),

    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_rule_metrics_unique ON rule_accuracy_metrics(rule_id, rule_file_id, metric_date);
CREATE INDEX idx_rule_metrics_date ON rule_accuracy_metrics(metric_date DESC);

COMMENT ON TABLE rule_accuracy_metrics IS '규칙 정확도 메트릭';

-- =============================================================================
-- Table 8: user_corrections - User Correction History
-- =============================================================================
CREATE TABLE user_corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES validation_sessions(id),
    error_id UUID REFERENCES validation_errors(id),

    -- Original error context
    original_rule_id VARCHAR(50),
    original_error_message TEXT,

    -- Correction details
    correction_action VARCHAR(50), -- 'mark_false_positive', 'adjust_rule', 'confirm_error'
    old_value TEXT,
    new_value TEXT,
    correction_reason TEXT,

    -- Impact tracking
    affects_rule_interpretation BOOLEAN DEFAULT false,
    suggested_rule_change TEXT,

    corrected_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_corrections_session ON user_corrections(session_id);
CREATE INDEX idx_user_corrections_rule ON user_corrections(original_rule_id);
CREATE INDEX idx_user_corrections_created ON user_corrections(created_at DESC);

COMMENT ON TABLE user_corrections IS '사용자 수정 이력';

-- =============================================================================
-- Helper Function: Increment False Positives
-- =============================================================================
CREATE OR REPLACE FUNCTION increment_false_positives(
    p_rule_id VARCHAR(50),
    p_metric_date DATE
) RETURNS VOID AS $$
BEGIN
    INSERT INTO rule_accuracy_metrics (rule_id, metric_date, false_positives_reported)
    VALUES (p_rule_id, p_metric_date, 1)
    ON CONFLICT (rule_id, rule_file_id, metric_date)
    DO UPDATE SET
        false_positives_reported = rule_accuracy_metrics.false_positives_reported + 1,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_false_positives IS 'False Positive 카운트 증가';

-- =============================================================================
-- Row Level Security (RLS) Setup
-- =============================================================================
-- Enable RLS on all tables
ALTER TABLE rule_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_interpretation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE false_positive_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_accuracy_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_corrections ENABLE ROW LEVEL SECURITY;

-- Basic policies (allow all for authenticated users)
-- Adjust these policies based on your authentication requirements

CREATE POLICY "Allow authenticated users to read rule_files"
    ON rule_files FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to insert rule_files"
    ON rule_files FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update rule_files"
    ON rule_files FOR UPDATE
    TO authenticated
    USING (true);

-- Similar policies for other tables
CREATE POLICY "Allow authenticated users full access to rules"
    ON rules FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to validation_sessions"
    ON validation_sessions FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to validation_errors"
    ON validation_errors FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to ai_interpretation_logs"
    ON ai_interpretation_logs FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to false_positive_feedback"
    ON false_positive_feedback FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to rule_accuracy_metrics"
    ON rule_accuracy_metrics FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to user_corrections"
    ON user_corrections FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- End of Schema
-- =============================================================================
COMMENT ON SCHEMA public IS 'K-IFRS 1019 DBO Validation System - Database Schema v1.0';
