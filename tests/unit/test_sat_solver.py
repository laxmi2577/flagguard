"""Unit tests for SAT solver and conflict detection."""

import pytest

# Check if Z3 is available
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


@pytest.mark.skipif(not Z3_AVAILABLE, reason="Z3 not installed")
class TestFlagSATSolver:
    """Tests for the Z3 wrapper."""
    
    def test_solver_initialization(self) -> None:
        """Test solver initializes correctly."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        assert solver.is_available is True
    
    def test_create_variable(self) -> None:
        """Test creating boolean variables."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        var = solver.get_or_create_var("test_flag")
        
        assert var is not None
        assert "test_flag" in solver.variables
    
    def test_requires_constraint(self) -> None:
        """Test dependency constraint encoding."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.add_requires("feature_a", "feature_b")
        
        # A=True, B=True should be possible
        assert solver.check_state_possible({"feature_a": True, "feature_b": True})
        
        # A=True, B=False should be impossible
        assert not solver.check_state_possible({"feature_a": True, "feature_b": False})
        
        # A=False, B=anything should be possible
        assert solver.check_state_possible({"feature_a": False, "feature_b": False})
    
    def test_conflicts_constraint(self) -> None:
        """Test mutual exclusion constraint."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.add_conflicts("premium", "free_tier")
        
        # Both True should be impossible
        assert not solver.check_state_possible({"premium": True, "free_tier": True})
        
        # One True, one False should be possible
        assert solver.check_state_possible({"premium": True, "free_tier": False})
        assert solver.check_state_possible({"premium": False, "free_tier": True})
        
        # Both False should be possible
        assert solver.check_state_possible({"premium": False, "free_tier": False})
    
    def test_always_on_constraint(self) -> None:
        """Test always-on constraint."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.add_always_on("required_flag")
        
        # True should be possible
        assert solver.check_state_possible({"required_flag": True})
        
        # False should be impossible
        assert not solver.check_state_possible({"required_flag": False})
    
    def test_always_off_constraint(self) -> None:
        """Test always-off constraint."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.add_always_off("disabled_flag")
        
        # False should be possible
        assert solver.check_state_possible({"disabled_flag": False})
        
        # True should be impossible
        assert not solver.check_state_possible({"disabled_flag": True})
    
    def test_get_impossible_states(self) -> None:
        """Test finding impossible states."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.add_conflicts("a", "b")
        
        impossible = solver.get_impossible_states(["a", "b"])
        
        # Should find one impossible state: both True
        assert len(impossible) == 1
        assert impossible[0] == {"a": True, "b": True}
    
    def test_reset(self) -> None:
        """Test solver reset."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        
        solver = FlagSATSolver()
        solver.get_or_create_var("test")
        solver.add_always_on("test")
        
        assert len(solver.variables) == 1
        
        solver.reset()
        
        assert len(solver.variables) == 0


@pytest.mark.skipif(not Z3_AVAILABLE, reason="Z3 not installed")
class TestConflictDetector:
    """Tests for conflict detection."""
    
    def test_no_conflicts_without_constraints(self) -> None:
        """Empty solver should find no conflicts."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        
        solver = FlagSATSolver()
        solver.get_or_create_var("flag_a")
        solver.get_or_create_var("flag_b")
        
        detector = ConflictDetector(solver)
        conflicts = detector.detect_all_conflicts()
        
        assert len(conflicts) == 0
    
    def test_detects_mutual_exclusion(self) -> None:
        """Should detect when two flags can't both be true."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        
        solver = FlagSATSolver()
        solver.add_conflicts("premium", "free_tier")
        
        detector = ConflictDetector(solver)
        conflicts = detector.detect_all_conflicts()
        
        # Should find: premium=True AND free_tier=True is impossible
        assert any(
            c.conflicting_values == {"premium": True, "free_tier": True}
            for c in conflicts
        )
    
    def test_detects_dependency_conflict(self) -> None:
        """Should detect when a dependency can't be satisfied."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        
        solver = FlagSATSolver()
        # A requires B, but B is always off
        solver.add_requires("feature_a", "feature_b")
        solver.add_always_off("feature_b")
        
        detector = ConflictDetector(solver)
        
        # A=True should be impossible
        conflict = detector.check_state({"feature_a": True})
        assert conflict is not None
    
    def test_load_flags(self) -> None:
        """Test loading flag definitions."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        from flagguard.core.models import FlagDefinition, FlagType
        
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        
        flags = [
            FlagDefinition(
                name="parent",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
            ),
            FlagDefinition(
                name="child",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
                dependencies=["parent"],
            ),
        ]
        
        detector.load_flags(flags)
        
        # Child requires parent, so child=True, parent=False is impossible
        conflict = detector.check_state({"child": True, "parent": False})
        assert conflict is not None


