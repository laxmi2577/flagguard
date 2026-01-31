"""Unit tests for analysis module."""

import pytest

from flagguard.core.models import FlagDefinition, FlagType, ConflictSeverity
from flagguard.analysis.z3_wrapper import FlagSATSolver
from flagguard.analysis.conflict_detector import ConflictDetector


class TestFlagSATSolver:
    """Tests for Z3 SAT solver wrapper."""
    
    @pytest.fixture
    def solver(self) -> FlagSATSolver:
        """Create a fresh solver instance."""
        return FlagSATSolver()
    
    def test_create_variable(self, solver: FlagSATSolver) -> None:
        """Test creating boolean variables."""
        if not solver.is_available:
            pytest.skip("Z3 not available")
        
        var = solver.get_or_create_var("test_flag")
        assert var is not None
        assert "test_flag" in solver.variables
    
    def test_requires_constraint(self, solver: FlagSATSolver) -> None:
        """Test requires constraint makes dependent state impossible."""
        if not solver.is_available:
            pytest.skip("Z3 not available")
        
        solver.add_requires("child", "parent")
        
        # child=True, parent=False should be impossible
        assert not solver.check_state_possible({"child": True, "parent": False})
        
        # child=True, parent=True should be possible
        assert solver.check_state_possible({"child": True, "parent": True})
    
    def test_conflicts_constraint(self, solver: FlagSATSolver) -> None:
        """Test mutual exclusion constraint."""
        if not solver.is_available:
            pytest.skip("Z3 not available")
        
        solver.add_conflicts("flag_a", "flag_b")
        
        # Both True should be impossible
        assert not solver.check_state_possible({"flag_a": True, "flag_b": True})
        
        # One True, one False should be possible
        assert solver.check_state_possible({"flag_a": True, "flag_b": False})
    
    def test_always_off_constraint(self, solver: FlagSATSolver) -> None:
        """Test always-off constraint."""
        if not solver.is_available:
            pytest.skip("Z3 not available")
        
        solver.add_always_off("disabled_flag")
        
        # disabled_flag=True should be impossible
        assert not solver.check_state_possible({"disabled_flag": True})
        
        # disabled_flag=False should be possible
        assert solver.check_state_possible({"disabled_flag": False})
    
    def test_get_impossible_states(self, solver: FlagSATSolver) -> None:
        """Test finding impossible states."""
        if not solver.is_available:
            pytest.skip("Z3 not available")
        
        solver.add_requires("child", "parent")
        solver.add_always_off("parent")
        
        impossible = solver.get_impossible_states(["child", "parent"])
        
        # Should find that child=True, parent=False is impossible
        assert len(impossible) > 0


class TestConflictDetector:
    """Tests for conflict detector."""
    
    @pytest.fixture
    def detector(self) -> ConflictDetector:
        """Create detector with solver."""
        solver = FlagSATSolver()
        return ConflictDetector(solver)
    
    def test_load_flags(
        self,
        detector: ConflictDetector,
        sample_flags: list[FlagDefinition],
    ) -> None:
        """Test loading flag definitions."""
        detector.load_flags(sample_flags)
        
        # Verify flags are registered
        assert len(detector.solver.variables) == 3
    
    def test_detect_dependency_conflict(self, detector: ConflictDetector) -> None:
        """Test detecting dependency conflicts."""
        if not detector.solver.is_available:
            pytest.skip("Z3 not available")
        
        flags = [
            FlagDefinition(
                name="parent",
                flag_type=FlagType.BOOLEAN,
                enabled=False,  # Parent is disabled
            ),
            FlagDefinition(
                name="child",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                dependencies=["parent"],  # Child requires parent
            ),
        ]
        
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        # Should detect that child cannot be enabled when parent is off
        assert len(conflicts) > 0
    
    def test_no_conflicts_when_healthy(self, detector: ConflictDetector) -> None:
        """Test no conflicts for healthy configuration."""
        if not detector.solver.is_available:
            pytest.skip("Z3 not available")
        
        flags = [
            FlagDefinition(
                name="flag_a",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
            ),
            FlagDefinition(
                name="flag_b",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
            ),
        ]
        
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        assert len(conflicts) == 0
    
    def test_check_specific_state(self, detector: ConflictDetector) -> None:
        """Test checking a specific state."""
        if not detector.solver.is_available:
            pytest.skip("Z3 not available")
        
        flags = [
            FlagDefinition(
                name="parent",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
            ),
            FlagDefinition(
                name="child",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                dependencies=["parent"],
            ),
        ]
        
        detector.load_flags(flags)
        
        # Valid state
        conflict = detector.check_state({"child": True, "parent": True})
        assert conflict is None
        
        # Invalid state
        conflict = detector.check_state({"child": True, "parent": False})
        assert conflict is not None
