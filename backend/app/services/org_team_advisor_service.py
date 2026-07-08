from typing import List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor
from backend.app.models.ingestion_source import IngestionSource
from backend.app.schemas.org_team_advisor import (
    OrganizationCreate,
    TeamCreate,
    AdvisorCreate,
    IngestionSourceCreate
)

class OrgTeamAdvisorService:
    # --- Organization CRUD ---
    @staticmethod
    def get_organization(db: Session, org_id: int) -> Optional[Organization]:
        return db.query(Organization).filter(Organization.id == org_id).first()

    @staticmethod
    def get_organization_by_name(db: Session, name: str) -> Optional[Organization]:
        return db.query(Organization).filter(Organization.name == name).first()

    @staticmethod
    def create_organization(db: Session, org: OrganizationCreate) -> Organization:
        db_org = Organization(name=org.name)
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org

    @staticmethod
    def list_organizations(db: Session) -> List[Organization]:
        return db.query(Organization).all()

    # --- Team CRUD ---
    @staticmethod
    def get_team(db: Session, team_id: int) -> Optional[Team]:
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def create_team(db: Session, team: TeamCreate) -> Team:
        db_team = Team(name=team.name, organization_id=team.organization_id)
        db.add(db_team)
        db.commit()
        db.refresh(db_team)
        return db_team

    @staticmethod
    def list_teams(db: Session, org_id: Optional[int] = None) -> List[Team]:
        query = db.query(Team)
        if org_id is not None:
            query = query.filter(Team.organization_id == org_id)
        return query.all()

    # --- Advisor CRUD ---
    @staticmethod
    def get_advisor(db: Session, advisor_id: int) -> Optional[Advisor]:
        return db.query(Advisor).filter(Advisor.id == advisor_id).first()

    @staticmethod
    def get_advisor_by_code(db: Session, employee_code: str) -> Optional[Advisor]:
        return db.query(Advisor).filter(Advisor.employee_code == employee_code).first()

    @staticmethod
    def create_advisor(db: Session, advisor: AdvisorCreate) -> Advisor:
        db_advisor = Advisor(
            name=advisor.name,
            team_id=advisor.team_id,
            employee_code=advisor.employee_code,
            email=advisor.email
        )
        db.add(db_advisor)
        db.commit()
        db.refresh(db_advisor)
        return db_advisor

    @staticmethod
    def list_advisors(db: Session, team_id: Optional[int] = None) -> List[Advisor]:
        query = db.query(Advisor)
        if team_id is not None:
            query = query.filter(Advisor.team_id == team_id)
        return query.all()

    # --- IngestionSource CRUD ---
    @staticmethod
    def get_ingestion_source(db: Session, source_id: int) -> Optional[IngestionSource]:
        return db.query(IngestionSource).filter(IngestionSource.id == source_id).first()

    @staticmethod
    def get_ingestion_source_by_name(db: Session, name: str) -> Optional[IngestionSource]:
        return db.query(IngestionSource).filter(IngestionSource.name == name).first()

    @staticmethod
    def create_ingestion_source(db: Session, source: IngestionSourceCreate) -> IngestionSource:
        db_source = IngestionSource(
            name=source.name,
            type=source.type,
            configuration_json=source.configuration_json,
            enabled=source.enabled
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    @staticmethod
    def list_ingestion_sources(db: Session) -> List[IngestionSource]:
        return db.query(IngestionSource).all()

    # --- Seeder helper ---
    @classmethod
    def seed_initial_org_data(cls, db: Session) -> None:
        """
        Seeds baseline Organization, Team, Advisor and IngestionSource records if database is empty.
        """
        # 1. Ingestion Sources
        sources = [
            ("Manual Upload", "Manual"),
            ("Folder Watcher", "Directory"),
            ("CRM Export", "Integration"),
            ("Telephony API", "API"),
            ("Dialer System", "Dialer"),
            ("REST API Webhook", "Webhook")
        ]
        for name, src_type in sources:
            if not cls.get_ingestion_source_by_name(db, name):
                cls.create_ingestion_source(
                    db,
                    IngestionSourceCreate(name=name, type=src_type, enabled=True)
                )

        # 2. Org Hierarchy Seeding
        if not cls.list_organizations(db):
            # FitNova global org
            org = cls.create_organization(db, OrganizationCreate(name="FitNova Corporate"))
            
            # Sales and Renewal Teams
            team_sales = cls.create_team(db, TeamCreate(name="Sales Team A", organization_id=org.id))
            team_renewal = cls.create_team(db, TeamCreate(name="Customer Success Team", organization_id=org.id))
            
            # Advisors
            cls.create_advisor(
                db, 
                AdvisorCreate(
                    name="Arjun Mehta", 
                    team_id=team_sales.id, 
                    employee_code="FN-SALES-01", 
                    email="arjun.mehta@fitnova.com"
                )
            )
            cls.create_advisor(
                db, 
                AdvisorCreate(
                    name="Priya Sharma", 
                    team_id=team_renewal.id, 
                    employee_code="FN-RENEW-02", 
                    email="priya.sharma@fitnova.com"
                )
            )
