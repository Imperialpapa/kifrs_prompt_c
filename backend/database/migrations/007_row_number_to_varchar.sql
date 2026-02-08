-- K-IFRS 1019 DBO Validation System - Row Number Type Migration
-- ============================================================
-- Migration: 007 - row_number to VARCHAR for sub-index support
-- Date: 2026-02-06
-- Purpose: Support composite rule splitting with sub-indices (e.g., 5.1, 5.2)

-- =============================================================================
-- Migrate row_number from INTEGER to VARCHAR(20)
-- =============================================================================
-- This allows storing sub-indices like "5.1", "5.2" for split composite rules
-- Existing integer values are automatically converted to strings (e.g., 5 -> "5")

ALTER TABLE rules ALTER COLUMN row_number TYPE VARCHAR(20) USING row_number::TEXT;

-- Update comment to reflect the change
COMMENT ON COLUMN rules.row_number IS 'Row number from Excel (supports sub-indices like 5.1, 5.2 for split rules)';

-- =============================================================================
-- End of Migration
-- =============================================================================
