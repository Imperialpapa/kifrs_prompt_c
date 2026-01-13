import sys
import os
import io

# backend 폴더를 모듈 경로에 추가
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.main import parse_rules_from_excel

def test_parsing():
    print("=" * 60)
    print("규칙 파일(B.xlsx) 읽기 테스트 실행")
    print("=" * 60)
    
    file_path = 'B.xlsx'
    
    if not os.path.exists(file_path):
        print(f"오류: {file_path} 파일이 현재 폴더에 없습니다.")
        return

    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            
        print(f"파일 읽기 완료: {len(content)} bytes")
        
        # 실제 파싱 함수 호출
        rules, sheet_counts, total_rows = parse_rules_from_excel(content)
        
        print("\n" + "=" * 60)
        print("최종 파싱 결과")
        print("-" * 60)
        print(f"1. 전체 읽은 데이터 행 수 (total_raw_rows): {total_rows}")
        print(f"2. 유효한 규칙으로 변환된 개수: {len(rules)}")
        print(f"3. 시트별 통계:")
        for sheet, count in sheet_counts.items():
            print(f"   - {sheet}: {count}행")
        print("=" * 60)
        
        if total_rows < 24:
            print(f"\n팩트 체크: 실제 행이 24개인데 {total_rows}개만 읽혔습니다.")
            print("=> 원인: openpyxl의 Max Row 인식이 실제와 다릅니다.")
        else:
            print("\n팩트 체크: 행은 24개 다 읽었으나 규칙 변환 과정에서 제외되었습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parsing()
