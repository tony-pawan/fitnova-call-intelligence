from datetime import datetime
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.analysis import CallAnalysis as CallAnalysisModel
from backend.app.models.issue_tag import IssueTag as IssueTagModel, Severity
from backend.app.ai.dto.analysis import AnalysisResult
from backend.app.utils.json_storage import save_json
from backend.app.core.logging import get_logger

logger = get_logger("ANALYSIS")

class AnalysisStorageService:
    @staticmethod
    def persist_analysis(db: Session, call_id: int, result: AnalysisResult) -> bool:
        """
        Stores consolidated call analysis details in PostgreSQL (call_analyses and issue_tags tables)
        and writes the versioned JSON scorecard artifact to storage/analysis/call_<call_id>.json.
        """
        logger.info(f"Persisting analysis details for Call ID {call_id}")

        # 1. Store in PostgreSQL database (Idempotent cleanup first)
        try:
            # Delete any existing analysis for this call to prevent unique constraint conflicts
            db.query(CallAnalysisModel).filter(CallAnalysisModel.call_id == call_id).delete()
            db.flush()

            # Join recommendations array into a unified text block
            recs_text = "\n".join(result.recommendations) if result.recommendations else "No recommendations generated."

            db_analysis = CallAnalysisModel(
                call_id=call_id,
                overall_score=int(round(result.overall_score)),  # Cast float score to DB Integer type safely
                summary=result.summary,
                recommendation=recs_text
            )
            
            # Map raw issue tag strings to DB model constraints using default severity/reasons
            for tag_str in result.issue_tags:
                db_tag = IssueTagModel(
                    tag=tag_str,
                    severity=Severity.Medium,
                    timestamp=0.0,
                    quote="Detected during conversation audit.",
                    reason="Flagged by AI analysis agent."
                )
                db_analysis.issue_tags.append(db_tag)

            db.add(db_analysis)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist Call Analysis in PostgreSQL database for Call ID {call_id}: {e}")
            raise

        # 2. Persist versioned JSON scorecard artifact using json_storage utility
        json_data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "model": result.analysis_metadata.model,
            "overall_score": result.overall_score,
            "summary": result.summary,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "recommendations": result.recommendations,
            "issue_tags": result.issue_tags,
            "analysis_metadata": {
                "model": result.analysis_metadata.model,
                "processing_time": result.analysis_metadata.processing_time,
                "analysis_timestamp": result.analysis_metadata.analysis_timestamp,
                "completed_analyzers": result.analysis_metadata.completed_analyzers,
                "failed_analyzers": result.analysis_metadata.failed_analyzers
            }
        }

        file_path = f"./storage/analysis/call_{call_id}.json"
        saved = save_json(file_path, json_data)
        if saved:
            logger.info("Analysis stored successfully")
        else:
            logger.error(f"Failed to save JSON analysis scorecard for Call ID {call_id}")
            raise RuntimeError("Filesystem save failure")

        return saved
