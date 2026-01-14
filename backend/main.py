"""
K-IFRS 1019 DBO Validation System - FastAPI Backend
===================================================
전체 시스템을 통합하는 웹 API

Endpoints:
- POST /upload: 파일 업로드
- POST /validate: 검증 실행
- GET /health: 헬스체크
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
import os
from typing import List, Dict, Any
import traceback
from datetime import datetime

from models import (
    ValidationResponse,
    AIInterpretationResponse,
    RuleConflict,
    ValidationErrorGroup,
    RuleFileUpload,
    RuleFileResponse,
    RuleUpdate,
    RuleDetail,
    FalsePositiveFeedback
)
from ai_layer import AIRuleInterpreter
from rule_engine import RuleEngine
from services.rule_service import RuleService
from services.ai_cache_service import AICacheService
from services.validation_service import ValidationService
from services.feedback_service import FeedbackService
from services.statistics_service import StatisticsService
from utils.excel_parser import parse_rules_from_excel, normalize_sheet_name, get_canonical_name
from utils.common import group_errors

# =============================================================================
# FastAPI 앱 초기화
# =============================================================================

app = FastAPI(
    title="K-IFRS 1019 DBO Validation System",
    description="AI-Powered Data Validation for Defined Benefit Obligations",
    version="1.0.0"
)

# CORS 설정 (모바일에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 전역 상태
# =============================================================================

ai_interpreter = AIRuleInterpreter()
rule_service = RuleService()
ai_cache_service = AICacheService()
validation_service = ValidationService()
feedback_service = FeedbackService()
statistics_service = StatisticsService()


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """
    Serve the frontend index.html
    """
    # Check if index.html exists in parent or current dir
    if os.path.exists("../index.html"):
        return FileResponse("../index.html")
    elif os.path.exists("index.html"):
        return FileResponse("index.html")
    
    return {
        "service": "K-IFRS 1019 DBO Validation System",
        "version": "1.4.1",
        "status": "operational (Frontend file not found)"
    }


@app.get("/api")
async def api_info():
    """
    API info endpoint
    """
    return {
        "service": "K-IFRS 1019 DBO Validation System",
        "version": "1.4.1",
        "build_date": "2025-01-13 15:00:00",
        "status": "operational",
        "features": [
            "다중 시트 검증 지원 (자동 매핑)",
            "인지 항목 집계",
            "동적 AI 규칙 생성",
            "규칙 편집기 (Rule Editor)"
        ]
    }


@app.get("/health")
async def health_check():
    """
    헬스체크
    """
    return {
        "status": "healthy",
        "ai_layer": "operational",
        "rule_engine": "operational"
    }


@app.get("/version")
async def get_version():
    """버전 정보 조회"""
    import sys
    import platform
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "system_version": "1.2.6",
        "build_date": now_str,
        "build_time": now_str,
        "server_start_time": now_str,
        "python_version": sys.version,
        "platform": platform.platform(),
        "features": {
            "multi_sheet_validation": True,
            "error_grouping": True,
            "dynamic_rule_generation": True,
            "excel_download": True,
            "fuzzy_sheet_matching": True,
            "sheet_matching_stats": True
        }
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate_data(
    employee_file: UploadFile = File(..., description="직원 데이터 파일 (Excel A)"),
    rules_file: UploadFile = File(..., description="검증 규칙 파일 (Excel B)")
):
    """
    데이터 검증 실행
    
    Process:
    1. Excel A (직원 데이터) 읽기
    2. Excel B (자연어 규칙) 읽기
    3. AI에게 규칙 해석 요청
    4. 결정론적 엔진으로 검증 실행
    5. 결과 반환
    """
    try:
        # =====================================================================
        # Step 1: Excel A 읽기 (직원 데이터) - 다중 시트 지원
        # =====================================================================
        print("[Step 1] Reading employee data...")
        employee_content = await employee_file.read()

        # 모든 시트 읽기
        excel_file = pd.ExcelFile(io.BytesIO(employee_content))
        
        # 통합 데이터 맵: Canonical Name -> { display_name, original_name, df }
        # 이것이 시트 데이터 조회 및 매칭의 Single Source of Truth가 됩니다.
        sheet_data_map = {}
        sheet_mapping_info = {} # Debug info for logging

        print(f"   [INFO] Raw sheet names in file: {excel_file.sheet_names}")

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(io.BytesIO(employee_content), sheet_name=sheet_name)
            
            # 이름 변환
            norm_name = normalize_sheet_name(sheet_name)
            canonical_name = get_canonical_name(sheet_name)
            
            sheet_data_map[canonical_name] = {
                "display_name": norm_name,
                "original_name": sheet_name,
                "df": df
            }
            sheet_mapping_info[canonical_name] = sheet_name
            
            print(f"   [OK] Loaded sheet '{sheet_name}' -> canonical '{canonical_name}': {len(df)} rows")

        print(f"[OK] Loaded {len(sheet_data_map)} sheets from employee file")
        
        # =====================================================================
        # Step 2: Excel B 읽기 (자연어 규칙)
        # =====================================================================
        print("\n[Step 2] Reading validation rules...")
        rules_content = await rules_file.read()

        # 헬퍼 함수를 사용하여 규칙 파싱 (로직 통합)
        natural_language_rules, sheet_row_counts, total_raw_rows, reported_max_row = parse_rules_from_excel(rules_content)

        # 디버깅: 시트별 규칙 개수 출력
        from collections import Counter
        sheet_counts = Counter(r['display_sheet_name'] for r in natural_language_rules)
        print(f"[OK] Loaded {len(natural_language_rules)} validation rules from {len(sheet_counts)} sheets:")
        for sheet, count in sheet_counts.items():
            print(f"   - '{sheet}': {count} rules")

        # [수정] 매칭 통계 계산을 위한 리스트 미리 정의 (Step 5에서 사용)
        # 필터링 전의 전체 시트 목록(sheet_row_counts)을 기준으로 합니다.
        all_rule_sheets_display_unfiltered = sorted(list(sheet_row_counts.keys()))
        all_rule_sheets_canonical_unfiltered = [get_canonical_name(name) for name in all_rule_sheets_display_unfiltered]

        # =====================================================================
        # Step 3: AI 규칙 해석
        # =====================================================================
        print("\n[Step 3] AI interpreting rules...")
        ai_response: AIInterpretationResponse = await ai_interpreter.interpret_rules(
            natural_language_rules
        )

        print(f"[OK] AI interpreted {len(ai_response.rules)} rules")
        print(f"[WARN] Detected {len(ai_response.conflicts)} conflicts")

        # =====================================================================
        # Step 4: 결정론적 검증 실행 - 시트별 처리 (통합 매칭 로직 적용)
        # =====================================================================
        print("\n[Step 4] Running deterministic validation...")
        validation_res = await validation_service.validate_sheets(sheet_data_map, ai_response.rules)

        # =====================================================================
        # Step 5: 응답 생성 및 메타데이터 추가
        # =====================================================================
        # AI 규칙 개수 집계 (시트별 - Canonical Name 기준)
        from collections import Counter
        rule_counts_by_canonical = Counter(rule.source.sheet_name for rule in ai_response.rules)

        # 매칭 연산
        data_sheets_set = set(sheet_data_map.keys())
        rule_sheets_set = set(all_rule_sheets_canonical_unfiltered)
        
        matched_sheets_set = data_sheets_set.intersection(rule_sheets_set)
        unmatched_sheets_set = rule_sheets_set - data_sheets_set
        
        matched_sheets_count = len(matched_sheets_set)
        
        # 매칭 안 된 시트들의 Display Name 찾기
        unmatched_sheet_names = []
        for c_name in unmatched_sheets_set:
            d_name = next((d for d in all_rule_sheets_display_unfiltered if get_canonical_name(d) == c_name), c_name)
            unmatched_sheet_names.append(d_name)

        all_data_sheets = sorted(list(sheet_mapping_info.values()))

        # 드롭다운 표시용 문자열 생성: "시트명 (N행 / M규칙)"
        display_list = []
        for d_name in all_rule_sheets_display_unfiltered:
            c_name = get_canonical_name(d_name)
            raw_rows_in_sheet = sheet_row_counts.get(d_name, 0)
            rule_count_in_sheet = rule_counts_by_canonical.get(c_name, 0)
            display_list.append(f"{d_name} ({raw_rows_in_sheet}행 / {rule_count_in_sheet}규칙)")

        matching_stats = {
            "total_rule_sheets": len(all_rule_sheets_canonical_unfiltered),
            "matched_sheets": matched_sheets_count,
            "unmatched_sheet_names": unmatched_sheet_names,
            "all_rule_sheets": display_list,
            "all_data_sheets": all_data_sheets,
            "total_raw_rows": total_raw_rows, 
            "reported_max_row": reported_max_row,
            "total_rules_count": len(ai_response.rules)
        }

        # 최종 응답 객체 완성
        validation_res.conflicts = ai_response.conflicts
        validation_res.metadata.update({
            "employee_file_name": employee_file.filename,
            "rules_file_name": rules_file.filename,
            "ai_model_version": "claude-sonnet-4-20250514",
            "system_version": "1.0.0",
            "ai_processing_time_seconds": ai_response.processing_time_seconds,
            "total_errors": validation_res.summary.total_errors,
            "errors_shown": min(validation_res.summary.total_errors, 200),
            "error_groups_count": len(validation_res.error_groups),
            "matching_stats": matching_stats
        })

        print("\n[OK] Response ready")
        return validation_res

    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Validation failed",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@app.post("/interpret-rules")
async def interpret_rules_only(
    rules_file: UploadFile = File(..., description="검증 규칙 파일 (Excel B)")
):
    """
    규칙만 해석 (검증 실행 없이)
    - 디버깅 및 규칙 검토용
    """
    try:
        # Excel B 읽기
        rules_content = await rules_file.read()
        
        # 헬퍼 함수 사용하여 규칙 파싱 (로직 통합)
        natural_language_rules, _, _, _ = parse_rules_from_excel(rules_content)
        
        # AI 해석
        ai_response = await ai_interpreter.interpret_rules(natural_language_rules)
        
        return {
            "status": "success",
            "rules_count": len(ai_response.rules),
            "conflicts_count": len(ai_response.conflicts),
            "rules": [rule.dict() for rule in ai_response.rules],
            "conflicts": [conflict.dict() for conflict in ai_response.conflicts],
            "summary": ai_response.ai_summary
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Rule interpretation failed",
                "message": str(e)
            }
        )


@app.get("/kifrs-references")
async def get_kifrs_references():
    """
    K-IFRS 1019 참조 정보 조회
    """
    from models import KIFRS_1019_REFERENCES
    return KIFRS_1019_REFERENCES


# =============================================================================
# Rule Management Endpoints (Phase 2)
# =============================================================================

@app.post("/rules/upload-to-db", response_model=RuleFileResponse)
async def upload_rule_file_to_db(
    rules_file: UploadFile = File(..., description="검증 규칙 파일 (Excel B)"),
    file_version: str = "1.0",
    uploaded_by: str = "system",
    notes: str = None
):
    """
    규칙 파일을 데이터베이스에 업로드

    Process:
    1. Excel B 파일 파싱
    2. rule_files 테이블에 메타데이터 저장
    3. rules 테이블에 개별 규칙 배치 저장
    4. 저장된 파일 정보 반환

    Args:
        rules_file: Excel 규칙 파일
        file_version: 파일 버전 (기본값: "1.0")
        uploaded_by: 업로드한 사용자 (기본값: "system")
        notes: 추가 메모

    Returns:
        RuleFileResponse: 저장된 규칙 파일 메타데이터
    """
    try:
        print(f"[API] Uploading rule file: {rules_file.filename}")

        # Read file content
        content = await rules_file.read()

        # Create metadata
        metadata = RuleFileUpload(
            file_name=rules_file.filename,
            file_version=file_version,
            uploaded_by=uploaded_by,
            notes=notes
        )

        # Upload using service
        response = await rule_service.upload_rule_file(content, metadata)

        print(f"[API] Successfully uploaded rule file: {response.id}")
        return response

    except Exception as e:
        print(f"[API] Error uploading rule file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to upload rule file",
                "message": str(e)
            }
        )


@app.get("/rules/files", response_model=List[RuleFileResponse])
async def list_rule_files(
    status: str = "active",
    limit: int = 50,
    offset: int = 0
):
    """
    저장된 규칙 파일 목록 조회

    Args:
        status: 필터링할 상태 (기본값: "active")
        limit: 최대 결과 수 (기본값: 50)
        offset: 페이지네이션 오프셋 (기본값: 0)

    Returns:
        List[RuleFileResponse]: 규칙 파일 목록
    """
    try:
        print(f"[API] Listing rule files (status={status}, limit={limit}, offset={offset})")
        files = await rule_service.list_rule_files(status, limit, offset)
        return files

    except Exception as e:
        print(f"[API] Error listing rule files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to list rule files",
                "message": str(e)
            }
        )


@app.get("/rules/files/{file_id}")
async def get_rule_file_details(file_id: str):
    """
    규칙 파일 상세 정보 조회

    Args:
        file_id: 규칙 파일 UUID

    Returns:
        Dict: 파일 메타데이터, 통계, 시트별 규칙 정보
    """
    try:
        print(f"[API] Getting rule file details: {file_id}")
        details = await rule_service.get_rule_file_details(file_id)

        if not details:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Rule file not found",
                    "file_id": file_id
                }
            )

        return details

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error getting rule file details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to get rule file details",
                "message": str(e)
            }
        )


@app.get("/rules/download/{file_id}")
async def download_rule_file(file_id: str):
    """
    데이터베이스에서 규칙을 Excel 파일로 다운로드

    Args:
        file_id: 규칙 파일 UUID

    Returns:
        Excel 파일 (StreamingResponse)
    """
    try:
        print(f"[API] Downloading rule file: {file_id}")

        # Export rules to Excel
        excel_bytes = await rule_service.export_rules_to_excel(file_id)
        print(f"[API] Excel generated: {len(excel_bytes)} bytes")

        # Get file metadata for filename
        try:
            details = await rule_service.get_rule_file_details(file_id)
            original_filename = details['file_name'] if details else 'rules.xlsx'
        except Exception as e:
            print(f"[API] Warning: Could not get file details, using default filename: {e}")
            original_filename = 'rules.xlsx'

        # Remove extension if exists
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename

        # Create download filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_exported_{timestamp}.xlsx"

        print(f"[API] Sending file: {filename}")

        # Create response with proper headers
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(excel_bytes)),
                "Cache-Control": "no-cache"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error downloading rule file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to download rule file",
                "message": str(e),
                "file_id": file_id
            }
        )


@app.post("/rules/interpret/{file_id}")
async def interpret_rules(file_id: str, force_reinterpret: bool = False):
    """
    규칙 파일의 AI 해석 실행 또는 재해석

    Args:
        file_id: 규칙 파일 UUID
        force_reinterpret: True면 기존 해석 무시하고 재해석

    Returns:
        Dict: 해석 결과 통계
    """
    try:
        print(f"[API] Starting AI interpretation for file: {file_id} (force={force_reinterpret})")

        result = await ai_cache_service.interpret_and_cache_rules(file_id, force_reinterpret)

        print(f"[API] AI interpretation completed")
        return {
            "status": "success",
            "file_id": file_id,
            **result
        }

    except Exception as e:
        print(f"[API] Error during AI interpretation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to interpret rules",
                "message": str(e),
                "file_id": file_id
            }
        )


@app.get("/rules/{rule_id}", response_model=RuleDetail)
async def get_rule_detail(rule_id: str):
    """
    개별 규칙 상세 정보 조회
    """
    try:
        rule = await rule_service.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/rules/{rule_id}")
async def update_rule(rule_id: str, updates: RuleUpdate):
    """
    개별 규칙 수정
    """
    try:
        success = await rule_service.update_rule(rule_id, updates.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found or no changes made")
        return {"status": "success", "message": "Rule updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, permanent: bool = False):
    """
    개별 규칙 삭제 (기본값: 비활성화)
    """
    try:
        success = await rule_service.delete_rule(rule_id, permanent)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"status": "success", "message": "Rule deleted/deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Validation Session Endpoints (Phase 3)
# =============================================================================

@app.post("/validate-with-db-rules")
async def validate_with_db_rules(
    rule_file_id: str,
    employee_file: UploadFile = File(..., description="직원 데이터 파일 (Excel A)")
):
    """
    DB에 저장된 규칙을 사용하여 데이터 검증 수행

    Args:
        rule_file_id: 규칙 파일 UUID
        employee_file: 직원 데이터 파일

    Returns:
        Dict: 검증 결과 요약 및 세션 ID
    """
    try:
        print(f"[API] Validating with DB rules: {rule_file_id}")
        
        # Read file content
        content = await employee_file.read()
        
        result = await validation_service.validate_with_db_rules(
            rule_file_id=rule_file_id,
            employee_file_content=content,
            employee_file_name=employee_file.filename
        )
        
        return result

    except ValueError as ve:
        print(f"[API] Validation error: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation failed",
                "message": str(ve)
            }
        )
    except Exception as e:
        print(f"[API] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Validation failed",
                "message": str(e)
            }
        )


@app.get("/sessions")
async def list_validation_sessions(
    limit: int = 50,
    offset: int = 0
):
    """
    검증 세션 목록 조회
    """
    try:
        sessions = await validation_service.list_sessions(limit, offset)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@app.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    세션 상세 정보 및 에러 목록 조회
    """
    try:
        details = await validation_service.get_session_details(session_id)
        if not details:
            raise HTTPException(status_code=404, detail="Session not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@app.post("/feedback/false-positive")
async def submit_false_positive_feedback(feedback: FalsePositiveFeedback):
    """
    False Positive 피드백 제출
    """
    try:
        result = await feedback_service.submit_false_positive_feedback(feedback)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@app.get("/statistics/dashboard")
async def get_dashboard_statistics():
    """
    대시보드 통계 조회
    """
    try:
        return await statistics_service.get_dashboard_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@app.post("/download-results")
async def download_validation_results(validation_response: ValidationResponse):
    """
    검증 결과를 Excel 파일로 다운로드

    Args:
        validation_response: 검증 결과 데이터

    Returns:
        Excel 파일 (StreamingResponse)
    """
    try:
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. 요약 시트
            summary_data = {
                "항목": ["검증 상태", "전체 행 수", "정상 행 수", "오류 행 수", "총 오류 수", "적용된 규칙 수", "검증 시각"],
                "값": [
                    validation_response.validation_status,
                    validation_response.summary.total_rows,
                    validation_response.summary.valid_rows,
                    validation_response.summary.error_rows,
                    validation_response.summary.total_errors,
                    validation_response.summary.rules_applied,
                    validation_response.summary.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name="검증 요약", index=False)

            # 2. 인지 항목 집계 시트
            if validation_response.error_groups:
                groups_data = []
                for group in validation_response.error_groups:
                    rows_str = ', '.join(map(str, group.affected_rows[:20]))
                    if len(group.affected_rows) > 20:
                        rows_str += f" 외 {len(group.affected_rows) - 20}개"

                    groups_data.append({
                        "시트명": group.sheet,
                        "열": group.column,
                        "규칙ID": group.rule_id,
                        "인지 메시지": group.message,
                        "인지 횟수": group.count,
                        "영향받은 행": rows_str,
                        "샘플 값": ", ".join(map(str, group.sample_values)),
                        "예상 값": group.expected or "",
                        "원본 규칙": group.source_rule
                    })
                df_groups = pd.DataFrame(groups_data)
                df_groups.to_excel(writer, sheet_name="인지 항목 집계", index=False)

            # 3. 개별 인지 목록 시트
            if validation_response.errors:
                errors_data = []
                for error in validation_response.errors:
                    errors_data.append({
                        "시트명": error.sheet or "",
                        "행": error.row,
                        "열": error.column,
                        "규칙ID": error.rule_id,
                        "인지 메시지": error.message,
                        "실제 값": str(error.actual_value),
                        "예상 값": error.expected or "",
                        "원본 규칙": error.source_rule
                    })
                df_errors = pd.DataFrame(errors_data)
                df_errors.to_excel(writer, sheet_name="개별 인지 목록", index=False)

            # 4. 규칙 충돌 시트
            if validation_response.conflicts:
                conflicts_data = []
                for conflict in validation_response.conflicts:
                    conflicts_data.append({
                        "규칙ID": conflict.rule_id,
                        "충돌 유형": conflict.conflict_type,
                        "설명": conflict.description,
                        "K-IFRS 1019 참조": conflict.kifrs_reference or "",
                        "영향받는 규칙": ", ".join(conflict.affected_rules),
                        "권장사항": conflict.recommendation,
                        "심각도": conflict.severity
                    })
                df_conflicts = pd.DataFrame(conflicts_data)
                df_conflicts.to_excel(writer, sheet_name="규칙 충돌", index=False)

            # 5. 적용된 규칙 시트
            if validation_response.rules_applied:
                rules_data = []
                for rule in validation_response.rules_applied:
                    rules_data.append({
                        "규칙ID": rule.rule_id,
                        "시트명": rule.source.sheet_name,
                        "필드명": rule.field_name,
                        "규칙 유형": rule.rule_type,
                        "파라미터": str(rule.parameters),
                        "오류 메시지": rule.error_message_template,
                        "원본 규칙": rule.source.original_text,
                        "신뢰도": rule.confidence_score
                    })
                df_rules = pd.DataFrame(rules_data)
                df_rules.to_excel(writer, sheet_name="적용된 규칙", index=False)

        output.seek(0)

        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DBO_Validation_Results_{timestamp}.xlsx"

        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate Excel file",
                "message": str(e)
            }
        )


# =============================================================================
# 예외 핸들러
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    전역 예외 핸들러
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


# =============================================================================
# 서버 실행 (개발용)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
    =================================================================
      K-IFRS 1019 DBO Validation System
      AI-Powered Data Validation for Defined Benefit Obligations
    =================================================================

    Starting server...
    Mobile-optimized UI available at: http://localhost:8000
    API Documentation: http://localhost:8000/docs

    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )