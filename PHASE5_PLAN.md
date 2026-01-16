# 🧠 Phase 5: AI 스마트 수정 & 자가 학습 시스템 (Self-Evolving System)

**목표**: 단순 검증을 넘어, AI가 오류 수정을 제안하고 사용자의 선택을 학습하여 시스템을 지속적으로 진화시킴.

---

## 📅 상세 구현 계획

### Step 1: 학습 데이터 기반 마련 (Foundation)
- [ ] **DB 스키마 확장**: `user_corrections` 테이블을 AI 학습용으로 최적화
    - 기존 단순 로그용에서 '학습 데이터셋' 형태로 활용하기 위한 인덱싱 및 필드 추가
- [ ] **Data Models**: Backend Pydantic 모델 업데이트 (`FixSuggestion`, `BatchFixRequest`)

### Step 2: AI 수정 제안 엔진 (The Brain)
- [ ] **FixService 구현**:
    - `suggest_fixes(errors)`: 오류 목록을 받아 AI에게 수정안 요청
    - **Prompt Engineering**: 규칙 문맥 + **과거 수정 이력(Few-shot)** 을 조합한 동적 프롬프트 구성
- [ ] **학습 루프 (Feedback Loop)**:
    - 사용자가 수정을 '승인'하거나 '직접 수정'할 때마다 `user_corrections`에 가중치 부여하여 저장

### Step 3: 엑셀 생성 및 다운로드 (The Hands)
- [ ] **Excel Modifier**:
    - `openpyxl`을 사용하여 메모리 상에서 원본 엑셀 수정
    - 스타일(폰트, 색상) 유지하며 값만 안전하게 변경
- [ ] **Stream Response**: 수정된 파일을 서버에 저장하지 않고 즉시 다운로드 스트림으로 제공

### Step 4: UI/UX (The Face)
- [ ] **수정 제안 모달**:
    - [오류 값] ➡️ [AI 제안 값] (신뢰도 %) 형태의 직관적 UI
    - 체크박스로 일괄 선택/해제
- [ ] **직접 수정 기능**: AI 제안이 틀렸을 경우 사용자가 텍스트박스에서 바로 수정 (이것이 학습 데이터가 됨)

---

## 🌟 기대 효과 (Scenario)

1. **초기**: AI가 "YYYY-MM-DD" 형식을 "YYYYMMDD"로 바꾸라고 제안 (일반 상식 기반)
2. **사용자 행동**: AI가 "미상"을 못 고치자, 사용자가 수동으로 "99999999"로 입력 후 저장.
3. **학습 후**: 다음 데이터에서 "미상"이 나오면, AI가 **"과거에 '99999999'로 수정하셨습니다. 적용할까요?"** 라고 제안 (신뢰도 99%).

