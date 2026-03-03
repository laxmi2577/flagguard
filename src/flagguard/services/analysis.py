"""Analysis execution service."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from flagguard.core.db import SessionLocal
from flagguard.core.models import ConflictType
from flagguard.core.models.tables import Scan, ScanResult
from flagguard.parsers import parse_config
from flagguard.analysis import FlagSATSolver, ConflictDetector

class AnalysisService:
    """Service for executing flag analysis."""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        
    def run_scan(
        self,
        project_id: str,
        config_file_path: str,
        result_summary_only: bool = False
    ) -> Scan:
        """Run a full analysis scan."""
        # 1. Create Pending Scan
        scan_id = uuid4().hex
        scan = Scan(
            id=scan_id,
            project_id=project_id,
            triggered_by="manual",  # simplified for phase 1
            status="running",
            created_at=datetime.utcnow()
        )
        self.db.add(scan)
        self.db.commit()
        
        try:
            # 2. Parse Flags
            flags = parse_config(config_file_path)
            
            # 3. Detect Conflicts
            solver = FlagSATSolver()
            detector = ConflictDetector(solver)
            detector.load_flags(flags)
            conflicts = detector.detect_all_conflicts()
            
            # 4. Process Results
            mutual_exclusions = [c for c in conflicts if c.conflict_type == ConflictType.MUTUAL_EXCLUSION]
            dependency_violations = [c for c in conflicts if c.conflict_type == ConflictType.DEPENDENCY_VIOLATION]
            
            # Calculate health
            total_issues = len(conflicts)
            flag_count = len(flags)
            health_score = int(max(0, 1 - (total_issues / flag_count if flag_count else 0)) * 100)
            
            summary = {
                "flag_count": flag_count,
                "conflict_count": len(mutual_exclusions),
                "dependency_count": len(dependency_violations),
                "total_issues": total_issues,
                "health_score": health_score
            }
            
            # 5. Save Results
            # Store full JSON report
            # Convert objects to dicts for JSON storage
            conflicts_json = [c.to_dict() for c in conflicts]
            flags_json = [f.name for f in flags] # Minimal info for now
            
            full_report = {
                "summary": summary,
                "conflicts": conflicts_json,
                "flags": flags_json
            }
            
            scan_result = ScanResult(
                scan_id=scan_id,
                raw_json=full_report
            )
            self.db.add(scan_result)
            
            # Update Scan Status
            scan.status = "completed"
            scan.result_summary = summary
            self.db.commit()
            
            return scan
            
        except Exception as e:
            scan.status = "failed"
            scan.result_summary = {"error": str(e)}
            self.db.commit()
            raise e
