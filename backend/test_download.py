"""
Test rule file download functionality
"""

import asyncio
import sys
from services.rule_service import RuleService

async def test_download():
    """Test downloading the first available rule file"""

    service = RuleService()

    print("=" * 70)
    print("Testing Rule File Download")
    print("=" * 70)

    # Get list of files
    print("\n1. Fetching rule files...")
    files = await service.list_rule_files(limit=5)

    if not files:
        print("No rule files found in database")
        return

    print(f"Found {len(files)} rule files")

    # Test download of first file
    first_file = files[0]
    print(f"\n2. Testing download of: {first_file.file_name}")
    print(f"   File ID: {first_file.id}")

    try:
        excel_bytes = await service.export_rules_to_excel(first_file.id)
        print(f"\n✓ Download successful!")
        print(f"   Excel file size: {len(excel_bytes)} bytes")

        # Save to file for inspection
        output_path = f"test_download_{first_file.id[:8]}.xlsx"
        with open(output_path, 'wb') as f:
            f.write(excel_bytes)
        print(f"   Saved to: {output_path}")

    except Exception as e:
        print(f"\n✗ Download failed!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(test_download())
