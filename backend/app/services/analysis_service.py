from typing import List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag
from backend.app.schemas.analysis import CallAnalysisCreate
from backend.app.schemas.issue_tag import IssueTagCreate
from backend.app.core.logging import get_logger

logger = get_logger("DATABASE")

class AnalysisService:
    @staticmethod
    def get_analysis(db: Session, analysis_id: int) -> Optional[CallAnalysis]:
        """
        Retrieves a CallAnalysis record by ID.
        """
        return db.query(CallAnalysis).filter(CallAnalysis.id == analysis_id).first()

    @staticmethod
    def get_analysis_by_call_id(db: Session, call_id: int) -> Optional[CallAnalysis]:
        """
        Retrieves the CallAnalysis record for a specific Call ID.
        """
        return db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()

    @staticmethod
    def create_analysis(db: Session, analysis: CallAnalysisCreate) -> CallAnalysis:
        """
        Creates a new CallAnalysis record.
        """
        logger.info(f"DB Operation: Creating scorecard analysis for Call ID: {analysis.call_id}")
        db_analysis = CallAnalysis(
            call_id=analysis.call_id,
            overall_score=analysis.overall_score,
            summary=analysis.summary,
            recommendation=analysis.recommendation
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        return db_analysis

    @staticmethod
    def create_issue_tag(db: Session, issue: IssueTagCreate) -> IssueTag:
        """
        Creates a new IssueTag record linked to an analysis.
        """
        logger.info(f"DB Operation: Flagging issue tag '{issue.tag}' under analysis ID: {issue.analysis_id}")
        db_issue = IssueTag(
            analysis_id=issue.analysis_id,
            tag=issue.tag,
            severity=issue.severity,
            timestamp=issue.timestamp,
            quote=issue.quote,
            reason=issue.reason
        )
        db.add(db_issue)
        db.commit()
        db.refresh(db_issue)
        return db_issue

    @staticmethod
    def get_issue_tags(db: Session, analysis_id: int) -> List[IssueTag]:
        """
        Retrieves all IssueTags for an analysis scorecard.
        """
        return db.query(IssueTag).filter(IssueTag.analysis_id == analysis_id).all()
