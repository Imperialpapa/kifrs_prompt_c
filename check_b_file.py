import pandas as pd
import sys

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("B.xlsx 파일 구조 분석")
print("=" * 80)

try:
    # B.xlsx 읽기 - 모든 시트 확인
    xl = pd.ExcelFile('B.xlsx')
    print(f"\n시트명: {xl.sheet_names}")

    for sheet_name in xl.sheet_names:
        print(f"\n{'='*80}")
        print(f"시트: {sheet_name}")
        print(f"{'='*80}")

        df = pd.read_excel('B.xlsx', sheet_name=sheet_name, header=None)
        print(f"행 수: {len(df)}")
        print("\n첫 5행:")
        print(df.head(5))

except Exception as e:
    print(f"에러 발생: {e}")
