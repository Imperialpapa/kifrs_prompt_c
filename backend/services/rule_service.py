"""
Rule Service - Business Logic Layer
====================================
규칙 파일 업로드, 다운로드, 조회 등의 비즈니스 로직 처리
"""

import io
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from database.rule_repository import RuleRepository
from utils.excel_parser import parse_rules_from_excel, normalize_sheet_name, get_canonical_name
from models import RuleFileUpload, RuleFileResponse
from services.ai_cache_service import AICacheService


class RuleService:
    """
    Service layer for rule management

    Provides high-level business logic for:
    - Uploading rule files to database
    - Exporting rules from database to Excel
    - Retrieving rule file details and statistics
    """

    def __init__(self):
        """Initialize service with repository"""
        self.repository = RuleRepository()
        self.ai_cache_service = AICacheService()

    async def upload_rule_file(
        self,
        excel_content: bytes,
        metadata: RuleFileUpload
    ) -> RuleFileResponse:
        """
        Upload and parse rule file to database

        Process:
        1. Parse Excel B file using excel_parser
        2. Create rule_file record in database
        3. Batch insert all rules
        4. Return metadata response

        Args:
            excel_content: Raw Excel file bytes
            metadata: File metadata (file_name, version, etc.)

        Returns:
            RuleFileResponse: Created rule file metadata

        Raises:
            Exception: If parsing or database operations fail
        """
        print(f"[RuleService] Starting upload for file: {metadata.file_name}")

        try:
            # Step 1: Parse Excel file
            print("[RuleService] Parsing Excel file...")
            natural_language_rules, sheet_row_counts, total_raw_rows, reported_max_row = parse_rules_from_excel(excel_content)

            print(f"[RuleService] Parsed {len(natural_language_rules)} rules from {len(sheet_row_counts)} sheets")

            # Step 2: Prepare rules for batch insert FIRST (before creating file record)
            print("[RuleService] Preparing rules for batch insert...")
            rules_to_insert = []

            for rule in natural_language_rules:
                rule_record = {
                    "sheet_name": rule["display_sheet_name"],  # Required by DB schema
                    "canonical_sheet_name": rule["sheet"],
                    "display_sheet_name": rule["display_sheet_name"],
                    "row_number": rule["row"],
                    "column_letter": rule["column_letter"],
                    "field_name": rule["field"],
                    "rule_text": rule["rule_text"],
                    "condition": rule["condition"],
                    "note": rule["note"],
                    "is_active": True
                }
                rules_to_insert.append(rule_record)

            print(f"[RuleService] Prepared {len(rules_to_insert)} rules for insertion")

            # Step 3: Check for duplicate file (same name + version)
            requested_version = metadata.file_version or "1.0"
            print(f"[RuleService] Checking for existing file: {metadata.file_name} v{requested_version}")

            existing_files = await self.repository.list_rule_files(status='active', limit=100)
            duplicate_found = False
            max_version_number = 0.0

            for existing in existing_files:
                if existing['file_name'] == metadata.file_name:
                    # Parse version as float
                    try:
                        existing_version = float(existing['file_version'])
                        max_version_number = max(max_version_number, existing_version)

                        if existing['file_version'] == requested_version:
                            duplicate_found = True
                            print(f"[RuleService] Found duplicate: {existing['id']} (uploaded {existing['uploaded_at']})")
                    except ValueError:
                        pass

            # Auto-increment version if duplicate found
            final_version = requested_version
            if duplicate_found:
                new_version_number = max_version_number + 0.1
                final_version = f"{new_version_number:.1f}"
                print(f"[RuleService] Auto-incrementing version: {requested_version} → {final_version}")

            # Step 4: Create rule_file record
            file_data = {
                "file_name": metadata.file_name,
                "file_version": final_version,
                "uploaded_by": metadata.uploaded_by or "system",
                "total_rules_count": len(natural_language_rules),
                "sheet_count": len(sheet_row_counts),
                "notes": metadata.notes,
                "status": "active"
            }

            print("[RuleService] Creating rule_file record...")
            file_id = await self.repository.create_rule_file(file_data)
            print(f"[RuleService] Created rule_file with ID: {file_id}")

            # Step 5: Add file_id to all rules and batch insert
            print(f"[RuleService] Adding file_id to rules and inserting...")
            for rule_record in rules_to_insert:
                rule_record["rule_file_id"] = file_id

            try:
                inserted_count = await self.repository.create_rules_batch(rules_to_insert)
                print(f"[RuleService] Successfully inserted {inserted_count} rules")

                # Verify insertion
                if inserted_count == 0:
                    raise Exception("Batch insert returned 0 rows - rules may not have been saved")

                if inserted_count != len(rules_to_insert):
                    print(f"[RuleService] WARNING: Expected {len(rules_to_insert)} rules, but inserted {inserted_count}")

            except Exception as insert_error:
                print(f"[RuleService] CRITICAL: Failed to insert rules: {str(insert_error)}")
                print(f"[RuleService] Attempting to delete orphaned file record: {file_id}")

                # Try to clean up the file record
                try:
                    await self.repository.archive_rule_file(file_id)
                    print(f"[RuleService] Archived orphaned file record")
                except Exception as cleanup_error:
                    print(f"[RuleService] Failed to clean up file record: {str(cleanup_error)}")

                raise Exception(f"Failed to insert rules to database: {str(insert_error)}")

            # Step 6: Retrieve and return file metadata
            file_record = await self.repository.get_rule_file(UUID(file_id))

            response = RuleFileResponse(
                id=file_record['id'],
                file_name=file_record['file_name'],
                file_version=file_record.get('file_version'),
                uploaded_by=file_record.get('uploaded_by'),
                uploaded_at=file_record['uploaded_at'],
                sheet_count=file_record['sheet_count'],
                total_rules_count=file_record['total_rules_count'],
                status=file_record['status']
            )

            print(f"[RuleService] Upload completed successfully")

            # Step 7: Start AI interpretation in background
            print(f"[RuleService] Starting AI interpretation...")
            try:
                # Run AI interpretation (this will take 10-20 seconds)
                ai_result = await self.ai_cache_service.interpret_and_cache_rules(file_id)
                print(f"[RuleService] AI interpretation completed: {ai_result['interpreted_rules']}/{ai_result['total_rules']} rules")
            except Exception as ai_error:
                print(f"[RuleService] AI interpretation failed (non-critical): {str(ai_error)}")
                # Don't fail the upload if AI interpretation fails

            return response

        except Exception as e:
            print(f"[RuleService] Error during upload: {str(e)}")
            raise Exception(f"Failed to upload rule file: {str(e)}")

    async def get_rule_file_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a rule file

        Args:
            file_id: UUID string of the rule file

        Returns:
            Dict with file metadata and statistics, or None if not found
        """
        print(f"[RuleService] Fetching details for file: {file_id}")

        try:
            # Get file metadata
            file_record = await self.repository.get_rule_file(UUID(file_id))

            if not file_record:
                print(f"[RuleService] File not found: {file_id}")
                return None

            # Get statistics
            stats = await self.repository.get_file_statistics(UUID(file_id))

            # Get rules grouped by sheet
            all_rules = await self.repository.get_rules_by_file(UUID(file_id), active_only=True)

            # Group rules by sheet
            from collections import defaultdict
            rules_by_sheet = defaultdict(list)
            for rule in all_rules:
                sheet_name = rule.get('display_sheet_name', 'Unknown')
                rules_by_sheet[sheet_name].append({
                    "id": str(rule.get('id')),
                    "field_name": rule.get('field_name'),
                    "rule_text": rule.get('rule_text'),
                    "has_ai_interpretation": bool(rule.get('ai_rule_id'))
                })

            # Build response
            response = {
                "id": file_record['id'],
                "file_name": file_record['file_name'],
                "file_version": file_record.get('file_version'),
                "uploaded_by": file_record.get('uploaded_by'),
                "uploaded_at": file_record['uploaded_at'],
                "updated_at": file_record.get('updated_at'),
                "sheet_count": file_record['sheet_count'],
                "total_rules_count": file_record['total_rules_count'],
                "status": file_record['status'],
                "notes": file_record.get('notes'),
                "statistics": stats,
                "sheets": [
                    {
                        "sheet_name": sheet_name,
                        "rule_count": len(rules),
                        "sample_rules": rules[:5]  # Show first 5 rules as sample
                    }
                    for sheet_name, rules in rules_by_sheet.items()
                ]
            }

            print(f"[RuleService] Retrieved details for file: {file_id}")
            return response

        except Exception as e:
            print(f"[RuleService] Error fetching file details: {str(e)}")
            raise Exception(f"Failed to get rule file details: {str(e)}")

    async def list_rule_files(
        self,
        status: str = 'active',
        limit: int = 50,
        offset: int = 0
    ) -> List[RuleFileResponse]:
        """
        List all rule files with pagination

        Args:
            status: Filter by status (default: 'active')
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of RuleFileResponse objects
        """
        print(f"[RuleService] Listing rule files (status={status}, limit={limit}, offset={offset})")

        try:
            files = await self.repository.list_rule_files(status, limit, offset)

            response_list = [
                RuleFileResponse(
                    id=file['id'],
                    file_name=file['file_name'],
                    file_version=file.get('file_version'),
                    uploaded_by=file.get('uploaded_by'),
                    uploaded_at=file['uploaded_at'],
                    sheet_count=file['sheet_count'],
                    total_rules_count=file['total_rules_count'],
                    status=file['status']
                )
                for file in files
            ]

            print(f"[RuleService] Found {len(response_list)} rule files")
            return response_list

        except Exception as e:
            print(f"[RuleService] Error listing files: {str(e)}")
            raise Exception(f"Failed to list rule files: {str(e)}")

    async def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single rule by ID

        Args:
            rule_id: UUID string of the rule

        Returns:
            Dict or None
        """
        try:
            rule = await self.repository.get_rule(UUID(rule_id))
            return rule
        except Exception as e:
            print(f"[RuleService] Error getting rule: {str(e)}")
            raise Exception(f"Failed to get rule: {str(e)}")

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a rule

        Args:
            rule_id: UUID string of the rule
            updates: Dictionary of fields to update

        Returns:
            bool: True if successful
        """
        print(f"[RuleService] Updating rule: {rule_id}")
        try:
            # Clean updates: remove None values to avoid overwriting with None
            # (Unless we specifically want to set something to None)
            clean_updates = {k: v for k, v in updates.items() if v is not None}
            
            success = await self.repository.update_rule(UUID(rule_id), clean_updates)
            return success
        except Exception as e:
            print(f"[RuleService] Error updating rule: {str(e)}")
            raise Exception(f"Failed to update rule: {str(e)}")

    async def delete_rule(self, rule_id: str, permanent: bool = False) -> bool:
        """
        Delete or deactivate a rule

        Args:
            rule_id: UUID string of the rule
            permanent: If True, delete from DB. If False, just deactivate.

        Returns:
            bool: True if successful
        """
        print(f"[RuleService] Deleting rule: {rule_id} (permanent={permanent})")
        try:
            if permanent:
                return await self.repository.delete_rule(UUID(rule_id))
            else:
                return await self.repository.deactivate_rule(UUID(rule_id))
        except Exception as e:
            print(f"[RuleService] Error deleting rule: {str(e)}")
            raise Exception(f"Failed to delete rule: {str(e)}")

    async def export_rules_to_excel(self, file_id: str) -> bytes:
        """
        Export rules from database back to Excel format

        Args:
            file_id: UUID string of the rule file

        Returns:
            bytes: Excel file content

        Raises:
            Exception: If file not found or export fails
        """
        print(f"[RuleService] Exporting rules to Excel for file: {file_id}")

        try:
            # Get file metadata
            file_record = await self.repository.get_rule_file(UUID(file_id))

            if not file_record:
                raise Exception(f"Rule file not found: {file_id}")

            # Get all rules
            all_rules = await self.repository.get_rules_by_file(UUID(file_id), active_only=True)

            if not all_rules:
                raise Exception(f"No rules found for file: {file_id}")

            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "규칙 목록"

            # Define styles
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Write headers
            headers = [
                "번호",
                "시트명",
                "행 번호",
                "컬럼",
                "필드명",
                "규칙 내용",
                "조건",
                "비고",
                "AI 해석 여부",
                "AI 규칙 ID",
                "AI 규칙 유형",
                "AI 신뢰도"
            ]

            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment

            # Write data rows
            for idx, rule in enumerate(all_rules, start=2):
                ws.cell(row=idx, column=1, value=idx - 1)
                ws.cell(row=idx, column=2, value=rule.get('display_sheet_name'))
                ws.cell(row=idx, column=3, value=rule.get('row_number'))
                ws.cell(row=idx, column=4, value=rule.get('column_letter'))
                ws.cell(row=idx, column=5, value=rule.get('field_name'))
                ws.cell(row=idx, column=6, value=rule.get('rule_text'))
                ws.cell(row=idx, column=7, value=rule.get('condition'))
                ws.cell(row=idx, column=8, value=rule.get('note'))
                ws.cell(row=idx, column=9, value="예" if rule.get('ai_rule_id') else "아니오")
                ws.cell(row=idx, column=10, value=rule.get('ai_rule_id') or "")
                ws.cell(row=idx, column=11, value=rule.get('ai_rule_type') or "")
                ws.cell(row=idx, column=12, value=rule.get('ai_confidence_score') or "")

            # Adjust column widths
            column_widths = [8, 25, 10, 10, 20, 40, 30, 30, 15, 20, 20, 12]
            for col_idx, width in enumerate(column_widths, start=1):
                ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

            # Add metadata sheet
            ws_meta = wb.create_sheet("파일 정보")
            metadata_rows = [
                ["항목", "값"],
                ["파일명", file_record['file_name']],
                ["파일 버전", file_record.get('file_version', '')],
                ["업로드일시", str(file_record['uploaded_at'])],
                ["업로드자", file_record.get('uploaded_by', '')],
                ["총 규칙 수", file_record['total_rules_count']],
                ["시트 수", file_record['sheet_count']],
                ["상태", file_record['status']],
                ["비고", file_record.get('notes', '')]
            ]

            for row_idx, row_data in enumerate(metadata_rows, start=1):
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws_meta.cell(row=row_idx, column=col_idx, value=value)
                    if row_idx == 1:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment

            ws_meta.column_dimensions['A'].width = 20
            ws_meta.column_dimensions['B'].width = 50

            # Save to bytes
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            excel_bytes = output.getvalue()
            print(f"[RuleService] Excel export completed ({len(excel_bytes)} bytes)")

            return excel_bytes

        except Exception as e:
            print(f"[RuleService] Error exporting to Excel: {str(e)}")
            raise Exception(f"Failed to export rules to Excel: {str(e)}")


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_service():
        """Test service operations"""
        print("=" * 70)
        print("RuleService Test")
        print("=" * 70)

        try:
            service = RuleService()
            print("✓ Service initialized")

            # Test list files
            print("\nListing rule files...")
            files = await service.list_rule_files(limit=5)
            print(f"Found {len(files)} rule files")

            for file in files:
                print(f"  - {file.file_name} (ID: {file.id})")

            print("\n✓ Service test completed successfully")

        except Exception as e:
            print(f"\n✗ Service test failed: {str(e)}")

        print("=" * 70)

    # Run test
    asyncio.run(test_service())
