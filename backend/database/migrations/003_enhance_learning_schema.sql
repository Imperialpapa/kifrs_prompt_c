-- Migration 003: Enhance user_corrections for AI Learning
-- ============================================================

-- Add columns to user_corrections to support AI learning
ALTER TABLE user_corrections
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2), -- AI's confidence if it was an AI suggestion
ADD COLUMN IF NOT EXISTS is_ai_suggested BOOLEAN DEFAULT false, -- Was this fix originally suggested by AI?
ADD COLUMN IF NOT EXISTS rule_file_id UUID REFERENCES rule_files(id), -- Link to specific rule file context
ADD COLUMN IF NOT EXISTS sheet_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS column_name VARCHAR(255);

-- Index for fast retrieval during RAG (Retrieval-Augmented Generation)
-- When AI needs to know "How did users fix 'rule_X' in 'col_Y'?", this index helps.
CREATE INDEX IF NOT EXISTS idx_learning_lookup 
ON user_corrections (original_rule_id, column_name, old_value);

COMMENT ON COLUMN user_corrections.confidence_score IS 'AI가 제안했을 당시의 신뢰도';
COMMENT ON COLUMN user_corrections.is_ai_suggested IS 'AI 제안 기반 수정 여부';
