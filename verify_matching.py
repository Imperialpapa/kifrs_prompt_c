import pandas as pd
import io
import re
import sys

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def normalize_sheet_name(name: str) -> str:
    """
    백엔드와 동일한 정규화 로직
    """
    if not isinstance(name, str):
        return str(name)
    
    # 공백 및 제어 문자 제거 (이스케이프 문자 주의)
    normalized = name.replace('\n', '').replace('\r', '').replace('\t', '')
    
    # 연속된 공백 제거
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()

print("=" * 60)
print("시트 이름 매칭 시뮬레이션 (정규화 로직 적용)")
print("=" * 60)

# 1. A.xls (데이터 파일) 분석
print("\n[1] A.xls (직원 데이터) 시트 분석")
try:
    xl_a = pd.ExcelFile('A.xls')
    sheets_a = xl_a.sheet_names
    
    norm_sheets_a = {}
    for s in sheets_a:
        norm = normalize_sheet_name(s)
        norm_sheets_a[norm] = s
        print(f"  - 원본: '{s}'")
        print(f"    변환: '{norm}'")
        
except Exception as e:
    print(f"  [ERROR] A.xls 읽기 실패: {e}")
    sheets_a = []
    norm_sheets_a = {}

# 2. B.xlsx (규칙 파일) 분석
print("\n[2] B.xlsx (검증 규칙) 시트 분석")
try:
    # 헤더 없는 상태로 읽어서 2번째 컬럼(시트명) 확인
    df_b = pd.read_excel('B.xlsx', header=None)
    
    rule_sheets_original = set()
    
    # 데이터 행 순회 (헤더 제외)
    for idx, row in df_b.iterrows():
        if idx < 2: continue # 0, 1행 건너뜀
        
        sheet_val = row.iloc[1] # B열: 시트명
        field_val = row.iloc[3] # D열: 항목명
        
        if pd.notna(sheet_val) and pd.notna(field_val):
            rule_sheets_original.add(str(sheet_val))
            
    norm_rule_sheets = {}
    for s in rule_sheets_original:
        norm = normalize_sheet_name(s)
        norm_rule_sheets[norm] = s
        print(f"  - 원본: '{s}'")
        print(f"    변환: '{norm}'")

except Exception as e:
    print(f"  [ERROR] B.xlsx 읽기 실패: {e}")
    norm_rule_sheets = {}

# 3. 매칭 결과 확인
print("\n[3] 매칭 결과 (A.xls <-> B.xlsx)")
print("-" * 60)

matched_count = 0
unmatched_rules = []

# 규칙 파일(B)에 정의된 시트가 데이터 파일(A)에 존재하는지 확인
for norm_rule, orig_rule in norm_rule_sheets.items():
    if norm_rule in norm_sheets_a:
        print(f"[매칭 성공] '{orig_rule}' -> A 파일의 '{norm_sheets_a[norm_rule]}' 시트와 연결됨")
        matched_count += 1
    else:
        print(f"[매칭 실패] '{orig_rule}' -> A 파일에서 찾을 수 없음 (정규화: '{norm_rule}')")
        unmatched_rules.append(orig_rule)

print("-" * 60)
print(f"총 {len(norm_rule_sheets)}개의 규칙 시트 중 {matched_count}개가 매칭되었습니다.")

if matched_count == 3:
    print("\n=> 결론: 3개 시트 모두 정상적으로 매칭됩니다.")
    print("   백엔드 검증 로직은 3개 시트 모두 수행할 것입니다.")
    print("   만약 화면에 1개만 나온다면, 프론트엔드 표시 문제일 가능성이 높습니다.")
else:
    print(f"\n=> 결론: {matched_count}개 시트만 매칭됩니다.")
    print("   아직 시트 이름 불일치 문제가 완전히 해결되지 않았을 수 있습니다.")
