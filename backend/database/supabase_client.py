"""
K-IFRS 1019 DBO Validation System - Supabase Client
===================================================
Singleton Supabase client for database connections

Usage:
    from database.supabase_client import supabase
    result = supabase.table('rule_files').select('*').execute()
"""

from supabase import create_client, Client
from typing import Optional
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
except ImportError:
    print("Warning: config.py not found. Supabase client will not be initialized.")
    settings = None


class SupabaseClient:
    """
    Singleton Supabase client manager

    Provides:
    - Single client instance (connection pooling)
    - Admin client for elevated operations
    - Connection validation
    """

    _instance: Optional[Client] = None
    _admin_instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get regular Supabase client (anon key)

        Returns:
            Client: Supabase client instance

        Raises:
            ValueError: If Supabase credentials are not configured
        """
        if cls._instance is None:
            if not settings or not settings.is_supabase_configured():
                raise ValueError(
                    "Supabase is not configured. Please set SUPABASE_URL and "
                    "SUPABASE_KEY in your .env file."
                )

            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            print(f"[Supabase] Connected to {settings.SUPABASE_URL}")

        return cls._instance

    @classmethod
    def get_admin_client(cls) -> Client:
        """
        Get admin Supabase client (service key)

        Use for operations requiring elevated privileges:
        - Bypassing RLS policies
        - Bulk operations
        - Administrative tasks

        Returns:
            Client: Supabase admin client instance

        Raises:
            ValueError: If service key is not configured
        """
        if cls._admin_instance is None:
            if not settings or not settings.SUPABASE_SERVICE_KEY:
                # Fall back to regular client if service key not available
                print("[Supabase] Warning: Service key not configured, using anon key")
                return cls.get_client()

            cls._admin_instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            print(f"[Supabase] Admin client connected")

        return cls._admin_instance

    @classmethod
    def test_connection(cls) -> bool:
        """
        Test Supabase connection

        Returns:
            bool: True if connection successful
        """
        try:
            client = cls.get_client()
            # Try a simple query to rule_files table
            result = client.table('rule_files').select('id').limit(1).execute()
            print("[Supabase] Connection test successful")
            return True
        except Exception as e:
            print(f"[Supabase] Connection test failed: {str(e)}")
            return False

    @classmethod
    def reset(cls):
        """Reset client instances (useful for testing)"""
        cls._instance = None
        cls._admin_instance = None


# =============================================================================
# Convenience: Global Client Instance
# =============================================================================

# Only initialize if settings are available
# Use ADMIN CLIENT (service key) to bypass RLS policies
supabase: Optional[Client] = None

if settings and settings.is_supabase_configured():
    try:
        # Use admin client with service key to bypass RLS
        if settings.SUPABASE_SERVICE_KEY:
            supabase = SupabaseClient.get_admin_client()
            print("[Supabase] Using admin client (service key) - RLS bypassed")
        else:
            supabase = SupabaseClient.get_client()
            print("[Supabase] Using regular client (anon key) - RLS policies apply")
    except ValueError as e:
        print(f"[Supabase] Initialization skipped: {str(e)}")
        print("[Supabase] Database features will be disabled.")
else:
    print("[Supabase] Configuration not found. Database features disabled.")
    print("[Supabase] To enable: Copy .env.example to .env and configure credentials.")


# =============================================================================
# Testing and Diagnostics
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Supabase Client Test")
    print("=" * 70)

    if not settings:
        print("ERROR: Settings not loaded")
        sys.exit(1)

    print(f"Supabase URL: {settings.SUPABASE_URL}")
    print(f"Supabase Configured: {settings.is_supabase_configured()}")

    if settings.is_supabase_configured():
        print("\nTesting connection...")
        success = SupabaseClient.test_connection()

        if success:
            print("\n✓ Supabase connection successful!")

            # Try listing tables
            try:
                client = SupabaseClient.get_client()
                result = client.table('rule_files').select('id, file_name').limit(5).execute()
                print(f"\nFound {len(result.data)} rule files in database")
                for row in result.data:
                    print(f"  - {row.get('file_name', 'N/A')}")
            except Exception as e:
                print(f"\nNote: Could not list rule_files: {str(e)}")
                print("(This is expected if tables haven't been created yet)")
        else:
            print("\n✗ Supabase connection failed")
            print("Please check your .env configuration")
    else:
        print("\n✗ Supabase not configured")
        print("Please set SUPABASE_URL and SUPABASE_KEY in .env")

    print("=" * 70)
