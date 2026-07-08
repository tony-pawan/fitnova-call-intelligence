import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]

from backend.app.models.call import Call
from backend.app.models.transcript import TranscriptSegment
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.models.version_models import TranscriptVersion, ConversationVersion, AnalysisVersion
from backend.app.utils.json_storage import load_json, save_json
from backend.app.ai.dto.conversation import ConversationResult, ConversationSegment
from backend.app.ai.analysis_orchestrator import AnalysisOrchestrator
from backend.app.core.logging import get_logger

logger = get_logger("FEEDBACK")

class FeedbackService:
    """
    Service handling human feedback loops, transcription/speaker corrections,
    reviews, overrides, re-analysis, and version history.
    """
    @staticmethod
    def get_version_history(db: Session, call_id: int) -> Dict[str, Any]:
        """
        Retrieves all version history iterations of transcripts, conversations, and analyses.
        """
        transcripts = db.query(TranscriptVersion).filter(TranscriptVersion.call_id == call_id).order_by(TranscriptVersion.version.asc()).all()
        conversations = db.query(ConversationVersion).filter(ConversationVersion.call_id == call_id).order_by(ConversationVersion.version.asc()).all()
        analyses = db.query(AnalysisVersion).filter(AnalysisVersion.call_id == call_id).order_by(AnalysisVersion.version.asc()).all()
        
        return {
            "transcripts": [
                {"version": t.version, "created_at": t.created_at.isoformat(), "file_path": t.file_path} for t in transcripts
            ],
            "conversations": [
                {"version": c.version, "created_at": c.created_at.isoformat(), "file_path": c.file_path} for c in conversations
            ],
            "analyses": [
                {
                    "version": a.version,
                    "created_at": a.created_at.isoformat(),
                    "overall_score": a.overall_score,
                    "human_score": a.human_score,
                    "human_reviewer": a.human_reviewer,
                    "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                    "file_path": a.file_path
                } for a in analyses
            ]
        }

    @staticmethod
    def correct_transcript(db: Session, call_id: int, corrections: List[Dict[str, Any]]) -> bool:
        """
        Corrects transcript segment texts, versions the file, and syncs the database.
        """
        logger.info(f"Applying transcript corrections to Call ID {call_id}")
        active_path = f"./storage/transcripts/call_{call_id}.json"
        
        if not os.path.exists(active_path):
            raise FileNotFoundError("Active transcript file does not exist")
            
        data = load_json(active_path)
        
        # 1. Archive version 1 if no versions exist yet
        version_count = db.query(TranscriptVersion).filter(TranscriptVersion.call_id == call_id).count()
        if version_count == 0:
            v1_path = f"./storage/transcripts/call_{call_id}_v1.json"
            shutil.copy2(active_path, v1_path)
            v1_record = TranscriptVersion(call_id=call_id, version=1, file_path=v1_path)
            db.add(v1_record)
            db.commit()
            version_count = 1
            
        # 2. Apply corrections to JSON
        corr_map = {int(c["index"]): c["text"] for c in corrections}
        for idx, seg in enumerate(data["segments"]):
            if idx in corr_map:
                seg["text"] = corr_map[idx]
                
        # 3. Save new version file
        next_ver = version_count + 1
        new_ver_path = f"./storage/transcripts/call_{call_id}_v{next_ver}.json"
        data["version"] = f"{next_ver}.0"
        data["generated_at"] = datetime.now().isoformat()
        
        save_json(new_ver_path, data)
        save_json(active_path, data)
        
        # Save version record
        v_record = TranscriptVersion(call_id=call_id, version=next_ver, file_path=new_ver_path)
        db.add(v_record)
        
        # 4. Sync transcript_segments database table
        db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).delete()
        db.flush()
        
        for idx, seg in enumerate(data["segments"]):
            db_seg = TranscriptSegment(
                call_id=call_id,
                speaker=None, # speaker is mapped in conversation step
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"]
            )
            db.add(db_seg)
            
        db.commit()
        logger.info(f"Successfully saved transcript version {next_ver} for Call ID {call_id}.")
        return True

    @staticmethod
    def correct_speakers(db: Session, call_id: int, speaker_updates: List[Dict[str, Any]]) -> bool:
        """
        Corrects speaker labels for conversation segments, versions the file, and syncs the database.
        """
        logger.info(f"Applying speaker label corrections to Call ID {call_id}")
        active_path = f"./storage/conversations/call_{call_id}.json"
        
        if not os.path.exists(active_path):
            raise FileNotFoundError("Active conversation file does not exist")
            
        data = load_json(active_path)
        
        # 1. Archive version 1 if no versions exist yet
        version_count = db.query(ConversationVersion).filter(ConversationVersion.call_id == call_id).count()
        if version_count == 0:
            v1_path = f"./storage/conversations/call_{call_id}_v1.json"
            shutil.copy2(active_path, v1_path)
            v1_record = ConversationVersion(call_id=call_id, version=1, file_path=v1_path)
            db.add(v1_record)
            db.commit()
            version_count = 1
            
        # 2. Apply speaker updates
        speaker_map = {int(u["index"]): u["speaker"] for u in speaker_updates}
        for idx, seg in enumerate(data["segments"]):
            if idx in speaker_map:
                seg["speaker"] = speaker_map[idx]
                
        # 3. Save new version file
        next_ver = version_count + 1
        new_ver_path = f"./storage/conversations/call_{call_id}_v{next_ver}.json"
        
        save_json(new_ver_path, data)
        save_json(active_path, data)
        
        # Save version record
        v_record = ConversationVersion(call_id=call_id, version=next_ver, file_path=new_ver_path)
        db.add(v_record)
        
        # 4. Sync database: update matching transcript_segments speaker columns
        # Transcript segments are ordered by start time
        db_segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).order_by(TranscriptSegment.start_time.asc()).all()
        for idx, db_seg in enumerate(db_segments):
            if idx < len(data["segments"]):
                db_seg.speaker = data["segments"][idx]["speaker"]
                
        db.commit()
        logger.info(f"Successfully saved conversation version {next_ver} for Call ID {call_id}.")
        return True

    @staticmethod
    def review_issue(db: Session, issue_id: int, review_status: str, reviewer_comments: Optional[str] = None, severity: Optional[str] = None) -> bool:
        """
        Accepts, dismisses, or marks an issue tag as false positive and updates severity.
        """
        issue = db.query(IssueTag).filter(IssueTag.id == issue_id).first()
        if not issue:
            raise ValueError(f"Issue tag with ID {issue_id} not found.")
            
        issue.review_status = review_status
        if reviewer_comments is not None:
            issue.reviewer_comments = reviewer_comments
        if severity is not None:
            issue.severity = Severity(severity)
            
        db.commit()
        logger.info(f"Updated issue tag {issue_id} status to {review_status}")
        return True

    @staticmethod
    def override_score(db: Session, call_id: int, human_score: float, reason: str, reviewer: str) -> bool:
        """
        Overrides the AI scorecard score with a human evaluator score.
        """
        logger.info(f"Applying score override for Call ID {call_id} (Human Score: {human_score})")
        analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
        if not analysis:
            raise ValueError(f"No analysis record found for Call ID {call_id}")
            
        # Write to active analysis JSON file
        active_path = f"./storage/analysis/call_{call_id}.json"
        
        if os.path.exists(active_path):
            data = load_json(active_path)
            
            # Archive previous version
            version_count = db.query(AnalysisVersion).filter(AnalysisVersion.call_id == call_id).count()
            if version_count == 0:
                v1_path = f"./storage/analysis/call_{call_id}_v1.json"
                shutil.copy2(active_path, v1_path)
                v1_record = AnalysisVersion(
                    call_id=call_id,
                    version=1,
                    overall_score=data.get("overall_score", 0.0),
                    file_path=v1_path
                )
                db.add(v1_record)
                db.commit()
                version_count = 1
                
            # Apply override
            data["overall_score"] = human_score
            data["human_override"] = {
                "human_score": human_score,
                "reason": reason,
                "reviewer": reviewer,
                "timestamp": datetime.now().isoformat()
            }
            
            next_ver = version_count + 1
            new_ver_path = f"./storage/analysis/call_{call_id}_v{next_ver}.json"
            
            save_json(new_ver_path, data)
            save_json(active_path, data)
            
            # Save version record
            v_record = AnalysisVersion(
                call_id=call_id,
                version=next_ver,
                overall_score=human_score,
                human_score=human_score,
                human_score_reason=reason,
                human_reviewer=reviewer,
                reviewed_at=datetime.now(),
                file_path=new_ver_path
            )
            db.add(v_record)
            
        # Update database overall score
        analysis.overall_score = int(round(human_score))
        db.commit()
        
        logger.info(f"Override complete for Call ID {call_id}")
        return True

    @staticmethod
    def reanalyze(db: Session, call_id: int) -> bool:
        """
        Re-runs the Gemini AI evaluation pipeline on the human-corrected transcript.
        """
        logger.info(f"Re-running analysis pipeline on Call ID {call_id}")
        
        active_conv_path = f"./storage/conversations/call_{call_id}.json"
        if not os.path.exists(active_conv_path):
            raise FileNotFoundError("Active conversation file does not exist")
            
        conv_data = load_json(active_conv_path)
        
        # Build ConversationResult DTO from the file
        segments = []
        for seg in conv_data.get("segments", []):
            segments.append(
                ConversationSegment(
                    speaker=seg["speaker"],
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"]
                )
            )
            
        conversation_dto = ConversationResult(
            language=conv_data.get("language", "hi"),
            duration=conv_data.get("duration", 0.0),
            segments=segments
        )
        
        # Archive the previous active scorecard
        active_analysis_path = f"./storage/analysis/call_{call_id}.json"
        if os.path.exists(active_analysis_path):
            data = load_json(active_analysis_path)
            version_count = db.query(AnalysisVersion).filter(AnalysisVersion.call_id == call_id).count()
            if version_count == 0:
                v1_path = f"./storage/analysis/call_{call_id}_v1.json"
                shutil.copy2(active_analysis_path, v1_path)
                v1_record = AnalysisVersion(
                    call_id=call_id,
                    version=1,
                    overall_score=data.get("overall_score", 0.0),
                    file_path=v1_path
                )
                db.add(v1_record)
                db.commit()
                version_count = 1
                
            next_ver = version_count + 1
        else:
            next_ver = 1
            
        # Execute analysis orchestrator using the corrected DTO
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.analyze(call_id, conversation_dto)
        
        # Save to active file path and write database record
        # Note: AnalysisStorageService.persist_analysis deletes previous record and commits new
        from backend.app.services.analysis_storage_service import AnalysisStorageService
        AnalysisStorageService.persist_analysis(db, call_id, result)
        
        # Fetch the newly generated active scorecard
        new_analysis_data = load_json(active_analysis_path)
        
        # Save version record
        new_ver_path = f"./storage/analysis/call_{call_id}_v{next_ver}.json"
        shutil.copy2(active_analysis_path, new_ver_path)
        
        v_record = AnalysisVersion(
            call_id=call_id,
            version=next_ver,
            overall_score=result.overall_score,
            file_path=new_ver_path
        )
        db.add(v_record)
        db.commit()
        
        logger.info(f"Re-analysis completed successfully for Call ID {call_id}. Saved scorecard version {next_ver}.")
        return True
