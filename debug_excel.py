
import pandas as pd
import sys
import os

# Add backend to path to import utils
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.excel_parser import parse_rules_from_excel

def debug_file(filename):
    print(f"=== Debugging {filename} ===")
    if not os.path.exists(filename):
        print("File not found!")
        return

    try:
        # 1. Read raw with pandas
        print("\n[Raw Content Preview (First 10 rows)]")
        df = pd.read_excel(filename, header=None, nrows=10)
        print(df)

        # 2. Check Sheet Names
        xl = pd.ExcelFile(filename)
        print(f"\n[Sheet Names]: {xl.sheet_names}")

        # 3. Test Parser (only if it looks like a rule file)
        # Assuming rule file has '시트명' or similar in first few rows
        # But let's just try parsing it using our utility
        with open(filename, 'rb') as f:
            content = f.read()
            rules, counts, raw_rows, max_rows = parse_rules_from_excel(content)
            
            print(f"\n[Parser Result]")
            print(f"Total Rules: {len(rules)}")
            print(f"Sheet Counts: {counts}")
            print(f"Raw Rows Scanned: {raw_rows}")
            
            print("\n[First 5 Rules]")
            for r in rules[:5]:
                print(r)
            
            # Check for specific sheet (2-3)
            target_sheet = "(2-3) 퇴직자 및 DC전환자 명부"
            print(f"\n[Searching for sheet: {target_sheet}]")
            found = [r for r in rules if target_sheet in r['display_sheet_name']]
            print(f"Found {len(found)} rules for target sheet.")
            if found:
                print("Sample:", found[0])

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

print("Checking C.xlsx...")
debug_file("C.xlsx")

print("\nChecking A.xls (Employee Data)...")
debug_file("A.xls")
