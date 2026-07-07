import os
import json
from datetime import datetime
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.core.logging import get_logger, setup_logging
from backend.app.database.database import engine
from backend.app.database.session import SessionLocal
from backend.app.database.base import Base
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.models.appeal import Appeal, AppealStatus

logger = get_logger("DATABASE")

def init_db() -> None:
    """
    Initializes database schema. Creates tables if they do not exist.
    """
    logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database schemas: {e}")
        raise

def seed_data() -> None:
    """
    Seeds database with Organization, Teams, and Advisors in an idempotent manner.
    """
    logger.info("Seeding data...")
    db = SessionLocal()
    try:
        # 1. Seed Organization
        org_name = "FitNova"
        org = db.query(Organization).filter(Organization.name == org_name).first()
        if not org:
            org = Organization(name=org_name)
            db.add(org)
            db.commit()
            db.refresh(org)
            logger.info(f"Seeded Organization: {org_name}")
        else:
            logger.info(f"Organization '{org_name}' already exists. Skipping.")

        # 2. Seed Teams
        team_names = ["Team Alpha", "Team Beta"]
        teams_map = {}
        for team_name in team_names:
            team = db.query(Team).filter(Team.name == team_name, Team.organization_id == org.id).first()
            if not team:
                team = Team(name=team_name, organization_id=org.id)
                db.add(team)
                db.commit()
                db.refresh(team)
                logger.info(f"Seeded Team: {team_name}")
            else:
                logger.info(f"Team '{team_name}' already exists. Skipping.")
            teams_map[team_name] = team

        # 3. Seed Advisors (Assign evenly: Rahul, Arjun -> Team Alpha | Priya, Sneha -> Team Beta)
        advisors_data = [
            {"name": "Rahul", "email": "rahul@fitnova.com", "team": "Team Alpha"},
            {"name": "Arjun", "email": "arjun@fitnova.com", "team": "Team Alpha"},
            {"name": "Priya", "email": "priya@fitnova.com", "team": "Team Beta"},
            {"name": "Sneha", "email": "sneha@fitnova.com", "team": "Team Beta"},
        ]
        advisors_map = {}
        for adv in advisors_data:
            advisor = db.query(Advisor).filter(Advisor.email == adv["email"]).first()
            target_team = teams_map[adv["team"]]
            if not advisor:
                advisor = Advisor(
                    name=adv["name"],
                    email=adv["email"],
                    team_id=target_team.id
                )
                db.add(advisor)
                db.commit()
                db.refresh(advisor)
                logger.info(f"Seeded Advisor: {adv['name']} ({adv['email']}) into {adv['team']}")
            else:
                if advisor.team_id != target_team.id:
                    advisor.team_id = target_team.id
                    db.commit()
                    logger.info(f"Updated Advisor {adv['name']}'s team assignment to {adv['team']}")
                else:
                    logger.info(f"Advisor '{adv['name']}' ({adv['email']}) already seeded. Skipping.")
            advisors_map[adv["name"]] = advisor

        # 4. Seed Demo Calls, Analyses, Issue Tags, and Appeals
        seed_demo_calls(db, advisors_map)

        logger.info("Seed complete.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def seed_demo_calls(db: Session, advisors_map: dict) -> None:
    """
    Idempotently seeds calls and writes mock JSON files to support dashboard analytics out-of-the-box.
    """
    logger.info("Checking for demo call seeds...")
    
    # Ensure storage folders exist
    os.makedirs("./storage/transcripts", exist_ok=True)
    os.makedirs("./storage/conversations", exist_ok=True)
    os.makedirs("./storage/analysis", exist_ok=True)
    os.makedirs("./storage/processed", exist_ok=True)
    os.makedirs("./storage/audio", exist_ok=True)

    demo_calls = [
        {
            "filename": "demo_call_1.wav",
            "advisor": "Rahul",
            "score": 84,
            "duration": 180.0,
            "summary": "Rahul needs discovery was great but compliance skipped disclosures.",
            "recs": "Re-read the compliance script carefully.\nValidate user identity early.",
            "tags": [
                {
                    "tag": "Disclosure Failure",
                    "severity": Severity.High,
                    "quote": "So let's jump straight to pricing details.",
                    "reason": "Advisor failed to state the privacy terms disclosure."
                }
            ],
            "appeal": {
                "reason": "I did read standard disclosures at the start.",
                "status": AppealStatus.Pending
            }
        },
        {
            "filename": "demo_call_2.wav",
            "advisor": "Priya",
            "score": 95,
            "duration": 240.0,
            "summary": "Excellent call flow. All compliance statements read perfectly.",
            "recs": "Continue maintaining high script compliance standards.",
            "tags": [],
            "appeal": None
        },
        {
            "filename": "demo_call_3.wav",
            "advisor": "Sneha",
            "score": 78,
            "duration": 150.0,
            "summary": "Objection handling on budget constraints was slightly weak.",
            "recs": "Pace calls slower when client mentions price concerns.\nIncorporate budget qualification.",
            "tags": [
                {
                    "tag": "Missing Budget Discovery",
                    "severity": Severity.Medium,
                    "quote": "Okay, let's sign up for the premium plan.",
                    "reason": "Skipped asking user for their budget boundaries."
                }
            ],
            "appeal": {
                "reason": "The customer refused to disclose their budget.",
                "status": AppealStatus.Approved
            }
        }
    ]

    for seed in demo_calls:
        existing_call = db.query(Call).filter(Call.original_filename == seed["filename"]).first()
        if not existing_call:
            adv = advisors_map[seed["advisor"]]
            
            # Create Call
            call = Call(
                advisor_id=adv.id,
                original_filename=seed["filename"],
                stored_filename=seed["filename"],
                audio_path=f"./storage/audio/{seed['filename']}",
                mime_type="audio/wav",
                file_size_bytes=1000,
                duration_seconds=seed["duration"],
                status=CallStatus.Completed,
                language="en"
            )
            db.add(call)
            db.commit()
            db.refresh(call)
            
            # Create Analysis
            analysis = CallAnalysis(
                call_id=call.id,
                overall_score=seed["score"],
                summary=seed["summary"],
                recommendation=seed["recs"]
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            
            # Create Issue Tags & Appeals
            for t_data in seed["tags"]:
                tag = IssueTag(
                    analysis_id=analysis.id,
                    tag=t_data["tag"],
                    severity=t_data["severity"],
                    timestamp=10.0,
                    quote=t_data["quote"],
                    reason=t_data["reason"]
                )
                db.add(tag)
                db.commit()
                db.refresh(tag)
                
                if seed["appeal"]:
                    app = Appeal(
                        issue_tag_id=tag.id,
                        advisor_id=adv.id,
                        reason=seed["appeal"]["reason"],
                        status=seed["appeal"]["status"]
                    )
                    db.add(app)
                    db.commit()

            # Write Mock JSON Files
            write_mock_json_artifacts(call.id, seed, adv.name)
            logger.info(f"Seeded Demo Call: {seed['filename']} (ID: {call.id})")
        else:
            logger.info(f"Demo Call '{seed['filename']}' already seeded. Skipping.")

def write_mock_json_artifacts(call_id: int, seed: dict, advisor_name: str) -> None:
    """
    Writes helper JSON files to disk to mock Whispering, Diarization, Analysis, and timeline state logs.
    """
    # 1. Timeline
    timeline = [
        {"event": "Queued", "timestamp": datetime.now().isoformat()},
        {"event": "Processing Started", "timestamp": datetime.now().isoformat()},
        {"event": "Transcription Started", "timestamp": datetime.now().isoformat()},
        {"event": "Language Detected", "timestamp": datetime.now().isoformat()},
        {"event": "Transcript Generated", "timestamp": datetime.now().isoformat()},
        {"event": "Transcript Stored", "timestamp": datetime.now().isoformat()},
        {"event": "Speaker Diarization Started", "timestamp": datetime.now().isoformat()},
        {"event": "Conversation Reconstructed", "timestamp": datetime.now().isoformat()},
        {"event": "Conversation Stored", "timestamp": datetime.now().isoformat()},
        {"event": "AI Analysis Started", "timestamp": datetime.now().isoformat()},
        {"event": "Analysis Stored", "timestamp": datetime.now().isoformat()},
        {"event": "Completed", "timestamp": datetime.now().isoformat()}
    ]
    with open(f"./storage/processed/call_{call_id}_timeline.json", "w") as f:
        json.dump(timeline, f, indent=2)

    # 2. Transcript
    transcript = {
        "model": "Whisper-base",
        "duration": seed["duration"],
        "segments": [
            {"start": 0.0, "end": 4.0, "text": f"Hello, thank you for calling FitNova. This is {advisor_name}."},
            {"start": 4.0, "end": 8.0, "text": "Hi, I am calling to inquire about fitness plans."}
        ]
    }
    with open(f"./storage/transcripts/call_{call_id}.json", "w") as f:
        json.dump(transcript, f, indent=2)

    # 3. Conversation
    conversation = {
        "model": "Pyannote-3.1",
        "segments": [
            {"speaker": "Advisor", "start": 0.0, "end": 4.0, "text": f"Hello, thank you for calling FitNova. This is {advisor_name}."},
            {"speaker": "Customer", "start": 4.0, "end": 8.0, "text": "Hi, I am calling to inquire about fitness plans."}
        ]
    }
    with open(f"./storage/conversations/call_{call_id}.json", "w") as f:
        json.dump(conversation, f, indent=2)

    # 4. Analysis
    analysis = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-1.5-flash",
        "overall_score": seed["score"],
        "summary": seed["summary"],
        "strengths": ["Professional opening tone", "Active listening style"],
        "weaknesses": [t["tag"] for t in seed["tags"]] if seed["tags"] else [],
        "recommendations": seed["recs"].split("\n"),
        "issue_tags": [t["tag"] for t in seed["tags"]] if seed["tags"] else [],
        "analysis_metadata": {
            "model": "gemini-1.5-flash",
            "processing_time": 0.45,
            "analysis_timestamp": datetime.now().isoformat(),
            "completed_analyzers": ["discovery", "compliance", "sales_quality"],
            "failed_analyzers": []
        }
    }
    with open(f"./storage/analysis/call_{call_id}.json", "w") as f:
        json.dump(analysis, f, indent=2)

def main() -> None:
    setup_logging("INFO")
    init_db()
    seed_data()

if __name__ == "__main__":
    main()
