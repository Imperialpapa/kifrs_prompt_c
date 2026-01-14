# K-IFRS 1019 DBO 검증 시스템 사용 가이드

## 빠른 시작

### 1. 서버 시작

```bash
cd backend
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 2. 웹 브라우저에서 접속

브라우저에서 `http://localhost:8000`을 엽니다.

### 3. 파일 업로드

1. **A 파일 (A.xls)**: 직원 데이터 파일
   - 다중 시트 지원
   - 주요 시트: "(2-2) 재직자 명부", "(2-3) 퇴직자 및 DC전환자 명부" 등

2. **B 파일 (B.xlsx)**: 검증 규칙 파일
   - 구조: [시트명, 열명, 항목명, 검증 룰, 조건, 비고]
   - 예시:
     ```
     시트명: (2-2) 재직자 명부
     열명: B
     항목명: 사원번호
     검증 룰: 공백, 중복
     조건: 오류
     ```

### 4. 검증 실행

"검증 시작" 버튼을 클릭하면:
- AI가 B 파일의 자연어 규칙을 해석
- 시트별로 A 파일의 데이터를 검증
- 결과를 대시보드에 표시

### 5. 결과 확인

대시보드에서 다음을 확인할 수 있습니다:
- **전체 검증 결과**: PASS/FAIL 상태
- **시트별 요약**: 각 시트의 오류 현황
- **오류 목록**: 상세 오류 내역 (시트명, 행, 열, 메시지 등)
- **규칙 충돌**: K-IFRS 1019와의 충돌 경고

### 6. 결과 다운로드

"결과 Excel 다운로드" 버튼을 클릭하면:
- Excel 파일 (.xlsx)로 다운로드
- 4개 시트:
  1. 검증 요약
  2. 오류 목록
  3. 규칙 충돌
  4. 적용된 규칙

---

## API 엔드포인트

### POST /validate

직원 데이터 검증 실행

**요청**:
- `employee_file`: A.xls 파일 (multipart/form-data)
- `rules_file`: B.xlsx 파일 (multipart/form-data)

**응답**: ValidationResponse JSON

```json
{
  "validation_status": "PASS" | "FAIL",
  "summary": {
    "total_rows": 1250,
    "valid_rows": 1180,
    "error_rows": 70,
    "total_errors": 95,
    "rules_applied": 12
  },
  "errors": [...],
  "conflicts": [...],
  "metadata": {
    "sheets_summary": {
      "(2-2) 재직자 명부": {
        "total_rows": 750,
        "error_rows": 45,
        "valid_rows": 705,
        "total_errors": 60,
        "rules_applied": 7
      }
    }
  }
}
```

### POST /download-results

검증 결과를 Excel로 다운로드

**요청**: ValidationResponse JSON
**응답**: Excel 파일 (.xlsx)

### GET /health

헬스체크

**응답**:
```json
{
  "status": "healthy",
  "ai_layer": "operational",
  "rule_engine": "operational"
}
```

---

## B 파일 (검증 규칙) 작성 가이드

### 파일 구조

| 시트명 | 열명 | 항목명 | 검증 룰 | 조건 | 비고 |
|--------|------|--------|---------|------|------|
| (2-2) 재직자 명부 | B | 사원번호 | 공백, 중복 | 오류 | |
| (2-2) 재직자 명부 | C | 생년월일 | 8자리 TEXT로 년월일(YYYYMMDD) 포맷 | 정상 | |
| (2-2) 재직자 명부 | D | 성별 | 1, 2 | 정상 | 1:남자, 2:여자 |

### 검증 룰 작성 예시

1. **필수 필드 + 중복 금지**
   ```
   공백, 중복
   ```

2. **날짜 형식**
   ```
   8자리 TEXT로 년월일(YYYYMMDD) 포맷
   ```

3. **허용 값 지정**
   ```
   1, 2, 3
   ```

4. **날짜 논리**
   ```
   입사일자 > 생년월일
   ```

5. **범위 검증**
   ```
   퇴직금추계액 >= 0
   ```

### AI가 해석하는 규칙 타입

- **required**: 필수 필드
- **no_duplicates**: 중복 금지
- **format**: 형식 검증 (날짜, 숫자, 허용값 등)
- **range**: 범위 검증 (최소/최대값)
- **date_logic**: 날짜 논리 (A > B 등)
- **cross_field**: 필드 간 검증

---

## 문제 해결

### 서버 시작 오류

**문제**: `ModuleNotFoundError: No module named 'fastapi'`

**해결**:
```bash
cd backend
pip install -r requirements.txt
```

### 파일 업로드 오류

**문제**: "파일 형식 오류"

**해결**:
- A 파일은 .xls 또는 .xlsx
- B 파일은 .xlsx
- 파일이 손상되지 않았는지 확인

### 검증 오류가 너무 많음

**문제**: 수백 개의 오류 발생

**해결**:
1. B 파일의 규칙을 재확인
2. A 파일의 데이터 형식 확인 (예: 날짜가 YYYYMMDD 형식인지)
3. 시트별 요약에서 어느 시트에 문제가 많은지 확인

### AI 규칙 해석 오류

**문제**: "신뢰도가 낮습니다" 경고

**해결**:
- B 파일의 규칙을 더 명확하게 작성
- 예시 추가 또는 구체적인 값 명시

---

## 고급 사용법

### curl을 사용한 API 호출

```bash
curl -X POST "http://localhost:8000/validate" \
  -F "employee_file=@A.xls" \
  -F "rules_file=@B.xlsx" \
  -o result.json
```

### Python으로 API 호출

```python
import requests

files = {
    'employee_file': open('A.xls', 'rb'),
    'rules_file': open('B.xlsx', 'rb')
}

response = requests.post('http://localhost:8000/validate', files=files)
result = response.json()

print(f"검증 상태: {result['validation_status']}")
print(f"총 오류: {result['summary']['total_errors']}")
```

---

## 주의사항

1. **개인정보 보호**: 민감한 데이터는 익명화 권장
2. **파일 크기**: 대용량 파일(10MB 이상)은 처리 시간이 오래 걸릴 수 있음
3. **K-IFRS 1019 충돌**: 충돌 경고가 있으면 회계법인과 협의 필요
4. **데이터 형식**: 날짜는 YYYYMMDD, 숫자는 숫자 형식으로 저장

---

## 지원

문제가 발생하면 다음을 확인하세요:
1. 서버 로그 (`backend/main.py` 실행 화면)
2. 브라우저 콘솔 (F12)
3. API 문서 (`http://localhost:8000/docs`)
