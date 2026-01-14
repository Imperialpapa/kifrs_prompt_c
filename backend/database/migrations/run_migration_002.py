"""
Migration 002 실행 스크립트
RLS 정책 비활성화
"""

import sys
sys.path.insert(0, '../..')

from database.supabase_client import supabase

def run_migration():
    """RLS 비활성화 마이그레이션 실행"""

    print("=" * 70)
    print("Migration 002: Disable RLS for Development")
    print("=" * 70)

    tables = [
        'rule_files',
        'rules',
        'validation_sessions',
        'validation_errors',
        'ai_interpretation_logs',
        'false_positive_feedback',
        'rule_accuracy_metrics',
        'user_corrections'
    ]

    try:
        for table in tables:
            sql = f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
            print(f"\n[{table}] Disabling RLS...")

            try:
                result = supabase.rpc('exec_sql', {'sql': sql}).execute()
                print(f"[{table}] ✓ RLS disabled")
            except Exception as e:
                # Supabase Python client doesn't support raw SQL execution
                # Users must run SQL manually in dashboard
                print(f"[{table}] ⚠ Cannot execute via Python client")
                print(f"          Please run SQL manually in Supabase Dashboard")

        print("\n" + "=" * 70)
        print("⚠ IMPORTANT:")
        print("Python client cannot execute ALTER TABLE commands.")
        print("Please run the SQL manually in Supabase SQL Editor:")
        print()
        print("1. Go to https://app.supabase.com")
        print("2. Open SQL Editor")
        print("3. Run the SQL from 002_disable_rls_for_dev.sql")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        return False

    return True

if __name__ == "__main__":
    run_migration()
