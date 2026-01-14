"""
Statistics Service - 데이터 및 규칙 통계 분석
=============================================
규칙별 성능, 오류 빈도, False Positive 비율 등을 분석하여 제공
"""

from typing import List, Dict, Any
from database.supabase_client import supabase

class StatisticsService:
    """
    통계 데이터 집계 및 분석 서비스
    """
    
    def __init__(self):
        self.client = supabase

    async def get_dashboard_statistics(self) -> Dict[str, Any]:
        """
        대시보드용 전체 통계 데이터 조회
        """
        try:
            # 1. 전체 검증 세션 통계
            sessions_res = self.client.table('validation_sessions') \
                .select('total_rows, total_errors, validation_status, created_at') \
                .order('created_at', desc=True) \
                .limit(100) \
                .execute()
            
            sessions = sessions_res.data
            total_sessions = len(sessions)
            total_rows_validated = sum(s['total_rows'] or 0 for s in sessions)
            avg_error_rate = 0
            if total_rows_validated > 0:
                avg_error_rate = (sum(s['total_errors'] or 0 for s in sessions) / total_rows_validated) * 100

            # 2. 규칙별 오류 발생 순위 (Top 10)
            # Note: GroupBy is not directly supported in simple Supabase client select(), 
            # so we fetch errors (limited) and aggregate in Python for prototype.
            # For production, use RPC or specific SQL view.
            errors_res = self.client.table('validation_errors') \
                .select('rule_id, error_message') \
                .limit(1000) \
                .execute()
            
            rule_stats = {}
            for err in errors_res.data:
                rid = err['rule_id']
                if rid not in rule_stats:
                    rule_stats[rid] = {'count': 0, 'sample_msg': err['error_message']}
                rule_stats[rid]['count'] += 1
            
            top_error_rules = sorted(
                [{'rule_id': k, **v} for k, v in rule_stats.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]

            # 3. False Positive (오진) 피드백 통계
            feedback_res = self.client.table('false_positive_feedback') \
                .select('rule_id') \
                .eq('is_false_positive', True) \
                .execute()
            
            fp_counts = {}
            for fb in feedback_res.data:
                rid = fb['rule_id']
                fp_counts[rid] = fp_counts.get(rid, 0) + 1
            
            # Merge FP counts into top rules
            for rule in top_error_rules:
                rule['fp_count'] = fp_counts.get(rule['rule_id'], 0)
                rule['accuracy_score'] = self._calculate_accuracy_score(rule['count'], rule['fp_count'])

            return {
                "overview": {
                    "total_sessions": total_sessions,
                    "total_rows_validated": total_rows_validated,
                    "avg_error_rate": round(avg_error_rate, 2)
                },
                "top_error_rules": top_error_rules,
                "recent_trend": [
                    {"date": s['created_at'][:10], "errors": s['total_errors']} 
                    for s in sessions[:10]
                ][::-1] # Reverse to show chronological order
            }
            
        except Exception as e:
            print(f"[StatisticsService] Error generating stats: {str(e)}")
            return {
                "error": str(e)
            }

    def _calculate_accuracy_score(self, error_count: int, fp_count: int) -> int:
        """
        단순 정확도 점수 계산 (0-100)
        - 오진율이 높을수록 점수가 낮음
        """
        if error_count == 0:
            return 100
        
        fp_rate = fp_count / error_count
        # 오진율 0% -> 100점
        # 오진율 100% -> 0점
        score = 100 * (1 - fp_rate)
        return round(score)
