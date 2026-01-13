"""
K-IFRS 1019 DBO Validation System - Rule Engine
================================================
AI가 해석한 규칙을 결정론적으로 실행하는 검증 엔진

🎯 핵심 원칙:
1. 100% 결정론적 실행 (동일 입력 → 동일 출력)
2. AI는 관여하지 않음 (규칙만 실행)
3. 감사 추적 가능 (모든 오류에 출처 명시)
4. 타입 안정성 (명확한 데이터 구조)
"""

import re
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import (
    ValidationRule,
    ValidationError,
    ValidationSummary,
    ValidationResponse
)


class RuleEngine:
    """
    결정론적 검증 엔진
    - AI가 해석한 규칙을 받아서 실제 데이터에 적용
    """
    
    def __init__(self):
        """초기화"""
        self.errors: List[ValidationError] = []
        self.row_error_flags: set = set()  # 오류가 있는 행 번호 추적
    
    def validate(
        self,
        data: pd.DataFrame,
        rules: List[ValidationRule]
    ) -> List[ValidationError]:
        """
        데이터프레임에 규칙 적용
        
        Args:
            data: 검증할 데이터프레임 (Excel A)
            rules: AI가 해석한 규칙들
            
        Returns:
            List[ValidationError]: 발견된 모든 오류
        """
        self.errors = []
        self.row_error_flags = set()
        
        for rule in rules:
            self._apply_rule(data, rule)
        
        return self.errors
    
    def _apply_rule(self, data: pd.DataFrame, rule: ValidationRule):
        """
        개별 규칙 적용
        """
        if rule.rule_type == "required":
            self._validate_required(data, rule)
        
        elif rule.rule_type == "no_duplicates":
            self._validate_no_duplicates(data, rule)
        
        elif rule.rule_type == "format":
            self._validate_format(data, rule)
        
        elif rule.rule_type == "range":
            self._validate_range(data, rule)
        
        elif rule.rule_type == "date_logic":
            self._validate_date_logic(data, rule)
        
        elif rule.rule_type == "cross_field":
            self._validate_cross_field(data, rule)
        
        elif rule.rule_type == "custom":
            self._validate_custom(data, rule)
        
        else:
            raise ValueError(f"알 수 없는 규칙 타입: {rule.rule_type}")
    
    # =========================================================================
    # 규칙 타입별 검증 메서드
    # =========================================================================
    
    def _validate_required(self, data: pd.DataFrame, rule: ValidationRule):
        """
        필수 필드 검증
        """
        field = rule.field_name
        
        if field not in data.columns:
            # 컬럼 자체가 없으면 모든 행에 대해 오류
            for idx in range(len(data)):
                self._add_error(
                    row=idx + 2,  # Excel 행 번호 (헤더 포함)
                    column=field,
                    rule=rule,
                    message=f"필수 컬럼 '{field}'가 존재하지 않습니다.",
                    actual_value=None
                )
            return
        
        # Null, NaN, 빈 문자열 체크
        for idx, value in enumerate(data[field]):
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                self._add_error(
                    row=idx + 2,
                    column=field,
                    rule=rule,
                    message=rule.error_message_template,
                    actual_value=value
                )
    
    def _validate_no_duplicates(self, data: pd.DataFrame, rule: ValidationRule):
        """
        중복 금지 검증
        """
        field = rule.field_name
        
        if field not in data.columns:
            return
        
        # 중복 찾기
        duplicates = data[data.duplicated(subset=[field], keep=False)]
        
        for idx in duplicates.index:
            value = data.loc[idx, field]
            self._add_error(
                row=idx + 2,
                column=field,
                rule=rule,
                message=rule.error_message_template,
                actual_value=value,
                expected="고유값"
            )
    
    def _validate_format(self, data: pd.DataFrame, rule: ValidationRule):
        """
        형식 검증 (regex, allowed_values 등)
        """
        field = rule.field_name
        params = rule.parameters
        
        if field not in data.columns:
            return
        
        # allowed_values 검증
        if "allowed_values" in params:
            allowed = params["allowed_values"]
            for idx, value in enumerate(data[field]):
                if pd.notna(value) and value not in allowed:
                    self._add_error(
                        row=idx + 2,
                        column=field,
                        rule=rule,
                        message=rule.error_message_template,
                        actual_value=value,
                        expected=f"{allowed} 중 하나"
                    )
        
        # regex 검증
        elif "regex" in params:
            pattern = re.compile(params["regex"])
            for idx, value in enumerate(data[field]):
                if pd.notna(value):
                    value_str = str(value)
                    if not pattern.match(value_str):
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=rule.error_message_template,
                            actual_value=value,
                            expected=params.get("format", "정규식 패턴 일치")
                        )
        
        # format 검증 (예: YYYYMMDD)
        elif "format" in params:
            fmt = params["format"]
            for idx, value in enumerate(data[field]):
                if pd.notna(value):
                    if not self._check_date_format(str(value), fmt):
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=rule.error_message_template,
                            actual_value=value,
                            expected=fmt
                        )
    
    def _validate_range(self, data: pd.DataFrame, rule: ValidationRule):
        """
        범위 검증 (숫자 또는 날짜)
        """
        field = rule.field_name
        params = rule.parameters
        
        if field not in data.columns:
            return
        
        # 날짜 범위 검증
        if "min_date" in params or "max_date" in params:
            min_date = params.get("min_date")
            max_date = params.get("max_date")
            
            for idx, value in enumerate(data[field]):
                if pd.notna(value):
                    value_str = str(value)
                    if min_date and value_str < min_date:
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=rule.error_message_template,
                            actual_value=value,
                            expected=f">= {min_date}"
                        )
                    if max_date and value_str > max_date:
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=rule.error_message_template,
                            actual_value=value,
                            expected=f"<= {max_date}"
                        )
        
        # 숫자 범위 검증
        elif "min_value" in params or "max_value" in params:
            min_val = params.get("min_value")
            max_val = params.get("max_value")
            
            for idx, value in enumerate(data[field]):
                if pd.notna(value):
                    try:
                        num_val = float(value)
                        if min_val is not None and num_val < min_val:
                            self._add_error(
                                row=idx + 2,
                                column=field,
                                rule=rule,
                                message=rule.error_message_template,
                                actual_value=value,
                                expected=f">= {min_val}"
                            )
                        if max_val is not None and num_val > max_val:
                            self._add_error(
                                row=idx + 2,
                                column=field,
                                rule=rule,
                                message=rule.error_message_template,
                                actual_value=value,
                                expected=f"<= {max_val}"
                            )
                    except (ValueError, TypeError):
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=f"숫자 형식이 아닙니다: {value}",
                            actual_value=value,
                            expected="숫자"
                        )
    
    def _validate_date_logic(self, data: pd.DataFrame, rule: ValidationRule):
        """
        날짜 논리 검증 (예: 입사일 > 생년월일)
        """
        field = rule.field_name
        params = rule.parameters
        
        if field not in data.columns:
            return
        
        compare_field = params.get("compare_field")
        operator = params.get("operator")
        
        if not compare_field or compare_field not in data.columns:
            return
        
        for idx in range(len(data)):
            value1 = data.loc[idx, field]
            value2 = data.loc[idx, compare_field]
            
            if pd.isna(value1) or pd.isna(value2):
                continue
            
            # 날짜 비교
            if operator == "greater_than":
                if str(value1) <= str(value2):
                    self._add_error(
                        row=idx + 2,
                        column=field,
                        rule=rule,
                        message=rule.error_message_template,
                        actual_value=f"{field}={value1}, {compare_field}={value2}",
                        expected=f"{field} > {compare_field}"
                    )
            
            elif operator == "less_than":
                if str(value1) >= str(value2):
                    self._add_error(
                        row=idx + 2,
                        column=field,
                        rule=rule,
                        message=rule.error_message_template,
                        actual_value=f"{field}={value1}, {compare_field}={value2}",
                        expected=f"{field} < {compare_field}"
                    )
            
            # 최소 나이 체크 (입사 시)
            if "min_age_at_hire" in params:
                min_age = params["min_age_at_hire"]
                try:
                    birth_year = int(str(value2)[:4])
                    hire_year = int(str(value1)[:4])
                    age_at_hire = hire_year - birth_year
                    
                    if age_at_hire < min_age:
                        self._add_error(
                            row=idx + 2,
                            column=field,
                            rule=rule,
                            message=f"입사 시 만 {age_at_hire}세로, 최소 만 {min_age}세 미만입니다.",
                            actual_value=f"만 {age_at_hire}세",
                            expected=f"만 {min_age}세 이상"
                        )
                except (ValueError, TypeError):
                    pass
    
    def _validate_cross_field(self, data: pd.DataFrame, rule: ValidationRule):
        """
        필드 간 교차 검증
        """
        field = rule.field_name
        params = rule.parameters
        
        if field not in data.columns:
            return
        
        reference_field = params.get("reference_field")
        condition = params.get("condition")
        
        if not reference_field or reference_field not in data.columns:
            return
        
        for idx in range(len(data)):
            value = data.loc[idx, field]
            ref_value = data.loc[idx, reference_field]
            
            if condition == "required_if_not_null":
                if pd.notna(ref_value) and pd.isna(value):
                    self._add_error(
                        row=idx + 2,
                        column=field,
                        rule=rule,
                        message=rule.error_message_template,
                        actual_value=value,
                        expected=f"{reference_field}이(가) 있을 때 필수"
                    )
    
    def _validate_custom(self, data: pd.DataFrame, rule: ValidationRule):
        """
        사용자 정의 검증
        - 복잡한 비즈니스 로직
        """
        # 예시: eval을 사용한 동적 검증 (실제로는 보안 고려 필요)
        # 여기서는 간단히 pass
        pass
    
    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================
    
    def _check_date_format(self, value: str, format_str: str) -> bool:
        """
        날짜 형식 체크
        """
        if format_str == "YYYYMMDD":
            if len(value) != 8:
                return False
            try:
                year = int(value[:4])
                month = int(value[4:6])
                day = int(value[6:8])
                # 간단한 유효성 체크
                if not (1900 <= year <= 2100):
                    return False
                if not (1 <= month <= 12):
                    return False
                if not (1 <= day <= 31):
                    return False
                # 실제 날짜 유효성
                datetime(year, month, day)
                return True
            except (ValueError, TypeError):
                return False
        
        return True
    
    def _add_error(
        self,
        row: int,
        column: str,
        rule: ValidationRule,
        message: str,
        actual_value: Any,
        expected: Optional[str] = None
    ):
        """
        오류 추가
        """
        error = ValidationError(
            row=row,
            column=column,
            rule_id=rule.rule_id,
            message=message,
            actual_value=actual_value,
            expected=expected,
            source_rule=rule.source.original_text
        )
        
        self.errors.append(error)
        self.row_error_flags.add(row)
    
    def get_summary(self, total_rows: int, rules_count: int) -> ValidationSummary:
        """
        검증 요약 통계 생성
        """
        error_rows = len(self.row_error_flags)
        
        return ValidationSummary(
            total_rows=total_rows,
            valid_rows=total_rows - error_rows,
            error_rows=error_rows,
            total_errors=len(self.errors),
            rules_applied=rules_count,
            timestamp=datetime.now()
        )


