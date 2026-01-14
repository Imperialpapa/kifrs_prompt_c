# 📋 Phase 3 계획: AI 학습 시스템 및 DB 기반 검증

**시작 날짜**: 2025-01-13
**상태**: 🚧 진행 중
**이전 단계**: Phase 2 - 규칙 업로드/다운로드 (완료)

---

## 🎯 Phase 3 목표

1. **AI 규칙 해석 자동화**: 규칙 업로드 시 자동으로 AI 해석 및 캐싱
2. **DB 기반 검증**: 저장된 규칙으로 검증 (AI 재해석 불필요)
3. **검증 히스토리 추적**: 모든 검증 세션 저장 및 조회
4. **False Positive 피드백**: 사용자 피드백 수집 및 학습 데이터 구축

---

## 📦 구현할 기능

### 1. AI 자동 해석 (규칙 업로드 후)

**현재 상태**:
- 규칙 파일 업로드 시 `rules` 테이블에 저장만 됨
- AI 해석 컬럼(`ai_rule_id`, `ai_rule_type`, etc.)이 모두 NULL

**구현 내용**:
```python
# rule_service.py - upload_rule_file 확장
async def upload_rule_file(...):
    # 1. 기존 로직 (파일 파싱, DB 저장)

    # 2. AI 자동 해석 추가
    await self._interpret_and_cache_rules(file_id)
```

**프로세스**:
1. 업로드된 규칙을 DB에서 조회
2. `AIRuleInterpreter`로 규칙 해석
3. 해석 결과를 `rules` 테이블에 UPDATE
4. `ai_interpretation_logs` 테이블에 로그 기록

**예상 시간**: 규칙 24개 기준 ~10-20초

---

### 2. DB 기반 검증

**새 엔드포인트**: `POST /validate-with-db-rules`

**Request**:
```json
{
  "rule_file_id": "5ea221ce-8985-49cc-8412-4995e87e62b2",
  "employee_file": "<multipart/form-data>"
}
```

**프로세스**:
1. `rule_file_id`로 DB에서 규칙 조회
2. 캐시된 AI 해석 데이터 활용 (재해석 불필요)
3. `ValidationRule` 객체로 변환
4. 기존 `RuleEngine`으로 검증 실행
5. 결과 반환 + 히스토리 저장

**장점**:
- ✅ AI 재해석 불필요 (빠른 응답)
- ✅ 일관된 규칙 적용
- ✅ 규칙 버전 관리 가능

---

### 3. 검증 세션 히스토리

**테이블 활용**:
- `validation_sessions`: 세션 메타데이터
- `validation_errors`: 개별 에러 기록

**새 엔드포인트**:
- `GET /sessions` - 세션 목록
- `GET /sessions/{session_id}` - 세션 상세
- `GET /sessions/{session_id}/errors` - 세션의 에러 목록

**저장 내용**:
```python
{
    "session_id": "uuid",
    "session_token": "unique_token",
    "rule_file_id": "uuid",
    "employee_file_name": "employees.xlsx",
    "total_rows": 100,
    "error_rows": 5,
    "validation_status": "FAIL",
    "full_results": { ... },  # JSON
    "created_at": "2025-01-13T..."
}
```

---

### 4. False Positive 피드백

**UI 변경**:
- 검증 결과 화면에 "False Positive" 버튼 추가
- 사용자가 오류가 아닌 항목 표시 가능

**API 엔드포인트**:
```
POST /feedback/false-positive
{
  "session_id": "uuid",
  "error_id": "uuid",
  "user_explanation": "이 값은 정상입니다",
  "suggested_rule_adjustment": "나이 범위를 0-200으로 확장"
}
```

**테이블**:
- `false_positive_feedback`: 피드백 저장
- `rule_accuracy_metrics`: 규칙별 정확도 지표

**활용**:
- AI 프롬프트 개선
- 규칙 자동 조정 제안
- 정확도 대시보드

---

## 🏗️ 구현 순서

### Step 1: AI 자동 해석
- [ ] `services/ai_cache_service.py` 생성
- [ ] `_interpret_and_cache_rules()` 메서드 구현
- [ ] `upload_rule_file()`에 통합
- [ ] 로그 테이블 활용

### Step 2: DB 기반 검증
- [ ] `POST /validate-with-db-rules` 엔드포인트 추가
- [ ] DB 규칙 → `ValidationRule` 변환 로직
- [ ] 기존 `RuleEngine` 재사용
- [ ] 테스트

### Step 3: 검증 히스토리
- [ ] `services/session_service.py` 생성
- [ ] 세션 저장 로직 구현
- [ ] 세션 조회 API 추가
- [ ] Frontend 히스토리 탭 추가

