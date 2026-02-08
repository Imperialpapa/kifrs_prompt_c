-- K-IFRS 1019 DBO Validation System - Column Letter Length Expansion
-- ============================================================
-- Migration: 009 - Expand column_letter to VARCHAR(100)
-- Date: 2026-02-08
-- Purpose: Support longer descriptive column letters or names in rule files

-- =============================================================================
-- Expand column_letter from VARCHAR(10) to VARCHAR(100)
-- =============================================================================
-- This prevents "value too long for type character varying(10)" errors
-- when the rule file contains longer strings in the column identification field.

ALTER TABLE rules ALTER COLUMN column_letter TYPE VARCHAR(100);

-- Update comment
COMMENT ON COLUMN rules.column_letter IS 'Column identification from Excel (e.g., A, B, or descriptive text)';

-- =============================================================================
-- End of Migration
-- =============================================================================