# =============================================================================
# 편의 함수
# =============================================================================

def validate_data(
    data: pd.DataFrame,
    rules: List[ValidationRule]
) -> ValidationResponse:
    """
    데이터 검증 실행 및 응답 생성
    
    Args:
        data: 검증할 데이터프레임
        rules: AI가 해석한 규칙들
        
    Returns:
        ValidationResponse: 전체 검증 결과
    """
    engine = RuleEngine()
    errors = engine.validate(data, rules)
    summary = engine.get_summary(len(data), len(rules))
    
    return ValidationResponse(
        validation_status="PASS" if len(errors) == 0 else "FAIL",
        summary=summary,
        errors=errors,
        conflicts=[],  # 규칙 충돌은 AI 레이어에서 처리
        rules_applied=rules
    )


# =============================================================================
# 테스트 코드
# =============================================================================

if __name__ == "__main__":
    import json
    from models import ValidationRule, RuleSource
    
    # 샘플 데이터
    sample_data = pd.DataFrame({
        "employee_id": ["E001", "E002", "E003", "E002", ""],
        "birth_date": ["19850315", "1990-05-20", "19920708", "19880101", "19950101"],
        "hire_date": ["20100101", "20150601", "20200101", "20120101", "20180101"],
        "gender": ["M", "F", "M", "X", "F"]
    })
    
    # 샘플 규칙
    sample_rules = [
        ValidationRule(
            rule_id="RULE_001",
            field_name="employee_id",
            rule_type="required",
            parameters={},
            error_message_template="사번이 비어있습니다.",
            source=RuleSource(
                original_text="사번: 공백 없음",
                sheet_name="rules",
                row_number=2
            ),
            ai_interpretation_summary="사번 필수",
            confidence_score=0.99
        ),
        ValidationRule(
            rule_id="RULE_002",
            field_name="employee_id",
            rule_type="no_duplicates",
            parameters={},
            error_message_template="사번이 중복되었습니다.",
            source=RuleSource(
                original_text="사번: 중복 없음",
                sheet_name="rules",
                row_number=2
            ),
            ai_interpretation_summary="사번 고유",
            confidence_score=0.99
        ),
        ValidationRule(
            rule_id="RULE_003",
            field_name="birth_date",
            rule_type="format",
            parameters={"format": "YYYYMMDD", "regex": "^[0-9]{8}$"},
            error_message_template="생년월일 형식이 잘못되었습니다.",
            source=RuleSource(
                original_text="생년월일: YYYYMMDD",
                sheet_name="rules",
                row_number=3
            ),
            ai_interpretation_summary="날짜 형식",
            confidence_score=0.99
        ),
        ValidationRule(
            rule_id="RULE_004",
            field_name="gender",
            rule_type="format",
            parameters={"allowed_values": ["M", "F", "남", "여"]},
            error_message_template="성별 값이 올바르지 않습니다.",
            source=RuleSource(
                original_text="성별: M/F/남/여",
                sheet_name="rules",
                row_number=4
            ),
            ai_interpretation_summary="성별 허용값",
            confidence_score=0.99
        )
    ]
    
    # 검증 실행
    result = validate_data(sample_data, sample_rules)
    print(json.dumps(result.dict(), indent=2, ensure_ascii=False, default=str))
