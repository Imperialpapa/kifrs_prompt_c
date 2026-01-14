"""
Feedback Service - 사용자 피드백 처리
=====================================
검증 오류에 대한 False Positive 피드백 및 사용자 수정 사항 처리
"""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from database.validation_repository import ValidationRepository
from models import FalsePositiveFeedback, UserCorrectionRequest

class FeedbackService:
    """
    사용자 피드백 및 수정을 처리하는 서비스
    
    주요 기능:
    - False Positive 피드백 저장
    - 사용자 수정 이력 기록
    - 규칙 개선 제안 생성 (추후 구현)
    """

    def __init__(self):
        self.repository = ValidationRepository()

    async def submit_false_positive_feedback(
        self,
        feedback: FalsePositiveFeedback
    ) -> Dict[str, Any]:
        """
        False Positive 피드백 저장
        """
        return await self.repository.create_false_positive_feedback(feedback)

    async def submit_user_correction(
        self,
        correction: UserCorrectionRequest
    ) -> Dict[str, Any]:
        """
        사용자 수정 사항 기록
        """
        return await self.repository.create_user_correction(correction)
