"""
K-IFRS 1019 DBO Validation System - AI Interpretation Layer
============================================================
AI는 오직 규칙 해석만 수행하며, 실제 데이터 검증은 하지 않음

🔒 AI의 역할 (STRICT):
1. Excel B의 자연어 규칙 → 구조화된 Rule JSON 변환
2. 규칙 간 충돌 감지
3. K-IFRS 1019와의 충돌 감지
4. 해석 근거 제공

🚫 AI가 하지 않는 것:
- 직접 데이터 검증
- 임의의 회계 판단
- 비결정론적 검증 결과 생성
"""

import json
import re
from typing import List, Dict, Any
from models import (
    AIInterpretationRequest,
    AIInterpretationResponse,
    ValidationRule,
    RuleConflict,
    RuleSource,
    KIFRS_1019_REFERENCES
)
import time


class AIRuleInterpreter:
    """
    AI 규칙 해석기
    - Anthropic Claude API 호출하여 자연어 규칙을 구조화
    """
    
    def __init__(self, api_key: str = None):
        """
        초기화
        
        Note: claude.ai 환경에서는 API 키 불필요 (자동 처리)
        """
        self.api_key = api_key
        self.model = "claude-sonnet-4-20250514"
    
    async def interpret_rules(
        self, 
        natural_language_rules: List[Dict[str, Any]]
    ) -> AIInterpretationResponse:
        """
        자연어 규칙을 구조화된 JSON으로 변환
        
        Args:
            natural_language_rules: Excel B에서 읽은 자연어 규칙들
            
        Returns:
            AIInterpretationResponse: 해석된 규칙 + 충돌 보고서
        """
        start_time = time.time()
        
        # AI 프롬프트 구성 (실제 API 호출 시 사용)
        prompt = self._build_interpretation_prompt(natural_language_rules)
        
        # AI 호출 (실제 구현에서는 Anthropic API 호출)
        # 시뮬레이션을 위해 natural_language_rules 객체를 직접 전달
        ai_response = await self._call_claude_api(prompt, natural_language_rules)
        
        # 응답 파싱
        rules, conflicts = self._parse_ai_response(ai_response)
        
        processing_time = time.time() - start_time
        
        return AIInterpretationResponse(
            rules=rules,
            conflicts=conflicts,
            ai_summary=self._generate_summary(rules, conflicts),
            processing_time_seconds=processing_time
        )
    
    def _build_interpretation_prompt(
        self, 
        natural_language_rules: List[Dict[str, Any]]
    ) -> str:
        """
        AI 해석을 위한 프롬프트 생성
        """
        kifrs_context = json.dumps(KIFRS_1019_REFERENCES, indent=2, ensure_ascii=False)
        rules_text = json.dumps(natural_language_rules, indent=2, ensure_ascii=False)
        
        prompt = f"""
당신은 K-IFRS 1019 (퇴직급여) 전문가이자 데이터 검증 시스템 설계자입니다.

🎯 **당신의 임무**:
아래 자연어 검증 규칙들을 구조화된 JSON 형태로 변환하세요.
이 규칙들은 나중에 결정론적 검증 엔진에서 실행됩니다.

📋 **Excel B 파일 구조 설명**:
- 시트명: 검증할 Excel A 파일의 시트 이름 (예: "(2-2) 재직자 명부")
- 열명: Excel의 열 문자 (예: B, C, D, ...)
- 항목명: 실제 컬럼명 (예: "사원번호", "생년월일", "성별")
- 검증 룰: 자연어로 작성된 검증 규칙 (예: "공백, 중복", "8자리 TEXT로 년월일(YYYYMMDD) 포맷")
- 조건: "정상", "오류", "해당없음" 등
- 비고: 추가 설명

🔍 **K-IFRS 1019 참조 정보**:
```json
{kifrs_context}
```

📋 **변환할 자연어 규칙들**:
다음은 Excel B 파일에서 읽은 규칙들입니다:
```json
{rules_text}
```

📐 **출력 형식**:
각 규칙을 다음 JSON 구조로 변환하세요:

```json
{{
  "rules": [
    {{
      "rule_id": "RULE_001",
      "field_name": "employee_id",
      "rule_type": "required|no_duplicates|format|range|date_logic|cross_field|custom",
      "parameters": {{
        // 규칙 타입에 따라 다름
        // 예: {{"format": "YYYYMMDD"}}
        // 예: {{"min_value": 0, "max_value": 150}}
        // 예: {{"compare_field": "birth_date", "operator": "greater_than"}}
      }},
      "error_message_template": "구체적인 오류 메시지",
      "source": {{
        "original_text": "원본 자연어 규칙",
        "sheet_name": "시트명",
        "row_number": 행번호,
        "kifrs_reference": "관련 K-IFRS 조항 (있다면)"
      }},
      "ai_interpretation_summary": "이 규칙을 어떻게 해석했는지 설명",
      "confidence_score": 0.95
    }}
  ],
  "conflicts": [
    {{
      "rule_id": "충돌이 발견된 규칙 ID",
      "conflict_type": "rule_contradiction|kifrs_mismatch|ambiguous_interpretation",
      "description": "충돌 상세 설명",
      "kifrs_reference": "관련 K-IFRS 조항",
      "affected_rules": ["관련된 다른 규칙들"],
      "recommendation": "해결 방안 제안",
      "severity": "high|medium|low"
    }}
  ]
}}
```

⚠️ **중요 지침**:
1. **K-IFRS 1019와의 충돌 감지**: 규칙이 K-IFRS 1019 기준과 맞지 않으면 conflicts에 보고
2. **규칙 간 충돌 감지**: 상호 모순되는 규칙이 있으면 conflicts에 보고
3. **명확성 우선**: 애매한 규칙은 ambiguous_interpretation으로 보고
4. **결정론적 실행 가능**: parameters는 코드가 직접 실행 가능해야 함
5. **감사 추적**: 모든 해석에 근거와 출처를 명시

🔥 **규칙 타입별 파라미터 예시**:

- **required**: {{}} (파라미터 없음)
- **no_duplicates**: {{}} (파라미터 없음)
- **format**: {{"format": "YYYYMMDD"}} 또는 {{"regex": "^[0-9]{{8}}$"}}
- **range**: {{"min_value": 18, "max_value": 100}}
- **date_logic**: {{"compare_field": "birth_date", "operator": "greater_than"}}
- **cross_field**: {{"reference_field": "salary", "condition": "required_if_not_null"}}
- **custom**: {{"expression": "age >= 18 and age <= 65"}}

응답은 반드시 순수 JSON만 반환하세요. 설명이나 마크다운 없이.
"""
        return prompt
    
    async def _call_claude_api(self, prompt: str, natural_language_rules: List[Dict[str, Any]] = None) -> str:
        """
        Claude API 호출

        실제 구현에서는 Anthropic API를 호출합니다.
        여기서는 데모를 위해 샘플 응답을 반환합니다.
        """
        # 실제 구현:
        # import anthropic
        # client = anthropic.Anthropic(api_key=self.api_key)
        # message = client.messages.create(
        #     model=self.model,
        #     max_tokens=4000,
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # return message.content[0].text

        # 데모용 샘플 응답 - 동적으로 프롬프트의 규칙을 반영
        return self._get_dynamic_sample_response(prompt, natural_language_rules)
    
    def _get_dynamic_sample_response(self, prompt: str, natural_language_rules: List[Dict[str, Any]] = None) -> str:
        """
        동적 샘플 응답 생성
        입력된 규칙 리스트를 기반으로 JSON으로 변환
        """
        if not natural_language_rules:
            raise ValueError("No natural language rules provided for interpretation.")

        # 동적으로 ValidationRule 생성
        rules = []
        rule_counter = 1

        for nat_rule in natural_language_rules:
            sheet = nat_rule.get('sheet', '')
            field = nat_rule.get('field', '')
            rule_text = nat_rule.get('rule_text', '')
            condition = nat_rule.get('condition', '')
            note = nat_rule.get('note', '')
            row_num = nat_rule.get('row', 0)

            if not field or not rule_text:
                continue

            # "공백, 중복"은 두 개의 규칙으로 분리
            if "공백" in rule_text and "중복" in rule_text:
                # required 규칙
                rules.append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "field_name": field,
                    "rule_type": "required",
                    "parameters": {},
                    "error_message_template": f"{field}이(가) 비어있습니다.",
                    "source": {
                        "original_text": rule_text,
                        "sheet_name": sheet,
                        "row_number": row_num,
                        "kifrs_reference": None
                    },
                    "ai_interpretation_summary": f"{field} 필드는 필수",
                    "confidence_score": 0.99
                })
                rule_counter += 1

                # no_duplicates 규칙
                rules.append({
                    "rule_id": f"RULE_{rule_counter:03d}",
                    "field_name": field,
                    "rule_type": "no_duplicates",
                    "parameters": {},
                    "error_message_template": f"{field}이(가) 중복되었습니다.",
                    "source": {
                        "original_text": rule_text,
                        "sheet_name": sheet,
                        "row_number": row_num,
                        "kifrs_reference": None
                    },
                    "ai_interpretation_summary": f"{field}은(는) 고유해야 하며 중복 불가",
                    "confidence_score": 0.99
                })
                rule_counter += 1
                continue

            # 규칙 텍스트 분석하여 타입 결정
            rule_type, parameters, error_msg = self._analyze_rule_text(rule_text, field)

            rule = {
                "rule_id": f"RULE_{rule_counter:03d}",
                "field_name": field,
                "rule_type": rule_type,
                "parameters": parameters,
                "error_message_template": error_msg,
                "source": {
                    "original_text": rule_text,
                    "sheet_name": sheet,
                    "row_number": row_num,
                    "kifrs_reference": None
                },
                "ai_interpretation_summary": f"{field} 필드에 대한 {rule_type} 검증",
                "confidence_score": 0.95
            }
            rules.append(rule)
            rule_counter += 1

        return json.dumps({
            "rules": rules,
            "conflicts": []
        }, ensure_ascii=False)

    def _analyze_rule_text(self, rule_text: str, field_name: str) -> tuple:
        """
        규칙 텍스트를 분석하여 타입, 파라미터, 에러 메시지 생성
        """
        rule_text_lower = rule_text.lower()

        # YYYYMMDD 형식
        if "yyyymmdd" in rule_text_lower or "년월일" in rule_text:
            return "format", {"format": "YYYYMMDD", "regex": "^[0-9]{8}$"}, \
                   f"{field_name} 형식이 잘못되었습니다. YYYYMMDD 8자리 숫자여야 합니다."

        # 숫자 목록 (1, 2, 3 등)
        if re.search(r'\d+\s*,\s*\d+', rule_text):
            values = re.findall(r'\d+', rule_text)
            return "format", {"allowed_values": values}, \
                   f"{field_name}은(는) {', '.join(values)} 중 하나여야 합니다."

        # 비교 연산 (A > B)
        if ">" in rule_text:
            parts = rule_text.split(">")
            if len(parts) == 2:
                field1 = parts[0].strip()
                field2 = parts[1].strip()
                return "date_logic", {"compare_field": field2, "operator": "greater_than"}, \
                       f"{field1}은(는) {field2}보다 이후여야 합니다."

        # 범위 (< 0, >= 0)
        if "<" in rule_text and "0" in rule_text:
            return "range", {"min_value": 0}, \
                   f"{field_name}은(는) 0 이상이어야 합니다."

        # 기본값
        return "custom", {"expression": rule_text}, \
               f"{field_name} 검증 실패: {rule_text}"


    
    def _parse_ai_response(self, ai_response: str) -> tuple[List[ValidationRule], List[RuleConflict]]:
        """
        AI 응답 파싱
        """
        try:
            data = json.loads(ai_response)
            
            rules = [ValidationRule(**rule) for rule in data["rules"]]
            conflicts = [RuleConflict(**conflict) for conflict in data.get("conflicts", [])]
            
            return rules, conflicts
        except Exception as e:
            raise ValueError(f"AI 응답 파싱 실패: {str(e)}")
    
    def _generate_summary(
        self, 
        rules: List[ValidationRule], 
        conflicts: List[RuleConflict]
    ) -> str:
        """
        전체 해석 요약 생성
        """
        high_confidence = sum(1 for r in rules if r.confidence_score >= 0.95)
        medium_confidence = sum(1 for r in rules if 0.8 <= r.confidence_score < 0.95)
        low_confidence = sum(1 for r in rules if r.confidence_score < 0.8)
        
        summary = f"""
AI 규칙 해석 완료

📊 **통계**:
- 총 규칙 수: {len(rules)}개
- 높은 신뢰도 (≥95%): {high_confidence}개
- 중간 신뢰도 (80-95%): {medium_confidence}개
- 낮은 신뢰도 (<80%): {low_confidence}개
- 충돌 감지: {len(conflicts)}건

⚠️ **주의사항**:
"""
        
        if conflicts:
            summary += "\n- 규칙 충돌이 발견되었습니다. conflicts 섹션을 확인하세요."
        
        if low_confidence > 0:
            summary += f"\n- {low_confidence}개 규칙의 신뢰도가 낮습니다. 검토가 필요합니다."
        
        if not conflicts and low_confidence == 0:
            summary += "\n- 모든 규칙이 명확하게 해석되었으며, 충돌이 없습니다."
        
        return summary.strip()


