from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import get_db
from backend.app.schemas.org_team_advisor import (
    Organization, OrganizationCreate,
    Team, TeamCreate,
    Advisor, AdvisorCreate,
    IngestionSource
)
from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService

router = APIRouter()

# --- Organizations ---
@router.get("/orgs", response_model=List[Organization])
def get_organizations(db: Session = Depends(get_db)):
    return OrgTeamAdvisorService.list_organizations(db)

@router.post("/orgs", response_model=Organization)
def create_organization(org: OrganizationCreate, db: Session = Depends(get_db)):
    db_org = OrgTeamAdvisorService.get_organization_by_name(db, org.name)
    if db_org:
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    return OrgTeamAdvisorService.create_organization(db, org)

# --- Teams ---
@router.get("/teams", response_model=List[Team])
def get_teams(org_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OrgTeamAdvisorService.list_teams(db, org_id)

@router.post("/teams", response_model=Team)
def create_team(team: TeamCreate, db: Session = Depends(get_db)):
    # Validate organization exists
    org = OrgTeamAdvisorService.get_organization(db, team.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrgTeamAdvisorService.create_team(db, team)

# --- Advisors ---
@router.get("/advisors", response_model=List[Advisor])
def get_advisors(team_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OrgTeamAdvisorService.list_advisors(db, team_id)

@router.post("/advisors", response_model=Advisor)
def create_advisor(advisor: AdvisorCreate, db: Session = Depends(get_db)):
    # Validate team exists
    team = OrgTeamAdvisorService.get_team(db, advisor.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    # Check employee code uniqueness
    existing = OrgTeamAdvisorService.get_advisor_by_code(db, advisor.employee_code)
    if existing:
        raise HTTPException(status_code=400, detail="Advisor with this employee code already exists")
    return OrgTeamAdvisorService.create_advisor(db, advisor)

# --- Ingestion Sources ---
@router.get("/sources", response_model=List[IngestionSource])
def get_ingestion_sources(db: Session = Depends(get_db)):
    return OrgTeamAdvisorService.list_ingestion_sources(db)