### Step 4: False Positive 피드백
- [ ] 피드백 API 구현
- [ ] Frontend 피드백 버튼 추가
- [ ] 피드백 조회 및 통계

### Step 5: 학습 통계 대시보드
- [ ] 규칙별 정확도 조회
- [ ] False Positive 통계
- [ ] AI 학습 제안 생성

---

## 📊 데이터베이스 활용

### Phase 3에서 사용할 테이블

| 테이블 | 용도 | Phase 3 구현 |
|--------|------|--------------|
| `rules` | AI 해석 캐싱 | ✅ UPDATE (ai_* 컬럼) |
| `ai_interpretation_logs` | AI 해석 로그 | ✅ INSERT |
| `validation_sessions` | 검증 히스토리 | ✅ INSERT |
| `validation_errors` | 개별 에러 | ✅ INSERT |
| `false_positive_feedback` | 피드백 수집 | ✅ INSERT |
| `rule_accuracy_metrics` | 정확도 지표 | ✅ UPDATE |
| `user_corrections` | 사용자 수정 | ⏳ Phase 4 |

---

## 🔄 시스템 흐름

### 기존 흐름 (Phase 2)
```
Excel B → Upload → DB (rules)
                      ↓
                  (AI 해석 없음)
```

### Phase 3 흐름
```
Excel B → Upload → DB (rules)
                      ↓
                  AI 자동 해석
                      ↓
              rules 테이블 UPDATE
                      ↓
           ai_interpretation_logs

Excel A → Validate with DB rules
              ↓
          캐시된 AI 해석 재사용
              ↓
          RuleEngine 검증
              ↓
          validation_sessions + validation_errors
```

---

## 🎨 Frontend 변경사항

### 1. 규칙 관리 탭
- "AI 해석 진행 중..." 표시
- 해석 완료율 표시
- 재해석 버튼 (필요 시)

### 2. 파일 업로드 탭
- "DB 규칙 사용" 옵션 추가
- 규칙 파일 선택 드롭다운

### 3. 검증 대시보드
- 세션 히스토리 섹션
- False Positive 버튼

### 4. 새 탭: 검증 히스토리
- 과거 검증 세션 목록
- 각 세션 클릭 시 결과 재조회

---

## 🔧 기술적 고려사항

### 1. AI 해석 성능
- **문제**: 24개 규칙 해석에 10-20초 소요
- **해결**:
  - 비동기 처리 (백그라운드 작업)
  - 업로드 즉시 반환, 해석은 별도 진행
  - WebSocket으로 진행률 알림 (선택)

### 2. 규칙 버전 관리
- **문제**: 같은 규칙 파일의 여러 버전
- **해결**:
  - `rule_file_id` + `version`으로 식별
  - 검증 시 특정 버전 선택 가능

### 3. 캐시 무효화
- **문제**: 규칙 변경 시 캐시 업데이트
- **해결**:
  - 재해석 버튼 제공
  - `ai_interpreted_at` 타임스탬프 확인

---

## 📈 예상 성과

### 검증 속도 개선
- **현재**: Excel B 업로드 시마다 AI 해석 (10-20초)
- **Phase 3**: 캐시 활용 (~1-2초)
- **개선율**: ~90% 속도 향상

### 학습 데이터 수집
- 검증 세션: ~100건/월 (예상)
- False Positive 피드백: ~10-20건/월
- AI 프롬프트 개선 자료 확보

---

## 🧪 테스트 계획

### 1. AI 캐싱 테스트
- [ ] 24개 규칙 업로드 및 해석
- [ ] DB에 AI 해석 저장 확인
- [ ] 해석 로그 확인

### 2. DB 검증 테스트
- [ ] 캐시된 규칙으로 검증
- [ ] 속도 측정 (기존 vs DB)
- [ ] 결과 정확도 비교

### 3. 히스토리 테스트
- [ ] 세션 저장 확인
- [ ] 세션 조회 확인
- [ ] 에러 기록 확인

### 4. 피드백 테스트
- [ ] False Positive 제출
- [ ] 피드백 조회
- [ ] 정확도 지표 업데이트

---

## 🚀 Phase 3 완료 기준

- ✅ 규칙 업로드 시 AI 자동 해석
- ✅ DB 기반 검증 API 작동
- ✅ 검증 히스토리 저장 및 조회
- ✅ False Positive 피드백 수집
- ✅ 규칙별 정확도 지표 산출
- ✅ Frontend UI 통합

---

## 📚 참고 문서

- `PHASE1_COMPLETE.md` - DB 인프라
- `PHASE2_COMPLETE.md` - 규칙 업로드/다운로드
- `backend/database/migrations/001_initial_schema.sql` - 테이블 스키마
- `backend/ai_layer.py` - AI 규칙 해석기

---

**준비 완료!** Phase 3 구현을 시작합니다. 🚀
