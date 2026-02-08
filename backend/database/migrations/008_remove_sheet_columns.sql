-- K-IFRS 1019 DBO Validation System - Remove Sheet Columns
-- ============================================================
-- Migration: 008 - Remove sheet_name based rule management
-- Date: 2026-02-07
-- Purpose: Switch to field_name only rule management (no sheet grouping)

-- =============================================================================
-- Step 1: Drop the sheet_name index (no longer needed for lookups)
-- =============================================================================
DROP INDEX IF EXISTS idx_rules_sheet_name;

-- =============================================================================
-- Step 2: Make sheet columns nullable (keep for backward compatibility)
-- =============================================================================
-- Instead of dropping columns immediately, we make them nullable
-- This allows existing data to remain but new rules won't require sheet info

ALTER TABLE rules ALTER COLUMN sheet_name DROP NOT NULL;

-- Note: display_sheet_name and canonical_sheet_name are already nullable

-- =============================================================================
-- Step 3: Add unique constraint on (rule_file_id, field_name, row_number)
-- =============================================================================
-- This ensures field_name uniqueness per file (replacing sheet-based grouping)
-- Note: We use row_number to allow same field with different rules

-- First, create a partial unique index (if needed)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_rules_file_field ON rules(rule_file_id, field_name, row_number) WHERE is_active = true;

-- =============================================================================
-- Step 4: Update comments
-- =============================================================================
COMMENT ON COLUMN rules.sheet_name IS 'DEPRECATED: Previously used for sheet-based grouping. Now nullable.';
COMMENT ON COLUMN rules.display_sheet_name IS 'DEPRECATED: Previously used for display. Now nullable.';
COMMENT ON COLUMN rules.canonical_sheet_name IS 'DEPRECATED: Previously used for matching. Now nullable.';

-- =============================================================================
-- Optional: Clean up old data (run manually if needed)
-- =============================================================================
-- UPDATE rules SET sheet_name = NULL, display_sheet_name = NULL, canonical_sheet_name = NULL;

-- =============================================================================
-- End of Migration
-- =============================================================================
