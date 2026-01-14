"""
Common Utility Functions
========================
Shared helper functions for the DBO Validation System
"""

from typing import List, Dict, Any, Set
from collections import defaultdict
import pandas as pd
import numpy as np
from models import ValidationErrorGroup

def convert_numpy_types(obj):
    """
    Recursively convert numpy types to standard Python types for JSON serialization.
    Handles NaN/Infinity by converting to None.
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj

def group_errors(errors: list) -> List[ValidationErrorGroup]:
    """
    동일한 인지 내용을 그룹화하여 집계

    Args:
        errors: ValidationError 리스트

    Returns:
        List[ValidationErrorGroup]: 그룹화된 인지 목록
    """
    # (시트, 컬럼, 규칙ID, 메시지)를 키로 그룹화
    groups = defaultdict(list)

    for error in errors:
        key = (
            error.sheet or "",
            error.column,
            error.rule_id,
            error.message
        )
        groups[key].append(error)

    # ValidationErrorGroup 객체 생성
    error_groups = []
    for (sheet, column, rule_id, message), error_list in groups.items():
        # 행 번호 수집
        affected_rows = [e.row for e in error_list]

        # 샘플 값 수집 (최대 3개, 중복 제거)
        sample_values = []
        seen_values = set()
        for e in error_list:
            val_str = str(e.actual_value)
            if val_str not in seen_values and len(sample_values) < 3:
                sample_values.append(e.actual_value)
                seen_values.add(val_str)

        error_group = ValidationErrorGroup(
            sheet=sheet,
            column=column,
            rule_id=rule_id,
            message=message,
            affected_rows=sorted(affected_rows),
            count=len(error_list),
            sample_values=sample_values,
            expected=error_list[0].expected if error_list else None,
            source_rule=error_list[0].source_rule if error_list else ""
        )
        error_groups.append(error_group)

    # 인지 개수 많은 순으로 정렬
    error_groups.sort(key=lambda x: x.count, reverse=True)

    return error_groups
