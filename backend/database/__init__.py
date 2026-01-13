"""
Database package for K-IFRS 1019 DBO Validation System
======================================================
Supabase-based data persistence layer
"""

from .supabase_client import SupabaseClient, supabase

__all__ = ["SupabaseClient", "supabase"]
