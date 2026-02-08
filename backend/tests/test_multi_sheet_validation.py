import sys
import os
import asyncio
import pandas as pd
from typing import List
from uuid import uuid4

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.validation_service import ValidationService
from models import ValidationRule, RuleSource
from rule_engine import RuleEngine

class TestValidationService(ValidationService):
    def __init__(self):
        # Skip DB initialization
        self.rule_repository = None
        self.validation_repository = None
        self.ai_cache_service = None
        self.rule_engine = RuleEngine()

async def test_multi_sheet_validation():
    print("=" * 70)
    print("Multi-Sheet Validation Logic Test")
    print("=" * 70)

    # 1. Setup Mock Data (2 Sheets)
    print("\n[Step 1] Preparing Mock Data...")
    
    # Sheet 1: Production (contains 'Gender' column)
    df_prod = pd.DataFrame({
        'Name': ['Kim', 'Lee', 'Park'],
        'Gender': ['M', 'F', 'Male']  # 'Male' is invalid (expecting M/F)
    })
    
    # Sheet 2: Office (contains 'Gender' column)
    df_office = pd.DataFrame({
        'Name': ['Choi', 'Jung'],
        'Gender': ['Woman', 'M']  # 'Woman' is invalid (expecting M/F)
    })
    
    # Sheet 3: Metadata (NO 'Gender' column) - Should be skipped for Gender rule
    df_meta = pd.DataFrame({
        'Info': ['Ver 1.0', '2023-01-01']
    })

    sheet_data_map = {
        "sheet1": {"display_name": "Production", "original_name": "Production", "df": df_prod},
        "sheet2": {"display_name": "Office", "original_name": "Office", "df": df_office},
        "sheet3": {"display_name": "Metadata", "original_name": "Metadata", "df": df_meta}
    }
    
    print(f"  - Sheet 'Production': {len(df_prod)} rows")
    print(f"  - Sheet 'Office': {len(df_office)} rows")
    print(f"  - Sheet 'Metadata': {len(df_meta)} rows")

    # 2. Setup Validation Rules (Field-based, No Sheet Info)
    print("\n[Step 2] Defining Rules...")
    
    source = RuleSource(
        original_text="성별은 M 또는 F여야 함",
        sheet_name="None", # No sheet info
        row_number="1"
    )
    
    rule_gender = ValidationRule(
        rule_id="RULE_GENDER",
        field_name="Gender",
        rule_type="format",
        parameters={"allowed_values": ["M", "F"]},
        error_message_template="{field_name} must be M or F",
        source=source,
        confidence_score=1.0,
        ai_interpretation_summary="Test Summary"
    )
    
    rules = [rule_gender]
    print(f"  - Defined {len(rules)} rule(s) for field 'Gender'")

    # 3. Execute Validation
    print("\n[Step 3] Executing Validation...")
    service = TestValidationService()
    
    result = await service.validate_sheets(sheet_data_map, rules)
    
    # 4. Analyze Results
    print("\n[Step 4] Analyzing Results...")
    
    print(f"  - Total Errors: {result.summary.total_errors}")
    print(f"  - Error Groups: {len(result.error_groups)}")
    
    # Check sheets in summary
    sheets_summary = result.metadata["sheets_summary"]
    print("\n  [Sheet Summary]")
    for sheet_name, summary in sheets_summary.items():
        print(f"    - {sheet_name}: {summary['total_errors']} errors")

    # Assertions
    errors = result.errors
    
    # Expect 2 errors: 'Male' in Production, 'Woman' in Office
    expected_errors = [
        ("Production", "Male"),
        ("Office", "Woman")
    ]
    
    found_errors = 0
    for sheet, invalid_val in expected_errors:
        matched = [e for e in errors if e.sheet == sheet and e.actual_value == invalid_val]
        if matched:
            print(f"  [PASS] Found expected error in '{sheet}': Value='{invalid_val}'")
            found_errors += 1
        else:
            print(f"  [FAIL] Missing expected error in '{sheet}': Value='{invalid_val}'")

    if found_errors == len(expected_errors):
        print("\n[SUCCESS] Multi-sheet validation logic is working correctly!")
    else:
        print("\n[FAILURE] Validation logic failed to catch all errors across sheets.")

if __name__ == "__main__":
    asyncio.run(test_multi_sheet_validation())
