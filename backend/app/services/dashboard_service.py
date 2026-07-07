import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag
from backend.app.utils.timeline import get_pipeline_timeline
from backend.app.utils.json_storage import load_json
from backend.app.core.logging import get_logger

logger = get_logger("ANALYTICS")

class DashboardService:
    """
    Service responsible for aggregating structured database queries and rich AI JSON artifacts
    to populate dashboard analytics and call history details.
    """

    @staticmethod
    def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
        """
        Retrieves top-level metrics for processed calls.
        """
        total_calls = db.query(Call).count()
        completed_calls = db.query(Call).filter(Call.status == CallStatus.Completed).count()
        
        analyses = db.query(CallAnalysis).all()
        avg_score = round(sum(a.overall_score for a in analyses) / len(analyses), 1) if analyses else 0.0

        calls = db.query(Call).all()
        avg_duration = round(sum(c.duration_seconds for c in calls) / len(calls), 1) if calls else 0.0

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "average_score": avg_score,
            "average_duration": avg_duration
        }

    @staticmethod
    def get_score_trends(db: Session) -> List[Dict[str, Any]]:
        """
        Retrieves timeline score trends for successfully processed call recordings.
        """
        results = db.query(Call, CallAnalysis).join(CallAnalysis).order_by(Call.created_at.asc()).all()
        trends = []
        for call, analysis in results:
            date_str = call.created_at.strftime("%Y-%m-%d") if isinstance(call.created_at, datetime) else str(call.created_at)
            trends.append({
                "date": date_str,
                "score": analysis.overall_score,
                "filename": call.original_filename
            })
        return trends

    @staticmethod
    def get_issue_distribution(db: Session) -> Dict[str, Any]:
        """
        Returns count breakdown of compliance issues and severity distributions.
        """
        issue_tags = db.query(IssueTag).all()
        
        issue_counts = {}
        severity_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        
        for tag in issue_tags:
            issue_counts[tag.tag] = issue_counts.get(tag.tag, 0) + 1
            sev_str = tag.severity.value if hasattr(tag.severity, "value") else str(tag.severity)
            if sev_str in severity_counts:
                severity_counts[sev_str] += 1
            else:
                severity_counts[sev_str] = 1

        top_issues = [{"tag": k, "count": v} for k, v in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)]
        
        return {
            "top_issues": top_issues[:10],
            "severity_breakdown": severity_counts
        }

    @staticmethod
    def get_processing_statistics(db: Session) -> Dict[str, int]:
        """
        Gathers count stats for background task executions by status.
        """
        stats = {}
        for s in CallStatus:
            count = db.query(Call).filter(Call.status == s).count()
            stats[s.value] = count
        return stats

    @staticmethod
    def get_history(db: Session) -> List[Dict[str, Any]]:
        """
        Lists all call records with details for overview tables.
        """
        calls = db.query(Call).order_by(Call.created_at.desc()).all()
        history = []
        for c in calls:
            c_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == c.id).first()
            history.append({
                "id": c.id,
                "filename": c.original_filename,
                "upload_time": c.created_at.isoformat() if isinstance(c.created_at, datetime) else str(c.created_at),
                "duration": c.duration_seconds,
                "status": c.status.value,
                "score": c_analysis.overall_score if c_analysis else None
            })
        return history

    @staticmethod
    def get_call_details(db: Session, call_id: int) -> Optional[Dict[str, Any]]:
        """
        Loads local filesystem JSON archives and timeline traces for a single Call.
        """
        logger.info(f"Loading scorecard details for call {call_id}")
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        # Load filesystem JSON logs
        transcript_json_path = f"./storage/transcripts/call_{call_id}.json"
        raw_transcript = None
        if os.path.exists(transcript_json_path):
            raw_transcript = load_json(transcript_json_path)

        conversation_json_path = f"./storage/conversations/call_{call_id}.json"
        conversation = None
        if os.path.exists(conversation_json_path):
            conversation = load_json(conversation_json_path)

        analysis_json_path = f"./storage/analysis/call_{call_id}.json"
        analysis = None
        if os.path.exists(analysis_json_path):
            analysis = load_json(analysis_json_path)

        timeline = get_pipeline_timeline(call_id)

        return {
            "metadata": {
                "id": call.id,
                "original_filename": call.original_filename,
                "stored_filename": call.stored_filename,
                "mime_type": call.mime_type,
                "file_size_bytes": call.file_size_bytes,
                "duration_seconds": call.duration_seconds,
                "status": call.status.value,
                "language": call.language,
                "created_at": call.created_at.isoformat() if isinstance(call.created_at, datetime) else str(call.created_at)
            },
            "transcript": raw_transcript,
            "conversation": conversation,
            "analysis": analysis,
            "timeline": timeline
        }

