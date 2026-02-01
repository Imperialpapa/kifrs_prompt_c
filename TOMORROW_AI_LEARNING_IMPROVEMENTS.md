# AI 학습 시스템 개선 제안

> 작성일: 2026-02-01
> 목적: 내일 작업 시 바로 참조하여 진행

---

## 현재 시스템 요약

### 핵심 파일
- `backend/services/learning_service.py` - 학습 서비스 메인
- `backend/database/migrations/002_learning_tables.sql` - DB 스키마

### 현재 기능
| 기능 | 상태 | 평가 |
|------|------|------|
| 패턴 저장/검색 | 2단계 캐싱(메모리+DB) | ⭐⭐⭐⭐ |
| 유사도 계산 | Jaccard+TF-IDF+Levenshtein 하이브리드 | ⭐⭐⭐⭐ |
| 피드백 수집 | success/failure 기본 | ⭐⭐⭐ |
| 자동 학습 | 조건 기반 자동 패턴화 | ⭐⭐⭐⭐ |
| **필드명 활용** | **거의 미사용** | ⭐⭐ |
| **대규모 확장성** | **500개 이상 시 성능 저하** | ⭐⭐⭐ |

---

## 우선순위별 개선 제안

### 1. 높음 (1~2일) - 즉시 효과

#### 1-1. 필드명 기반 필터링 추가

**문제**: 현재 `find_matching_pattern()`에서 `field_name`은 참고용만, 검색에 미반영
- "사원번호" 규칙과 "입사일자" 규칙이 구분 안 됨

**수정 위치**: `learning_service.py` - `find_matching_pattern()` 메서드 (~321행)

**수정 방안**:
```python
async def find_matching_pattern(self, rule_text: str, field_name: str = "", threshold: float = 0.8):
    # 1단계: 같은 필드의 패턴에서 우선 검색
    if field_name:
        field_patterns = self.client.table('rule_patterns') \
            .select('*') \
            .eq('field_name_hint', field_name) \
            .eq('is_active', True) \
            .execute()

        if field_patterns.data:
            best_match = self._find_best_match(field_patterns.data, rule_text, threshold)
            if best_match:
                return best_match

    # 2단계: 없으면 전체에서 검색 (기존 로직)
    return await self._find_global_match(rule_text, threshold)
```

**효과**: 검색 정확도 향상, 오탐 감소

---

#### 1-2. 패턴 인덱싱 개선

**문제**: 검색 시마다 최대 500개 패턴 로드

**수정 방안**: 인메모리 인덱스 구조 개선
```python
class PatternIndex:
    def __init__(self):
        self._by_field = {}      # field_name → [patterns]
        self._by_type = {}       # rule_type → [patterns]
        self._hash_index = {}    # pattern_hash → pattern
        self._last_sync = None

    async def refresh_if_stale(self, max_age_seconds=3600):
        if self._last_sync is None or (time.time() - self._last_sync) > max_age_seconds:
            await self._load_all_patterns()
```

---

### 2. 중간 (2~3일)

#### 2-1. AI 신뢰도를 초기 confidence에 반영

**문제**: 모든 새 패턴이 0.95로 시작 (AI 신뢰도 무시)

**수정 위치**: `save_learned_pattern()` 메서드 (~213행)

**수정 방안**:
```python
async def save_learned_pattern(
    self,
    rule_text: str,
    field_name: str,
    ai_rule_type: str,
    ai_parameters: Dict,
    ai_error_message: str = "",
    source_rule_id: str = None,
    confidence_boost: float = 0.0,
    source_ai_confidence: float = None  # 추가
):
    # AI 신뢰도를 초기값에 반영
    if source_ai_confidence is not None:
        base_confidence = min(0.95, source_ai_confidence)
    else:
        base_confidence = 0.95  # 사용자 확정의 경우

    confidence_score = min(1.0, base_confidence + confidence_boost)
```

---

#### 2-2. 패턴 복구 메커니즘

**문제**: `is_active=False` 되면 복구 불가

**수정 방안**: status enum 도입
```sql
-- 마이그레이션
ALTER TABLE rule_patterns
ADD COLUMN status VARCHAR(20) DEFAULT 'active';
-- 'active', 'inactive', 'archived', 'blacklisted'

-- is_active 컬럼은 하위 호환성 위해 유지
UPDATE rule_patterns SET status = CASE
    WHEN is_active = true THEN 'active'
    ELSE 'inactive'
END;
```

