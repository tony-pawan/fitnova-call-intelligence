from backend.app.database.session import SessionLocal
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor

def test_db_seeded_data() -> None:
    """
    Verifies that the database has been successfully seeded with organizations, 
    teams, and advisors, and that relationships are valid.
    """
    db = SessionLocal()
    try:
        # Check Organization
        org = db.query(Organization).filter(Organization.name == "FitNova").first()
        assert org is not None
        assert org.name == "FitNova"

        # Check Teams associated with Org
        teams = db.query(Team).filter(Team.organization_id == org.id).all()
        assert len(teams) == 2
        team_names = {team.name for team in teams}
        assert "Team Alpha" in team_names
        assert "Team Beta" in team_names

        # Check Advisors
        advisors = db.query(Advisor).all()
        assert len(advisors) == 4
        advisor_names = {adv.name for adv in advisors}
        assert {"Rahul", "Priya", "Arjun", "Sneha"}.issubset(advisor_names)
        
        # Verify relationship references
        for team in teams:
            assert len(team.advisors) == 2
            for advisor in team.advisors:
                assert advisor.team_id == team.id
                assert advisor.email is not None
    finally:
        db.close()
