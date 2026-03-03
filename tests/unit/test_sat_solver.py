"""Unit tests for SAT solver, conflict detection, constraint encoding, and dead code finder."""

import pytest

# Check if Z3 is available
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────
# SAT Solver Core Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_duplicate_variable_returns_same(self) -> None:
        """Getting same variable twice returns identical reference."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        var1 = solver.get_or_create_var("flag_a")
        var2 = solver.get_or_create_var("flag_a")

        assert var1 is var2
        assert len(solver.variables) == 1

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

    def test_chained_dependencies(self) -> None:
        """Test A→B→C→D chain: enabling A requires entire chain."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        solver.add_requires("d", "c")
        solver.add_requires("c", "b")
        solver.add_requires("b", "a")

        # D=True requires entire chain: a=T, b=T, c=T, d=T
        assert solver.check_state_possible({
            "a": True, "b": True, "c": True, "d": True
        })

        # D=True but a=False should be impossible (transitive)
        assert not solver.check_state_possible({"d": True, "a": False})

        # D=True but b=False should be impossible
        assert not solver.check_state_possible({"d": True, "b": False})

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

    def test_combined_requires_and_conflicts(self) -> None:
        """Test combining requires + conflicts constraints."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        # premium requires payment, but payment conflicts with free
        solver.add_requires("premium", "payment")
        solver.add_conflicts("payment", "free")

        # premium=T, payment=T, free=F: valid
        assert solver.check_state_possible({
            "premium": True, "payment": True, "free": False
        })

        # premium=T, free=T: impossible (payment must be on, but conflicts with free)
        assert not solver.check_state_possible({
            "premium": True, "payment": True, "free": True
        })

    def test_combined_always_on_and_requires(self) -> None:
        """Always-on flag combined with requires."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        solver.add_always_on("feature")
        solver.add_requires("feature", "base")

        # base must also be on (because feature is always on and requires base)
        assert not solver.check_state_possible({"base": False})
        assert solver.check_state_possible({"base": True, "feature": True})

    def test_impossible_system(self) -> None:
        """System with contradictory constraints should detect impossibility."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        solver.add_always_on("flag_a")
        solver.add_always_off("flag_a")

        # No valid state should be possible
        assert not solver.check_state_possible({"flag_a": True})
        assert not solver.check_state_possible({"flag_a": False})

    def test_many_variables(self) -> None:
        """Solver should handle 50+ variables without issue."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        solver = FlagSATSolver()
        for i in range(50):
            solver.get_or_create_var(f"flag_{i}")

        assert len(solver.variables) == 50
        assert solver.check_state_possible({"flag_0": True, "flag_49": True})