```python
async def reactivate_pattern(self, pattern_id: str) -> bool:
    """비활성화된 패턴 다시 활성화"""
    result = self.client.table('rule_patterns') \
        .update({"status": "active", "is_active": True}) \
        .eq('id', pattern_id) \
        .execute()
    return bool(result.data)
```

---

#### 2-3. 피드백 세분화

**문제**: success/failure 2단계만 존재

**수정 방안**: 5단계로 세분화
```python
async def record_validation_result_enhanced(self, ...):
    error_rate = error_count / total_rows

    if error_rate < 0.02:
        feedback_type = "excellent"
        confidence_delta = +0.01
    elif error_rate < 0.05:
        feedback_type = "success"
        confidence_delta = +0.005
    elif error_rate < 0.10:
        feedback_type = "acceptable"
        confidence_delta = 0.0
    elif error_rate < 0.20:
        feedback_type = "warning"
        confidence_delta = -0.01
    else:
        feedback_type = "failure"
        confidence_delta = -0.02
```

---

### 3. 낮음 (필요 시)

#### 3-1. 컨텍스트 기반 유사도 가중치 조정

```python
def _calculate_similarity_adaptive(self, text1, text2, field_type=None):
    if field_type == "date":
        weights = {"jaccard": 0.20, "tfidf": 0.30, "levenshtein": 0.50}
    elif field_type == "numeric":
        weights = {"jaccard": 0.25, "tfidf": 0.50, "levenshtein": 0.25}
    else:
        weights = {"jaccard": 0.30, "tfidf": 0.40, "levenshtein": 0.30}
    # ...
```

#### 3-2. 패턴 클러스터링 (패밀리 그룹화)

- "값은 0 이상 100 이하"와 "값은 0 이상 150 이하"를 같은 패밀리로 그룹화
- 관련 패턴들의 통계 통합

---

## 작업 순서 제안

```
Day 1 (오전)
├── 1-1. 필드명 기반 필터링 구현
└── 테스트

Day 1 (오후)
├── 1-2. 패턴 인덱싱 개선
└── 테스트

Day 2
├── 2-1. AI 신뢰도 반영
├── 2-2. 패턴 복구 메커니즘 (DB 마이그레이션 포함)
└── 통합 테스트

Day 3 (선택)
├── 2-3. 피드백 세분화
└── UI 반영 (필요 시)
```

---

## 테스트 방법

```bash
# 학습 서비스 단위 테스트
cd backend
python -m pytest tests/test_learning_cycle.py -v

# 또는 직접 테스트
python -c "
from services.learning_service import LearningService
service = LearningService()

# 패턴 저장 테스트
await service.save_learned_pattern(
    rule_text='YYYYMMDD',
    field_name='입사일자',
    ai_rule_type='format',
    ai_parameters={'format': 'YYYYMMDD'},
)

# 패턴 검색 테스트 (필드명 필터링)
result = await service.find_matching_pattern('YYYYMMDD', field_name='입사일자')
print(result)
"
```

---

## 참고: 현재 학습 데이터 흐름

```
사용자 규칙 업로드
    ↓
AI 해석 (ai_layer.py)
    ↓
Smart Interpret (learning_service)
├── 학습된 패턴 있음 → 즉시 반환
└── 없음 → AI 해석 사용
    ↓
사용자 규칙 확정 (PUT /rules/{id})
    → save_learned_pattern() 호출
    ↓
검증 실행 (POST /validate)
    → record_validation_result() 호출
    → auto_learn_from_validation() 호출
    ↓
유지보수 (POST /learning/maintenance)
    → 저신뢰 패턴 비활성화
    → 고성공률 패턴 확정
```

---

## 관련 파일 위치

| 파일 | 설명 |
|------|------|
| `backend/services/learning_service.py` | 학습 서비스 메인 (1123줄) |
| `backend/main.py` | API 엔드포인트 (학습 관련 ~1519행) |
| `backend/database/migrations/002_learning_tables.sql` | DB 스키마 |
| `backend/tests/test_learning_cycle.py` | 테스트 코드 |
| `index.html` | 프론트엔드 (학습 대시보드) |

---

Good luck tomorrow!
