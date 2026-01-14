"""
Clean up broken rule file (file record exists but no rules)
"""

import asyncio
from database.rule_repository import RuleRepository
from uuid import UUID

async def cleanup():
    repo = RuleRepository()
    file_id = '5ea221ce-8985-49cc-8412-4995e87e62b2'

    print("=" * 70)
    print("Cleaning up broken rule file")
    print("=" * 70)

    # Check file
    file_record = await repo.get_rule_file(UUID(file_id))
    if file_record:
        print(f"\nFile: {file_record['file_name']}")
        print(f"Status: {file_record['status']}")
        print(f"Reported rules: {file_record['total_rules_count']}")

    # Check rules
    rules = await repo.get_rules_by_file(UUID(file_id), active_only=True)
    print(f"Actual rules in DB: {len(rules)}")

    if len(rules) == 0:
        print("\n⚠ This file has no rules. Archiving...")
        success = await repo.archive_rule_file(UUID(file_id))

        if success:
            print("✓ File archived successfully")
            print("\nYou can now re-upload the file to create rules properly.")
        else:
            print("✗ Failed to archive file")
    else:
        print("\n✓ File has rules, no cleanup needed")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(cleanup())
