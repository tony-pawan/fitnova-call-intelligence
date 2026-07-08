import os
import pytest  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker  # pyrefly: ignore [missing-import]
from backend.app.database.database import engine
from backend.app.database.init_db import init_db
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor
from backend.app.models.ingestion_source import IngestionSource
from backend.app.models.call import Call, CallStatus
from backend.app.schemas.org_team_advisor import OrganizationCreate, TeamCreate, AdvisorCreate
from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService
from backend.app.services.dashboard_service import DashboardService
from backend.app.utils.storage import StorageManager, LocalStorageProvider

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db():
    init_db()
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_organization_crud(db):
    """Verifies creation and listing of Org, Team, and Advisor entities."""
    import uuid
    uid = str(uuid.uuid4())[:8]
    org_name = f"Test Group Corp {uid}"
    team_name = f"Enterprise Sales Team {uid}"
    employee_code = f"SC-{uid}"
    advisor_name = f"Sara Croft {uid}"

    # Test Org
    org_in = OrganizationCreate(name=org_name)
    org = OrgTeamAdvisorService.create_organization(db, org_in)
    assert org.id is not None
    assert org.name == org_name

    # Test Team
    team_in = TeamCreate(name=team_name, organization_id=org.id)
    team = OrgTeamAdvisorService.create_team(db, team_in)
    assert team.id is not None
    assert team.organization_id == org.id

    # Test Advisor
    adv_in = AdvisorCreate(name=advisor_name, employee_code=employee_code, team_id=team.id)
    adv = OrgTeamAdvisorService.create_advisor(db, adv_in)
    assert adv.id is not None
    assert adv.team_id == team.id
    assert adv.employee_code == employee_code

    # Test list queries
    orgs = OrgTeamAdvisorService.list_organizations(db)
    assert len(orgs) >= 1
    assert any(o.name == org_name for o in orgs)

    teams = OrgTeamAdvisorService.list_teams(db, org_id=org.id)
    assert len(teams) == 1
    assert teams[0].name == team_name

    advisors = OrgTeamAdvisorService.list_advisors(db, team_id=team.id)
    assert len(advisors) == 1
    assert advisors[0].name == advisor_name

def test_storage_provider_abstraction(tmp_path):
    """Verifies that the LocalStorageProvider saves and reads files accurately."""
    provider = LocalStorageProvider()
    test_file_path = str(tmp_path / "test_recording.wav")
    content = b"RIFFmockaudiowavebytes"
    
    # Save file
    provider.save(content, test_file_path)
    assert os.path.exists(test_file_path)
    
    # Read file
    read_bytes = provider.load(test_file_path)
    assert read_bytes == content
    
    # Delete file
    provider.delete(test_file_path)
    assert not os.path.exists(test_file_path)

def test_dashboard_filters(db):
    """Verifies that queries in DashboardService successfully apply hierarchy and source filters."""
    import uuid
    uid = str(uuid.uuid4())[:8]
    org_name = f"Filter Org {uid}"
    team_name = f"Filter Team {uid}"
    employee_code = f"FSC-{uid}"
    advisor_name = f"Filter Advisor {uid}"

    # Create test call records
    org_in = OrganizationCreate(name=org_name)
    org = OrgTeamAdvisorService.create_organization(db, org_in)
    
    team_in = TeamCreate(name=team_name, organization_id=org.id)
    team = OrgTeamAdvisorService.create_team(db, team_in)
        
    adv_in = AdvisorCreate(name=advisor_name, employee_code=employee_code, team_id=team.id)
    advisor = OrgTeamAdvisorService.create_advisor(db, adv_in)
        
    source = db.query(IngestionSource).first()

    # Add mock calls with FK links
    call1 = Call(
        original_filename=f"filter_call_{uid}.mp3",
        stored_filename=f"call_{uid}.mp3",
        audio_path="mock/path",
        mime_type="audio/mp3",
        file_size_bytes=100,
        duration_seconds=50.0,
        status=CallStatus.Completed,
        source="Upload",
        vendor="Direct",
        organization_id=org.id,
        team_id=team.id,
        advisor_id=advisor.id,
        source_id=source.id if source else None
    )
    db.add(call1)
    db.commit()

    # Query metrics with filters
    metrics = DashboardService.get_dashboard_metrics(
        db, 
        org_id=org.id, 
        team_id=team.id, 
        advisor_id=advisor.id, 
        source_id=source.id if source else None
    )
    assert metrics["total_calls"] >= 1

    # Cleanup mock calls
    db.delete(call1)
    db.commit()
