import pandas as pd
import io
import re
import sys

# Encoding setup
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_sheet_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    normalized = name.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()

def get_canonical_name(name: str) -> str:
    norm = normalize_sheet_name(name)
    return "".join(norm.split())

def debug_rules_parsing():
    print("Reading B.xlsx...")
    # Read the file
    all_rules_sheets = pd.read_excel('B.xlsx', header=None, engine='openpyxl', sheet_name=None)
    
    natural_language_rules = []
    
    print(f"Found {len(all_rules_sheets)} sheets in file: {list(all_rules_sheets.keys())}")

    for rule_sheet_name, rules_df in all_rules_sheets.items():
        print(f"\nProcessing sheet: '{rule_sheet_name}' (Rows: {len(rules_df)})")
        
        # Original Logic: Forward Fill
        if len(rules_df) > 2:
            rules_df.iloc[2:, 1] = rules_df.iloc[2:, 1].ffill()

        sheet_rules_count = 0
        for idx, row in rules_df.iterrows():
            if idx < 2: continue

            num_cols = len(row)
            # Logic from backend/main.py
            raw_sheet_name = row.iloc[1] if num_cols > 1 and pd.notna(row.iloc[1]) else ""
            condition = row.iloc[5] if num_cols > 5 and pd.notna(row.iloc[5]) else ""

            # Check for "해당없음"
            if condition and "해당없음" in str(condition):
                print(f"  Row {idx}: Skipped due to condition '해당없음' (Sheet: {raw_sheet_name})")
                continue
            
            # Additional debug info for first few rows
            if idx < 5:
                print(f"  Row {idx}: raw_sheet_name='{raw_sheet_name}'")

            if raw_sheet_name:
                rule_entry = {
                    "display_sheet_name": normalize_sheet_name(raw_sheet_name),
                }
                natural_language_rules.append(rule_entry)
                sheet_rules_count += 1
        
        print(f"  -> Extracted {sheet_rules_count} rules from this sheet")

    # Resulting unique sheets
    unique_sheets = sorted(list(set(r['display_sheet_name'] for r in natural_language_rules)))
    print("\n[RESULT] Unique Sheet Names Found in Rules:")
    for s in unique_sheets:
        print(f" - {s}")

if __name__ == "__main__":
    debug_rules_parsing()