@pytest.mark.skipif(not Z3_AVAILABLE, reason="Z3 not installed")
class TestConstraintEncoder:
    """Tests for constraint encoding."""
    
    def test_encode_flags(self) -> None:
        """Test encoding flag definitions."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        from flagguard.core.models import FlagDefinition, FlagType
        
        encoder = ConstraintEncoder()
        
        flags = [
            FlagDefinition(
                name="feature_a",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
            ),
            FlagDefinition(
                name="feature_b",
                flag_type=FlagType.BOOLEAN,
                enabled=False,  # Disabled
                default_variation="off",
            ),
        ]
        
        solver = encoder.encode_flags(flags)
        
        # feature_b is disabled, should be impossible to enable
        assert not solver.check_state_possible({"feature_b": True})
    
    def test_encode_dependencies(self) -> None:
        """Test encoding flag dependencies."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        from flagguard.core.models import FlagDefinition, FlagType
        
        encoder = ConstraintEncoder()
        
        flags = [
            FlagDefinition(
                name="parent",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
            ),
            FlagDefinition(
                name="child",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
                dependencies=["parent"],
            ),
        ]
        
        solver = encoder.encode_flags(flags)
        
        # child=True, parent=False should be impossible
        assert not solver.check_state_possible({"child": True, "parent": False})
    
    def test_encode_exclusive_flags(self) -> None:
        """Test encoding mutually exclusive flags."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        
        encoder = ConstraintEncoder()
        encoder.encode_exclusive_flags([["plan_free", "plan_premium", "plan_enterprise"]])
        
        solver = encoder.solver
        
        # Any two enabled should be impossible
        assert not solver.check_state_possible({"plan_free": True, "plan_premium": True})
        assert not solver.check_state_possible({"plan_premium": True, "plan_enterprise": True})
    
    def test_encode_required_flags(self) -> None:
        """Test encoding required flags."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        
        encoder = ConstraintEncoder()
        encoder.encode_required_flags(["auth_enabled", "logging_enabled"])
        
        solver = encoder.solver
        
        # Disabling required flags should be impossible
        assert not solver.check_state_possible({"auth_enabled": False})
        assert not solver.check_state_possible({"logging_enabled": False})


@pytest.mark.skipif(not Z3_AVAILABLE, reason="Z3 not installed")
class TestDeadCodeFinder:
    """Tests for dead code detection."""
    
    def test_find_dead_code(self) -> None:
        """Test finding unreachable code."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.dead_code import DeadCodeFinder
        from flagguard.core.models import FlagUsage
        
        solver = FlagSATSolver()
        # feature_a is always off
        solver.add_always_off("feature_a")
        
        finder = DeadCodeFinder(solver)
        
        usages = [
            FlagUsage(
                flag_name="feature_a",
                file_path="app.py",
                line_number=10,
                column=4,
                containing_function="main",
                check_type="if",
                negated=False,  # Requires feature_a=True
                code_snippet='if is_enabled("feature_a"):',
            ),
        ]
        
        dead_blocks = finder.find_dead_code(usages)
        
        # Should find one dead code block
        assert len(dead_blocks) == 1
        assert dead_blocks[0].file_path == "app.py"
        assert dead_blocks[0].start_line == 10
    
    def test_no_dead_code_for_possible_states(self) -> None:
        """Test that reachable code is not flagged."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.dead_code import DeadCodeFinder
        from flagguard.core.models import FlagUsage
        
        solver = FlagSATSolver()
        # feature_a is always on
        solver.add_always_on("feature_a")
        
        finder = DeadCodeFinder(solver)
        
        usages = [
            FlagUsage(
                flag_name="feature_a",
                file_path="app.py",
                line_number=10,
                column=4,
                containing_function="main",
                check_type="if",
                negated=False,  # Requires feature_a=True, which is possible
                code_snippet='if is_enabled("feature_a"):',
            ),
        ]
        
        dead_blocks = finder.find_dead_code(usages)
        
        # Should find no dead code
        assert len(dead_blocks) == 0
