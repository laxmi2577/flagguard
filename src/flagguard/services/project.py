"""Project management service."""

from typing import List, Optional

from sqlalchemy.orm import Session

from flagguard.core.models.tables import Project
from flagguard.core.db import SessionLocal

class ProjectService:
    """Service for managing projects."""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        
    def create_project(self, name: str, owner_id: str, description: str = "") -> Project:
        """Create a new project."""
        project = Project(
            name=name,
            owner_id=owner_id,
            description=description
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_projects_for_user(self, owner_id: str) -> List[Project]:
        """Get all projects owned by a user."""
        return self.db.query(Project).filter(Project.owner_id == owner_id).all()
        
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self.db.query(Project).filter(Project.id == project_id).first()
