from typing import List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor
from backend.app.schemas.organization import OrganizationCreate
from backend.app.schemas.team import TeamCreate
from backend.app.schemas.advisor import AdvisorCreate
from backend.app.core.logging import get_logger

logger = get_logger("DATABASE")

class OrganizationService:
    @staticmethod
    def get_organization(db: Session, org_id: int) -> Optional[Organization]:
        """
        Fetches an Organization by its primary key ID.
        """
        return db.query(Organization).filter(Organization.id == org_id).first()

    @staticmethod
    def get_organization_by_name(db: Session, name: str) -> Optional[Organization]:
        """
        Fetches an Organization by its unique name (useful for seeding checks).
        """
        return db.query(Organization).filter(Organization.name == name).first()

    @staticmethod
    def create_organization(db: Session, org: OrganizationCreate) -> Organization:
        """
        Creates a new Organization record.
        """
        logger.info(f"DB Operation: Creating organization '{org.name}'")
        db_org = Organization(name=org.name)
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org

    @staticmethod
    def list_organizations(db: Session, skip: int = 0, limit: int = 100) -> List[Organization]:
        """
        Lists all Organizations.
        """
        return db.query(Organization).offset(skip).limit(limit).all()

    @staticmethod
    def get_team(db: Session, team_id: int) -> Optional[Team]:
        """
        Fetches a Team by its primary key ID.
        """
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def get_team_by_name_and_org(db: Session, name: str, org_id: int) -> Optional[Team]:
        """
        Fetches a Team by name and organization ID.
        """
        return db.query(Team).filter(Team.name == name, Team.organization_id == org_id).first()

    @staticmethod
    def create_team(db: Session, team: TeamCreate) -> Team:
        """
        Creates a new Team record.
        """
        logger.info(f"DB Operation: Creating team '{team.name}' under org ID: {team.organization_id}")
        db_team = Team(name=team.name, organization_id=team.organization_id)
        db.add(db_team)
        db.commit()
        db.refresh(db_team)
        return db_team

    @staticmethod
    def list_teams(db: Session, skip: int = 0, limit: int = 100) -> List[Team]:
        """
        Lists all Teams.
        """
        return db.query(Team).offset(skip).limit(limit).all()

    @staticmethod
    def get_advisor(db: Session, advisor_id: int) -> Optional[Advisor]:
        """
        Fetches an Advisor by primary key ID.
        """
        return db.query(Advisor).filter(Advisor.id == advisor_id).first()

    @staticmethod
    def get_advisor_by_email(db: Session, email: str) -> Optional[Advisor]:
        """
        Fetches an Advisor by unique email address.
        """
        return db.query(Advisor).filter(Advisor.email == email).first()

    @staticmethod
    def create_advisor(db: Session, advisor: AdvisorCreate) -> Advisor:
        """
        Creates a new Advisor record.
        """
        logger.info(f"DB Operation: Creating advisor '{advisor.name}' with email: {advisor.email}")
        db_advisor = Advisor(
            name=advisor.name,
            email=advisor.email,
            team_id=advisor.team_id
        )
        db.add(db_advisor)
        db.commit()
        db.refresh(db_advisor)
        return db_advisor

    @staticmethod
    def list_advisors(db: Session, skip: int = 0, limit: int = 100) -> List[Advisor]:
        """
        Lists all Advisors.
        """
        return db.query(Advisor).offset(skip).limit(limit).all()