# ─────────────────────────────────────────────────────────────────
# Conflict Detector Tests
# ─────────────────────────────────────────────────────────────────

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
        from flagguard.core.models import FlagDefinition, FlagType

        solver = FlagSATSolver()
        detector = ConflictDetector(solver)

        flags = [
            FlagDefinition(
                name="premium",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
                conflicts=["free_tier"],
            ),
            FlagDefinition(
                name="free_tier",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
                conflicts=["premium"],
            ),
        ]

        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()

        # Should find: premium=True AND free_tier=True is impossible
        assert len(conflicts) > 0
        assert any(
            "premium" in c.flags_involved and "free_tier" in c.flags_involved
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

    def test_load_multiple_flags_with_mixed_states(self) -> None:
        """Load flags with mix of enabled/disabled states."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        from flagguard.core.models import FlagDefinition, FlagType

        solver = FlagSATSolver()
        detector = ConflictDetector(solver)

        flags = [
            FlagDefinition(
                name="active",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
            ),
            FlagDefinition(
                name="deprecated",
                flag_type=FlagType.BOOLEAN,
                enabled=False,
                default_variation="off",
            ),
            FlagDefinition(
                name="depends_on_deprecated",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_variation="on",
                dependencies=["deprecated"],
            ),
        ]

        detector.load_flags(flags)

        # depends_on_deprecated=True requires deprecated=True,
        # so depends_on_deprecated=True AND deprecated=False is impossible
        conflict = detector.check_state({"depends_on_deprecated": True, "deprecated": False})
        assert conflict is not None

    def test_load_chained_flags(self) -> None:
        """Load flags with chained dependencies A→B→C."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.conflict_detector import ConflictDetector
        from flagguard.core.models import FlagDefinition, FlagType

        solver = FlagSATSolver()
        detector = ConflictDetector(solver)

        flags = [
            FlagDefinition(name="base", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on"),
            FlagDefinition(name="mid", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["base"]),
            FlagDefinition(name="top", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["mid"]),
        ]

        detector.load_flags(flags)

        # top=True, base=False is impossible (transitive: top→mid→base)
        conflict = detector.check_state({"top": True, "base": False})
        assert conflict is not None

        # Verify all-on is valid
        no_conflict = detector.check_state({"top": True, "mid": True, "base": True})
        assert no_conflict is None


# ─────────────────────────────────────────────────────────────────
# Constraint Encoder Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_encode_chained_dependencies(self) -> None:
        """Encoder should handle deep dependency chains."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        from flagguard.core.models import FlagDefinition, FlagType

        encoder = ConstraintEncoder()

        flags = [
            FlagDefinition(name="level_1", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on"),
            FlagDefinition(name="level_2", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["level_1"]),
            FlagDefinition(name="level_3", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["level_2"]),
            FlagDefinition(name="level_4", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["level_3"]),
        ]

        solver = encoder.encode_flags(flags)

        # level_4=True, level_1=False => impossible
        assert not solver.check_state_possible({"level_4": True, "level_1": False})

    def test_encode_mixed_constraints(self) -> None:
        """Combine multiple constraint types in one encoding pass."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        from flagguard.core.models import FlagDefinition, FlagType

        encoder = ConstraintEncoder()

        flags = [
            FlagDefinition(name="auth", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on"),
            FlagDefinition(name="premium", flag_type=FlagType.BOOLEAN, enabled=True, default_variation="on", dependencies=["auth"]),
            FlagDefinition(name="legacy", flag_type=FlagType.BOOLEAN, enabled=False, default_variation="off"),
        ]

        solver = encoder.encode_flags(flags)
        encoder.encode_required_flags(["auth"])

        # auth can't be disabled (it's required)
        assert not solver.check_state_possible({"auth": False})
        # legacy can't be enabled (it's disabled)
        assert not solver.check_state_possible({"legacy": True})
        # premium needs auth, which is required => always satisfiable
        assert solver.check_state_possible({"premium": True, "auth": True})


# ─────────────────────────────────────────────────────────────────
# Dead Code Finder Tests
# ─────────────────────────────────────────────────────────────────

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

    def test_dead_code_negated_check(self) -> None:
        """Negated check for always-on flag should be dead code."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.dead_code import DeadCodeFinder
        from flagguard.core.models import FlagUsage

        solver = FlagSATSolver()
        solver.add_always_on("feature_a")

        finder = DeadCodeFinder(solver)

        usages = [
            FlagUsage(
                flag_name="feature_a",
                file_path="utils.py",
                line_number=20,
                column=4,
                containing_function="helper",
                check_type="if",
                negated=True,  # not is_enabled("feature_a") - always False
                code_snippet='if not is_enabled("feature_a"):',
            ),
        ]

        dead_blocks = finder.find_dead_code(usages)

        # Negated check on always-on flag => dead code
        assert len(dead_blocks) == 1

    def test_multiple_dead_code_blocks(self) -> None:
        """Detect multiple dead code blocks across files."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.dead_code import DeadCodeFinder
        from flagguard.core.models import FlagUsage

        solver = FlagSATSolver()
        solver.add_always_off("old_feature")
        solver.add_always_off("deprecated")

        finder = DeadCodeFinder(solver)

        usages = [
            FlagUsage(
                flag_name="old_feature",
                file_path="app.py",
                line_number=10,
                column=4,
                containing_function="func_a",
                check_type="if",
                negated=False,
                code_snippet='if is_enabled("old_feature"):',
            ),
            FlagUsage(
                flag_name="deprecated",
                file_path="service.py",
                line_number=30,
                column=8,
                containing_function="func_b",
                check_type="if",
                negated=False,
                code_snippet='if is_enabled("deprecated"):',
            ),
        ]

        dead_blocks = finder.find_dead_code(usages)

        assert len(dead_blocks) == 2
        files = {b.file_path for b in dead_blocks}
        assert "app.py" in files
        assert "service.py" in files

    def test_no_dead_code_unconstrained(self) -> None:
        """Unconstrained flags should not produce dead code."""
        from flagguard.analysis.z3_wrapper import FlagSATSolver
        from flagguard.analysis.dead_code import DeadCodeFinder
        from flagguard.core.models import FlagUsage

        solver = FlagSATSolver()
        solver.get_or_create_var("flexible_flag")

        finder = DeadCodeFinder(solver)

        usages = [
            FlagUsage(
                flag_name="flexible_flag",
                file_path="app.py",
                line_number=5,
                column=4,
                containing_function="main",
                check_type="if",
                negated=False,
                code_snippet='if is_enabled("flexible_flag"):',
            ),
        ]

        dead_blocks = finder.find_dead_code(usages)
        assert len(dead_blocks) == 0
