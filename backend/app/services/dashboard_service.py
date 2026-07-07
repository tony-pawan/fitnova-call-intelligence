import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.call import Call, CallStatus
from backend.app.models.advisor import Advisor
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag
from backend.app.models.appeal import Appeal, AppealStatus
from backend.app.utils.timeline import get_pipeline_timeline
from backend.app.utils.json_storage import load_json
from backend.app.core.logging import get_logger

logger = get_logger("DASHBOARD")

class DashboardService:
    """
    Service responsible for aggregating structured database queries and rich AI JSON artifacts
    to populate manager views, advisor performance trends, and call details scorecards.
    """

    @staticmethod
    def get_filter_options(db: Session) -> Dict[str, Any]:
        """
        Retrieves list of advisors and available pipeline statuses to populate UI filters.
        """
        advisors = db.query(Advisor).all()
        statuses = [s.value for s in CallStatus]
        return {
            "advisors": [{"id": a.id, "name": a.name} for a in advisors],
            "statuses": statuses
        }

    @staticmethod
    def get_manager_dashboard(db: Session, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Aggregates global call metrics, compliance averages, issue severities,
        and recent call lists. Exposes search functionality by Call ID.
        """
        logger.info("Loaded manager dashboard")
        query = db.query(Call)

        # Apply search and filters
        if filters:
            if filters.get("search_id"):
                try:
                    search_val = int(filters["search_id"])
                    query = query.filter(Call.id == search_val)
                except ValueError:
                    pass  # Non-integer search queries ignored
            else:
                if filters.get("advisor_id"):
                    query = query.filter(Call.advisor_id == filters["advisor_id"])
                if filters.get("status"):
                    query = query.filter(Call.status == filters["status"])
                if filters.get("min_score") is not None:
                    query = query.join(CallAnalysis).filter(CallAnalysis.overall_score >= filters["min_score"])

        calls = query.all()
        call_ids = [c.id for c in calls]

        # Aggregate Call statuses
        total_calls = len(calls)
        completed_calls = len([c for c in calls if c.status == CallStatus.Completed])
        queue_calls = len([c for c in calls if c.status in [CallStatus.Uploaded, CallStatus.Queued, CallStatus.Processing]])

        # Gather completed analyses
        analyses_query = db.query(CallAnalysis)
        if call_ids:
            analyses_query = analyses_query.filter(CallAnalysis.call_id.in_(call_ids))
        else:
            analyses_query = analyses_query.filter(CallAnalysis.id == -1)
            
        analyses = analyses_query.all()
        avg_score = round(sum(a.overall_score for a in analyses) / len(analyses), 1) if analyses else 0.0

        # Load compliance details from JSON scorecards
        compliance_scores = []
        for c in calls:
            if c.status == CallStatus.Completed:
                json_path = f"./storage/analysis/call_{c.id}.json"
                if os.path.exists(json_path):
                    try:
                        data = load_json(json_path)
                        if data and "overall_score" in data:
                            # Use overall score or default as compliance placeholder
                            compliance_scores.append(data.get("overall_score", 90.0))
                    except Exception:
                        pass
        avg_compliance = round(sum(compliance_scores) / len(compliance_scores), 1) if compliance_scores else 0.0

        # Create Advisor Leaderboard
        advisors = db.query(Advisor).all()
        leaderboard = []
        for adv in advisors:
            adv_calls = [c for c in calls if c.advisor_id == adv.id]
            adv_call_ids = [c.id for c in adv_calls]
            adv_completed = len([c for c in adv_calls if c.status == CallStatus.Completed])

            adv_analyses = [a for a in analyses if a.call_id in adv_call_ids]
            adv_avg = round(sum(a.overall_score for a in adv_analyses) / len(adv_analyses), 1) if adv_analyses else 0.0

            leaderboard.append({
                "advisor_id": adv.id,
                "advisor_name": adv.name,
                "calls_processed": adv_completed,
                "average_score": adv_avg
            })
        leaderboard.sort(key=lambda x: x["average_score"], reverse=True)

        # Issue tags severity mapping
        issues_query = db.query(IssueTag)
        if analyses:
            issues_query = issues_query.filter(IssueTag.analysis_id.in_([a.id for a in analyses]))
        else:
            issues_query = issues_query.filter(IssueTag.id == -1)
            
        issue_tags = issues_query.all()
        
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

        # Fetch recent call list
        recent_calls_list = []
        for c in sorted(calls, key=lambda x: x.id, reverse=True)[:10]:
            adv = next((a for a in advisors if a.id == c.advisor_id), None)
            c_analysis = next((a for a in analyses if a.call_id == c.id), None)
            recent_calls_list.append({
                "id": c.id,
                "advisor_name": adv.name if adv else "Unknown",
                "status": c.status.value,
                "overall_score": c_analysis.overall_score if c_analysis else None,
                "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else str(c.created_at),
                "duration_seconds": c.duration_seconds
            })

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "queue_calls": queue_calls,
            "average_score": avg_score,
            "compliance_score": avg_compliance,
            "pending_appeals": db.query(Appeal).filter(Appeal.status == AppealStatus.Pending).count(),
            "leaderboard": leaderboard,
            "severity_breakdown": severity_counts,
            "top_issues": top_issues[:5],
            "recent_calls": recent_calls_list
        }

    @staticmethod
    def get_advisor_dashboard(db: Session, advisor_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Aggregates metrics for a single Advisor including average performance score,
        score trends over time, and action items checklist.
        """
        logger.info(f"Loaded advisor dashboard for advisor ID {advisor_id}")
        query = db.query(Call).filter(Call.advisor_id == advisor_id)

        if filters:
            if filters.get("status"):
                query = query.filter(Call.status == filters["status"])
            if filters.get("min_score") is not None:
                query = query.join(CallAnalysis).filter(CallAnalysis.overall_score >= filters["min_score"])

        calls = query.all()
        call_ids = [c.id for c in calls]

        analyses_query = db.query(CallAnalysis)
        if call_ids:
            analyses_query = analyses_query.filter(CallAnalysis.call_id.in_(call_ids))
        else:
            analyses_query = analyses_query.filter(CallAnalysis.id == -1)
            
        analyses = analyses_query.all()
        avg_score = round(sum(a.overall_score for a in analyses) / len(analyses), 1) if analyses else 0.0

        recommendations = []
        performance_trend = []
        
        for c in sorted(calls, key=lambda x: x.id):
            c_analysis = next((a for a in analyses if a.call_id == c.id), None)
            if c_analysis:
                date_str = c.created_at.split("T")[0] if isinstance(c.created_at, str) else c.created_at.strftime("%Y-%m-%d")
                performance_trend.append({
                    "date": date_str,
                    "score": c_analysis.overall_score,
                    "call_id": c.id
                })
                if c_analysis.recommendation:
                    recommendations.extend(c_analysis.recommendation.split("\n"))

        # Deduplicate recommendations and limit output to 5
        seen_recs = set()
        unique_recs = [r for r in recommendations if not (r in seen_recs or seen_recs.add(r))][:5]

        recent_calls_list = []
        for c in sorted(calls, key=lambda x: x.id, reverse=True)[:10]:
            c_analysis = next((a for a in analyses if a.call_id == c.id), None)
            recent_calls_list.append({
                "id": c.id,
                "status": c.status.value,
                "overall_score": c_analysis.overall_score if c_analysis else None,
                "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else str(c.created_at),
                "duration_seconds": c.duration_seconds
            })

        pending_count = db.query(Appeal).filter(Appeal.advisor_id == advisor_id, Appeal.status == AppealStatus.Pending).count()
        approved_count = db.query(Appeal).filter(Appeal.advisor_id == advisor_id, Appeal.status == AppealStatus.Approved).count()
        rejected_count = db.query(Appeal).filter(Appeal.advisor_id == advisor_id, Appeal.status == AppealStatus.Rejected).count()

        return {
            "average_score": avg_score,
            "performance_trend": performance_trend,
            "recent_recommendations": unique_recs,
            "recent_calls": recent_calls_list,
            "pending_appeals": pending_count,
            "approved_appeals": approved_count,
            "rejected_appeals": rejected_count
        }

    @staticmethod
    def get_call_details(db: Session, call_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves database status and loads transcription, conversation,
        analysis, and timeline JSON artifacts for a specific Call ID.
        """
        logger.info(f"Fetched analytics for Call ID {call_id}")
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        advisor = db.query(Advisor).filter(Advisor.id == call.advisor_id).first()
        advisor_name = advisor.name if advisor else "Unknown"

        # Load filesystem JSON artifacts
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

        # Retrieve timelines logs
        timeline = get_pipeline_timeline(call_id)

        return {
            "metadata": {
                "id": call.id,
                "advisor_name": advisor_name,
                "advisor_id": call.advisor_id,
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

    @staticmethod
    def get_pending_appeals(db: Session) -> list:
        """
        Returns all submitted appeals that are currently Pending.
        """
        return db.query(Appeal).filter(Appeal.status == AppealStatus.Pending).all()

    @staticmethod
    def get_appeal_statistics(db: Session) -> dict:
        """
        Aggregates global counts for pending, approved, and rejected appeals.
        """
        pending = db.query(Appeal).filter(Appeal.status == AppealStatus.Pending).count()
        approved = db.query(Appeal).filter(Appeal.status == AppealStatus.Approved).count()
        rejected = db.query(Appeal).filter(Appeal.status == AppealStatus.Rejected).count()
        return {
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "total": pending + approved + rejected
        }

    @staticmethod
    def get_advisor_appeals(db: Session, advisor_id: int) -> list:
        """
        Compiles a list of all appeals submitted by a specific sales advisor.
        """
        appeals = db.query(Appeal).filter(Appeal.advisor_id == advisor_id).order_by(Appeal.created_at.desc()).all()
        results = []
        for app in appeals:
            tag = db.query(IssueTag).filter(IssueTag.id == app.issue_tag_id).first()
            analysis = db.query(CallAnalysis).filter(CallAnalysis.id == tag.analysis_id).first() if tag else None
            call = db.query(Call).filter(Call.id == analysis.call_id).first() if analysis else None
            results.append({
                "id": app.id,
                "call_id": call.id if call else None,
                "issue_tag_id": app.issue_tag_id,
                "tag": tag.tag if tag else "Unknown",
                "severity": tag.severity.value if tag else "Medium",
                "quote": tag.quote if tag else "",
                "reason": app.reason,
                "status": app.status.value,
                "created_at": app.created_at.isoformat() if app.created_at else ""
            })
        return results

    @staticmethod
    def get_manager_queue(db: Session) -> list:
        """
        Compiles a detailed review queue of all appeals for managers.
        """
        appeals = db.query(Appeal).order_by(
            # Sort Pending first, then newest
            Appeal.status == AppealStatus.Pending, 
            Appeal.created_at.desc()
        ).all()
        results = []
        for app in appeals:
            tag = db.query(IssueTag).filter(IssueTag.id == app.issue_tag_id).first()
            analysis = db.query(CallAnalysis).filter(CallAnalysis.id == tag.analysis_id).first() if tag else None
            call = db.query(Call).filter(Call.id == analysis.call_id).first() if analysis else None
            advisor = db.query(Advisor).filter(Advisor.id == app.advisor_id).first()
            results.append({
                "id": app.id,
                "call_id": call.id if call else None,
                "advisor_name": advisor.name if advisor else "Unknown",
                "tag": tag.tag if tag else "Unknown",
                "severity": tag.severity.value if tag else "Medium",
                "quote": tag.quote if tag else "",
                "reason": app.reason,
                "status": app.status.value,
                "created_at": app.created_at.isoformat() if app.created_at else ""
            })
        return results
