# -*- coding: utf-8 -*-
import pandas as pd
import openpyxl
import sys

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("B.xlsx 파일 구조 분석")
print("=" * 80)

# B.xlsx 읽기
wb = openpyxl.load_workbook('B.xlsx')
ws = wb.active

print("\n첫 15행:")
for i, row in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True)):
    print(f"Row {i+1}: {row}")

print("\n" + "=" * 80)
print("A.xls 파일 구조 분석")
print("=" * 80)

# A.xls 읽기
df_a = pd.read_excel('_확정급여채무평가 작성요청자료A.xls')
print(f"\n컬럼: {list(df_a.columns)}")
print(f"행 수: {len(df_a)}")
print("\n첫 5행:")
print(df_a.head())
