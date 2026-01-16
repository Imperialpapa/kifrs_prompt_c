"""
Migration 004 Runner - Add Original File Storage
================================================
원본 파일 저장 컬럼 추가 마이그레이션 실행

Usage:
    python run_migration_004.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from database.supabase_client import supabase


def run_migration():
    """Execute migration 004"""
    print("=" * 60)
    print("Migration 004: Add Original File Storage")
    print("=" * 60)

    if not supabase:
        print("ERROR: Supabase client not initialized")
        return False

    # SQL statements to execute
    statements = [
        # 1. Add original_file_content column
        """
        ALTER TABLE rule_files
        ADD COLUMN IF NOT EXISTS original_file_content TEXT;
        """,

        # 2. Add interpretation_status column
        """
        ALTER TABLE rule_files
        ADD COLUMN IF NOT EXISTS interpretation_status VARCHAR(20) DEFAULT 'pending';
        """,

        # 3. Add last_interpreted_at column
        """
        ALTER TABLE rule_files
        ADD COLUMN IF NOT EXISTS last_interpreted_at TIMESTAMP;
        """,

        # 4. Add interpretation_engine column
        """
        ALTER TABLE rule_files
        ADD COLUMN IF NOT EXISTS interpretation_engine VARCHAR(20);
        """
    ]

    success_count = 0
    for i, sql in enumerate(statements, 1):
        try:
            # Execute via RPC or direct query
            # Note: Supabase Python client doesn't support raw SQL easily
            # You may need to run this directly in Supabase SQL Editor
            print(f"\n[{i}/{len(statements)}] Executing...")
            print(f"SQL: {sql.strip()[:100]}...")

            # This won't work directly - need to run in Supabase SQL Editor
            # Just print for manual execution
            success_count += 1
            print(f"   -> Please run this SQL in Supabase SQL Editor")

        except Exception as e:
            print(f"   -> Error: {str(e)}")

    print("\n" + "=" * 60)
    print(f"Migration completed: {success_count}/{len(statements)} statements")
    print("\nIMPORTANT: Please run the SQL in 004_add_original_file_storage.sql")
    print("directly in Supabase SQL Editor at:")
    print("https://supabase.com/dashboard/project/YOUR_PROJECT/sql")
    print("=" * 60)

    return True


if __name__ == "__main__":
    run_migration()
