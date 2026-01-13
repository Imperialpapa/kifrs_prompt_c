# -*- coding: utf-8 -*-
import pandas as pd
import sys

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("A.xls 파일 구조 분석")
print("=" * 80)

# A.xls 읽기 - 모든 시트 확인
xl = pd.ExcelFile('A.xls')
print(f"\n시트명: {xl.sheet_names}")

for sheet_name in xl.sheet_names:
    print(f"\n{'='*80}")
    print(f"시트: {sheet_name}")
    print(f"{'='*80}")

    df = pd.read_excel('A.xls', sheet_name=sheet_name)
    print(f"컬럼: {list(df.columns)}")
    print(f"행 수: {len(df)}")
    print("\n첫 3행:")
    print(df.head(3))
