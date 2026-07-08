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
            
            # Map raw issue tag details to DB models
            seen_tags = set()
            import json
            for tag_detail in result.issue_tags:
                clean_t = tag_detail.tag.strip()
                norm_t = clean_t.lower()
                if norm_t in ["none", "no issues", "no violations", "none detected", "no compliance issues", "no compliance violations", "n/a", "null", ""]:
                    continue
                if norm_t in seen_tags:
                    continue
                seen_tags.add(norm_t)
                
                # Check severity mapping
                from backend.app.models.issue_tag import Severity as DBSeverity
                db_sev = DBSeverity.Medium
                try:
                    sev_str = tag_detail.severity.strip().capitalize()
                    if sev_str in ["Low", "Medium", "High", "Critical"]:
                        db_sev = DBSeverity[sev_str]
                except:
                    pass
                
                # Compute timestamp and quote from evidence segments
                first_timestamp = 0.0
                combined_quote = "Detected during conversation audit."
                
                if tag_detail.evidence_segments:
                    first_timestamp = tag_detail.evidence_segments[0].start_time
                    combined_quote = " | ".join(f"{ev.speaker}: {ev.transcript_text}" for ev in tag_detail.evidence_segments)
                
                # Serialize evidence segments
                serialized_evidence = json.dumps([ev.model_dump() for ev in tag_detail.evidence_segments])
                
                db_tag = IssueTagModel(
                    tag=clean_t,
                    severity=db_sev,
                    timestamp=first_timestamp,
                    quote=combined_quote,
                    reason=tag_detail.reason,
                    confidence=tag_detail.confidence,
                    recommendation=tag_detail.recommendation,
                    evidence_segments=serialized_evidence
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
            "issue_tags": [tag.model_dump() for tag in result.issue_tags],
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
