"""
Fuzzy Field Matching Utility
============================
규칙의 항목명과 데이터 파일의 컬럼명을 유연하게 매칭하는 유틸리티
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd

class FieldMatcher:
    """
    규칙 필드명과 데이터 컬럼명 간의 퍼지 매칭을 수행합니다.
    """
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        # 자주 사용되는 매핑 사전 (학습 효과)
        self.hard_mappings = {
            "사원번호": "사번",
            "사번": "사원번호",
            "성명": "이름",
            "이름": "성명",
            "생년월일": "생일",
            "주민번호": "주민등록번호",
            "입사일자": "입사일",
            "퇴사일자": "퇴사일",
            "평균임금": "평균급여",
            "급여": "임금"
        }

    def normalize(self, text: str) -> str:
        """텍스트 정규화 (공백 제거, 소문자화, 설명 부분 제거)"""
        if not text:
            return ""
        
        # 1. 줄바꿈 및 탭을 공백으로 치환
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # 2. 첫 번째 괄호'(' 이후의 내용은 설명(코드값 등)이므로 과감히 제거
        # 예: "종업원 구분(1:직원, 3:임원..." -> "종업원 구분"
        if '(' in text:
            text = text.split('(')[0]
            
        # 3. 특수문자 및 공백 제거, 소문자화
        return re.sub(r'[^a-zA-Z0-9가-힣]', '', text).lower()

    def calculate_similarity(self, a: str, b: str) -> float:
        """두 문자열 간의 유사도 계산 (0.0 ~ 1.0)"""
        norm_a = self.normalize(a)
        norm_b = self.normalize(b)
        
        if not norm_a or not norm_b:
            return 0.0
            
        if norm_a == norm_b:
            return 1.0
            
        # 부분 일치 가중치
        if norm_a in norm_b or norm_b in norm_a:
            return 0.9
            
        return SequenceMatcher(None, norm_a, norm_b).ratio()

    def find_best_column(self, rule_field: str, data_columns: List[str]) -> Tuple[Optional[str], float]:
        """
        데이터 컬럼 목록에서 규칙 필드명과 가장 유사한 컬럼을 찾습니다.
        """
        if not rule_field or not data_columns:
            return None, 0.0
            
        # 1. 완전 일치 확인
        if rule_field in data_columns:
            return rule_field, 1.0
            
        # 2. 정규화 후 완전 일치 확인
        norm_rule_field = self.normalize(rule_field)
        for col in data_columns:
            if norm_rule_field == self.normalize(col):
                return col, 0.95
                
        # 3. 핵심 키워드(괄호 앞부분) 매칭 강화
        # 규칙 항목명이나 데이터 컬럼명 중 하나라도 괄호가 있다면 괄호 앞만 따서 비교
        core_rule_field = rule_field.split('(')[0].strip() if '(' in rule_field else rule_field
        norm_core_rule = self.normalize(core_rule_field)
        
        for col in data_columns:
            core_col = col.split('(')[0].split('\n')[0].strip()
            if norm_core_rule == self.normalize(core_col):
                return col, 0.92 # 상당히 높은 신뢰도
        
        # 4. 하드 매핑 확인 (기존 로직 유지)
        if rule_field in self.hard_mappings:
            target = self.hard_mappings[rule_field]
            if target in data_columns:
                return target, 0.95
            norm_target = self.normalize(target)
            for col in data_columns:
                if norm_target == self.normalize(col):
                    return col, 0.9
        
        # 5. 유사도 매칭 (Fuzzy)
        best_col = None
        max_score = 0.0
        
        for col in data_columns:
            score = self.calculate_similarity(rule_field, col)
            if score > max_score:
                max_score = score
                best_col = col
                
        if max_score >= self.threshold:
            return best_col, max_score
            
        return None, 0.0

    def match_rules_to_columns(self, rules: List[Any], data_columns: List[str]) -> Dict[str, str]:
        """
        규칙 필드명들을 실제 데이터 컬럼명들로 매핑하는 맵을 생성합니다.
        """
        mapping = {}
        for rule in rules:
            field = rule.field_name
            if field not in mapping:
                matched_col, score = self.find_best_column(field, data_columns)
                if matched_col:
                    mapping[field] = matched_col
        return mapping
