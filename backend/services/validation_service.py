from models import ValidationRule, ValidationResponse, ValidationError, ValidationSummary, ValidationErrorGroup
from utils.common import convert_numpy_types, group_errors
import numpy as np
from datetime import datetime
from uuid import UUID, uuid4
from typing import Dict, List, Any, Optional
import json
import pandas as pd
import io

from database.rule_repository import RuleRepository
from database.validation_repository import ValidationRepository
from services.ai_cache_service import AICacheService
from rule_engine import RuleEngine

class ValidationService:
    """
    DB 기반 검증을 수행하는 서비스
    """

    def __init__(self):
        """Initialize service"""
        self.rule_repository = RuleRepository()
        self.validation_repository = ValidationRepository()
        self.ai_cache_service = AICacheService()
        self.rule_engine = RuleEngine()

    async def validate_sheets(
        self,
        sheet_data_map: Dict[str, Dict[str, Any]],
        validation_rules: List[ValidationRule]
    ) -> ValidationResponse:
        """
        공통 시트 검증 로직
        
        Args:
            sheet_data_map: Canonical Name -> { display_name, original_name, df }
            validation_rules: 적용할 규칙 리스트
            
        Returns:
            ValidationResponse: 전체 검증 결과
        """
        all_errors = []
        all_sheets_summary = {}

        # 규칙을 시트별로 그룹화
        from collections import defaultdict
        rules_by_sheet = defaultdict(list)
        for rule in validation_rules:
            rules_by_sheet[rule.source.sheet_name].append(rule)

        # 각 시트 검증
        for canonical_name, data in sheet_data_map.items():
            display_name = data["display_name"]
            df = data["df"]
            
            sheet_rules = rules_by_sheet.get(canonical_name, [])
            if not sheet_rules:
                continue
            
            errors = self.rule_engine.validate(df, sheet_rules)
            summary = self.rule_engine.get_summary(len(df), len(sheet_rules))

            for error in errors:
                error.sheet = display_name
            
            all_errors.extend(errors)
            
            all_sheets_summary[display_name] = {
                "total_rows": len(df),
                "error_rows": summary.error_rows,
                "valid_rows": summary.valid_rows,
                "total_errors": len(errors),
                "rules_applied": len(sheet_rules)
            }

        # 데이터 정제 (Numpy 타입 변환)
        cleaned_errors = []
        for err in all_errors:
            err_dict = err.dict()
            err_dict['actual_value'] = convert_numpy_types(err.actual_value)
            cleaned_errors.append(ValidationError(**err_dict))

        # 전체 요약 계산
        total_rows = sum(s["total_rows"] for s in all_sheets_summary.values())
        total_error_rows = sum(s["error_rows"] for s in all_sheets_summary.values())
        
        # 원본 시트 순서 추출 (sheet_data_map은 삽입 순서가 보장된다고 가정하거나 별도 리스트 필요)
        # sheet_data_map은 위에서 excel_file.sheet_names 순서대로 생성되었으므로 keys() 순서가 원본 순서임
        original_sheet_order = [data["display_name"] for data in sheet_data_map.values()]

        overall_summary = ValidationSummary(
            total_rows=total_rows,
            valid_rows=total_rows - total_error_rows,
            error_rows=total_error_rows,
            total_errors=len(cleaned_errors),
            rules_applied=len(validation_rules),
            timestamp=datetime.now()
        )

        # 인지 내용 집계
        error_groups = group_errors(cleaned_errors)

        return ValidationResponse(
            validation_status="PASS" if len(cleaned_errors) == 0 else "FAIL",
            summary=overall_summary,
            errors=cleaned_errors,
            error_groups=error_groups,
            rules_applied=validation_rules,
            metadata={
                "sheets_summary": all_sheets_summary,
                "sheet_order": original_sheet_order  # 원본 시트 순서 추가
            }
        )

    async def validate_with_db_rules(
        self,
        rule_file_id: str,
        employee_file_content: bytes,
        employee_file_name: str
    ) -> Dict[str, Any]:
        """
        DB에 저장된 규칙을 사용하여 데이터 검증 수행
        """
        start_time = datetime.now()

        # Step 1: 규칙 로드
        print(f"[ValidationService] Loading rules from DB: {rule_file_id}")
        validation_rules = await self.ai_cache_service.get_cached_rules_as_validation_rules(rule_file_id)

        # Step 1.5: AI 해석이 없으면 자동으로 실행
        if not validation_rules:
            print(f"[ValidationService] No AI interpreted rules found. Running auto-interpretation...")
            interpret_result = await self.ai_cache_service.interpret_and_cache_rules(rule_file_id)
            print(f"[ValidationService] Auto-interpretation completed: {interpret_result}")

            # 다시 로드
            validation_rules = await self.ai_cache_service.get_cached_rules_as_validation_rules(rule_file_id)

            if not validation_rules:
                raise ValueError("규칙 해석에 실패했습니다. 규칙 파일을 확인해주세요.")

        # Step 2: 직원 데이터 파싱
        try:
            excel_file = pd.ExcelFile(io.BytesIO(employee_file_content))
            sheet_data_map = {}
            from utils.excel_parser import normalize_sheet_name, get_canonical_name
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(io.BytesIO(employee_file_content), sheet_name=sheet_name)
                canonical_name = get_canonical_name(sheet_name)
                sheet_data_map[canonical_name] = {
                    "display_name": normalize_sheet_name(sheet_name),
                    "original_name": sheet_name,
                    "df": df
                }
        except Exception as e:
            raise ValueError(f"직원 데이터 파싱 실패: {str(e)}")

        # Step 3: 공통 검증 로직 실행
        validation_res = await self.validate_sheets(sheet_data_map, validation_rules)
        engine_duration = (datetime.now() - start_time).total_seconds()

        # Step 4: 매칭 통계 추가
        file_record = await self.rule_repository.get_rule_file(UUID(rule_file_id))
        matching_stats = {
            "matched_sheets": len(validation_res.metadata["sheets_summary"]),
            "total_rule_sheets": file_record.get('sheet_count', 0) if file_record else 0,
            "all_data_sheets": [data['display_name'] for data in sheet_data_map.values()],
            "all_rule_sheets": list(set(r.source.sheet_name for r in validation_rules))
        }
        validation_res.metadata.update({
            "employee_file_name": employee_file_name,
            "rule_file_id": rule_file_id,
            "matching_stats": matching_stats
        })

        # Step 5: 세션 저장
        session_id = str(uuid4())
        session_token = f"V-{datetime.now().strftime('%Y%m%d')}-{session_id[:8].upper()}"
        
        full_results_json = json.loads(validation_res.json())

        session_data = {
            "id": session_id,
            "session_token": session_token,
            "employee_file_name": employee_file_name,
            "rule_source_type": "database",
            "rule_file_id": rule_file_id,
            "total_rows": validation_res.summary.total_rows,
            "valid_rows": validation_res.summary.valid_rows,
            "error_rows": validation_res.summary.error_rows,
            "total_errors": validation_res.summary.total_errors,
            "rules_applied_count": validation_res.summary.rules_applied,
            "validation_status": validation_res.validation_status,
            "validation_processing_time_seconds": engine_duration,
            "full_results": full_results_json,
            "created_at": datetime.now().isoformat()
        }

        await self.validation_repository.create_session(session_data)

        # Step 6: 개별 에러 저장
        if validation_res.errors:
            error_records = [{
                "session_id": session_id,
                "sheet_name": err.sheet or "Sheet1",
                "row_number": err.row,
                "column_name": err.column,
                "rule_id": err.rule_id,
                "error_message": err.message,
                "actual_value": str(err.actual_value) if err.actual_value is not None else None,
                "expected_value": err.expected,
                "source_rule_text": err.source_rule
            } for err in validation_res.errors]
            
            await self.validation_repository.create_errors_batch(error_records)

        return {
            "status": "success",
            "session_id": session_id,
            "session_token": session_token,
            "summary": validation_res.summary.dict(),
            "total_processing_time_seconds": engine_duration
        }

    async def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """
        세션 상세 정보 조회
        """
        session = await self.validation_repository.get_session(UUID(session_id))
        if not session:
            return None
            
        errors = await self.validation_repository.get_session_errors(UUID(session_id))
        
        return {
            "session": session,
            "errors": errors
        }

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        세션 목록 조회
        """
        return await self.validation_repository.list_sessions(limit, offset)