# =============================================================================
# 유틸리티 함수
# =============================================================================

async def interpret_excel_b_rules(
    natural_language_rules: List[Dict[str, Any]]
) -> AIInterpretationResponse:
    """
    Excel B의 자연어 규칙을 해석하는 편의 함수
    
    Args:
        natural_language_rules: Excel B에서 읽은 규칙들
        
    Returns:
        AIInterpretationResponse: 해석 결과
    """
    interpreter = AIRuleInterpreter()
    return await interpreter.interpret_rules(natural_language_rules)


# =============================================================================
# 테스트/데모 코드
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # 샘플 자연어 규칙
    sample_rules = [
        {
            "sheet": "validation_rules",
            "row": 2,
            "field": "employee_id",
            "rule_text": "사번: 공백 없음, 중복 없음"
        },
        {
            "sheet": "validation_rules",
            "row": 3,
            "field": "birth_date",
            "rule_text": "생년월일은 YYYYMMDD 형식"
        },
        {
            "sheet": "validation_rules",
            "row": 4,
            "field": "birth_date",
            "rule_text": "생년월일은 1920년 이후, 2007년 이전"
        },
        {
            "sheet": "validation_rules",
            "row": 5,
            "field": "hire_date",
            "rule_text": "입사일은 생년월일보다 이후, 최소 만 15세"
        },
        {
            "sheet": "validation_rules",
            "row": 6,
            "field": "gender",
            "rule_text": "성별: M, F, 남, 여만 허용"
        }
    ]
    
    async def test():
        result = await interpret_excel_b_rules(sample_rules)
        print(json.dumps(result.dict(), indent=2, ensure_ascii=False))
    
    asyncio.run(test())
