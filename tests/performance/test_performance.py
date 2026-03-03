"""Performance tests for FlagGuard.

Benchmarks to ensure acceptable performance for common use cases.
Covers: config parsing, codebase scanning, conflict detection, memory usage,
and end-to-end pipeline throughput at enterprise scale.
"""

import json
import time
import pytest
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
# Config Parsing Performance
# ─────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestParsingPerformance:
    """Benchmark configuration parsing performance."""

    def test_parse_100_flags(self, tmp_path: Path) -> None:
        """Benchmark parsing config with 100 flags."""
        from flagguard.parsers import parse_config

        # Create config with 100 flags
        flags = {}
        for i in range(100):
            flags[f"flag_{i}"] = {
                "on": i % 2 == 0,
                "variations": [True, False],
                "prerequisites": [{"key": f"flag_{i-1}"}] if i > 0 else [],
            }

        config_path = tmp_path / "large_config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        start = time.time()
        parsed = parse_config(config_path)
        duration = time.time() - start

        assert len(parsed) == 100
        assert duration < 2.0, f"Parsing took {duration:.2f}s, expected < 2s"

    def test_parse_500_flags(self, tmp_path: Path) -> None:
        """Benchmark parsing config with 500 flags and complex dependencies."""
        from flagguard.parsers import parse_config

        flags = {}
        for i in range(500):
            prereqs = []
            if i > 0:
                prereqs.append({"key": f"flag_{i-1}"})
            if i > 10:
                prereqs.append({"key": f"flag_{i-10}"})

            flags[f"flag_{i}"] = {
                "on": i % 3 != 0,
                "variations": [True, False],
                "prerequisites": prereqs,
                "description": f"Feature flag number {i}",
                "tags": [f"group_{i // 50}"],
            }

        config_path = tmp_path / "enterprise_config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        start = time.time()
        parsed = parse_config(config_path)
        duration = time.time() - start

        assert len(parsed) == 500
        assert duration < 5.0, f"Parsing 500 flags took {duration:.2f}s, expected < 5s"

    def test_parse_1000_flags(self, tmp_path: Path) -> None:
        """Benchmark parsing config with 1000 flags."""
        from flagguard.parsers import parse_config

        flags = {}
        for i in range(1000):
            flags[f"flag_{i}"] = {
                "on": True,
                "variations": [True, False],
            }

        config_path = tmp_path / "huge_config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        start = time.time()
        parsed = parse_config(config_path)
        duration = time.time() - start

        assert len(parsed) == 1000
        assert duration < 5.0, f"Parsing took {duration:.2f}s, expected < 5s"

    def test_parse_unleash_yaml_100_features(self, tmp_path: Path) -> None:
        """Benchmark parsing Unleash YAML with 100 features."""
        from flagguard.parsers.unleash import UnleashParser

        lines = ["features:"]
        for i in range(100):
            lines.append(f"  - name: feature_{i}")
            lines.append(f"    enabled: {'true' if i % 2 == 0 else 'false'}")
            lines.append(f"    description: 'Feature number {i}'")
            if i % 5 == 0:
                lines.append("    strategies:")
                lines.append("      - name: default")

        yaml_content = "\n".join(lines)
        parser = UnleashParser()

        start = time.time()
        parsed = parser.parse(yaml_content)
        duration = time.time() - start

        assert len(parsed) == 100
        assert duration < 3.0, f"YAML parsing took {duration:.2f}s, expected < 3s"


# ─────────────────────────────────────────────────────────────────
# Source Code Scanning Performance
# ─────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestScanningPerformance:
    """Benchmark source code scanning performance."""

    def test_scan_100_files(self, tmp_path: Path) -> None:
        """Benchmark scanning 100 Python files."""
        from flagguard.parsers.ast import SourceScanner

        # Create 100 Python files
        for i in range(100):
            subdir = tmp_path / f"module_{i // 10}"
            subdir.mkdir(exist_ok=True)

            file_path = subdir / f"file_{i}.py"
            file_path.write_text(f'''
def func_{i}():
    if is_enabled("flag_{i}"):
        return {i}
''')

        scanner = SourceScanner()

        start = time.time()
        usages = scanner.scan_directory(tmp_path)
        duration = time.time() - start

        assert usages.files_scanned == 100
        assert len(usages.usages) >= 50  # Allow some tolerance
        assert duration < 15.0, f"Scanning took {duration:.2f}s, expected < 15s"

    def test_scan_500_files(self, tmp_path: Path) -> None:
        """Benchmark scanning 500 Python files across nested modules."""
        from flagguard.parsers.ast import SourceScanner

        for i in range(500):
            # Deep nesting: module/sub/file
            subdir = tmp_path / f"pkg_{i // 100}" / f"module_{i // 10}"
            subdir.mkdir(parents=True, exist_ok=True)

            file_path = subdir / f"service_{i}.py"
            file_path.write_text(f'''
class Service{i}:
    def handle(self):
        if is_enabled("flag_{i}"):
            return self.process_{i}()
        if is_enabled("fallback_{i}"):
            return self.fallback()
''')

        scanner = SourceScanner()

        start = time.time()
        usages = scanner.scan_directory(tmp_path)
        duration = time.time() - start

        assert usages.files_scanned == 500
        assert len(usages.usages) >= 400  # 2 flags per file, allow tolerance
        assert duration < 60.0, f"Scanning 500 files took {duration:.2f}s, expected < 60s"

    def test_scan_mixed_languages(self, tmp_path: Path) -> None:
        """Benchmark scanning mixed Python and JavaScript files."""
        from flagguard.parsers.ast import SourceScanner

        # Create Python files
        py_dir = tmp_path / "python"
        py_dir.mkdir()
        for i in range(25):
            (py_dir / f"app_{i}.py").write_text(f'if is_enabled("py_flag_{i}"): pass')

        # Create JavaScript files
        js_dir = tmp_path / "javascript"
        js_dir.mkdir()
        for i in range(25):
            (js_dir / f"app_{i}.js").write_text(f'if (isEnabled("js_flag_{i}")) {{}}')

        scanner = SourceScanner()

        start = time.time()
        usages = scanner.scan_directory(tmp_path)
        duration = time.time() - start

        assert usages.files_scanned == 50
        assert duration < 10.0, f"Scanning took {duration:.2f}s, expected < 10s"

    def test_scan_large_files(self, tmp_path: Path) -> None:
        """Benchmark scanning files with many flag checks per file."""
        from flagguard.parsers.ast import SourceScanner

        for i in range(20):
            file_path = tmp_path / f"large_module_{i}.py"
            lines = []
            for j in range(50):
                lines.append(f'def handler_{j}():')
                lines.append(f'    if is_enabled("flag_{i}_{j}"):')
                lines.append(f'        return process_{j}()')
                lines.append('')
            file_path.write_text('\n'.join(lines))

        scanner = SourceScanner()

        start = time.time()
        usages = scanner.scan_directory(tmp_path)
        duration = time.time() - start

        assert usages.files_scanned == 20
        assert len(usages.usages) >= 500  # 50 flags × 20 files
        assert duration < 30.0, f"Scanning large files took {duration:.2f}s"


# ─────────────────────────────────────────────────────────────────
# Conflict Detection Performance
# ─────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestConflictDetectionPerformance:
    """Benchmark conflict detection performance."""

    def test_detect_conflicts_50_flags(self, tmp_path: Path) -> None:
        """Benchmark conflict detection with 50 flags."""
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector

        # Create config with dependencies
        flags = {}
        for i in range(50):
            flags[f"flag_{i}"] = {
                "on": True,
                "variations": [True, False],
                "prerequisites": [{"key": f"flag_{i-1}"}] if i > 5 else [],
            }

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        parsed = parse_config(config_path)

        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(parsed)

        start = time.time()
        conflicts = detector.detect_all_conflicts()
        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 30.0, f"Detection took {duration:.2f}s, expected < 30s"

    def test_detect_conflicts_100_flags_mixed(self, tmp_path: Path) -> None:
        """Benchmark conflict detection with 100 flags and mixed constraints."""
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector

        flags = {}
        for i in range(100):
            prereqs = []
            if i > 0 and i % 3 == 0:
                prereqs.append({"key": f"flag_{i-1}"})
            if i > 20 and i % 7 == 0:
                prereqs.append({"key": f"flag_{i-5}"})

            flags[f"flag_{i}"] = {
                "on": i % 4 != 0,  # Some disabled
                "variations": [True, False],
                "prerequisites": prereqs,
            }

        config_path = tmp_path / "complex_config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        parsed = parse_config(config_path)

        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(parsed)

        start = time.time()
        conflicts = detector.detect_all_conflicts()
        duration = time.time() - start

        assert duration < 60.0, f"Detection of 100 flags took {duration:.2f}s, expected < 60s"

    def test_constraint_encoding_performance(self) -> None:
        """Benchmark encoding 200 flags into SAT constraints."""
        from flagguard.analysis.constraint_encoder import ConstraintEncoder
        from flagguard.core.models import FlagDefinition, FlagType

        flags = []
        for i in range(200):
            deps = []
            if i > 0 and i % 2 == 0:
                deps.append(f"flag_{i-1}")

            flags.append(FlagDefinition(
                name=f"flag_{i}",
                flag_type=FlagType.BOOLEAN,
                enabled=i % 3 != 0,
                default_variation="on" if i % 3 != 0 else "off",
                dependencies=deps,
            ))

        encoder = ConstraintEncoder()

        start = time.time()
        solver = encoder.encode_flags(flags)
        duration = time.time() - start

        assert len(solver.variables) == 200
        assert duration < 10.0, f"Encoding 200 flags took {duration:.2f}s, expected < 10s"


# ─────────────────────────────────────────────────────────────────
# Memory Usage Performance
# ─────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestMemoryPerformance:
    """Test memory usage stays within bounds."""

    def test_memory_usage_large_scan(self, tmp_path: Path) -> None:
        """Memory usage should stay reasonable for large scans."""
        import sys
        from flagguard.parsers.ast import SourceScanner

        # Create 50 files with moderate content
        for i in range(50):
            file_path = tmp_path / f"file_{i}.py"
            lines = [f'if is_enabled("flag_{j}"): pass' for j in range(10)]
            file_path.write_text("\n".join(lines))

        scanner = SourceScanner()

        # Get baseline memory
        initial_size = sys.getsizeof(scanner)

        usages = scanner.scan_directory(tmp_path)

        # Result should not be excessively large
        result_size = sys.getsizeof(usages) + sum(
            sys.getsizeof(u) for u in usages.usages
        )

        # Very rough check - result shouldn't be > 10MB
        assert result_size < 10 * 1024 * 1024, f"Result size: {result_size / 1024 / 1024:.2f}MB"

    def test_memory_usage_solver(self) -> None:
        """SAT solver memory should stay bounded with many variables."""
        import tracemalloc
        from flagguard.analysis.z3_wrapper import FlagSATSolver

        tracemalloc.start()

        solver = FlagSATSolver()

        # Create 100 variables with constraints
        for i in range(100):
            solver.get_or_create_var(f"flag_{i}")
            if i > 0:
                solver.add_requires(f"flag_{i}", f"flag_{i-1}")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory for 100 vars + constraints should be < 50MB
        assert peak < 50 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024:.2f}MB"


# ─────────────────────────────────────────────────────────────────
# End-to-End Pipeline Performance
# ─────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestEndToEndPerformance:
    """Benchmark full analysis pipeline throughput."""

    def test_full_pipeline_small(self, tmp_path: Path) -> None:
        """End-to-end: 20 flags + 10 source files."""
        from flagguard.parsers import parse_config
        from flagguard.parsers.ast import SourceScanner
        from flagguard.analysis import FlagSATSolver, ConflictDetector

        # Config
        flags = {}
        for i in range(20):
            flags[f"flag_{i}"] = {
                "on": i % 3 != 0,
                "variations": [True, False],
                "prerequisites": [{"key": f"flag_{i-1}"}] if i > 0 else [],
            }

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        # Source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        for i in range(10):
            (src_dir / f"module_{i}.py").write_text(
                f'if is_enabled("flag_{i}"): pass\nif is_enabled("flag_{i+10}"): pass'
            )

        start = time.time()

        # Step 1: Parse config
        parsed = parse_config(config_path)

        # Step 2: Scan source
        scanner = SourceScanner()
        usages = scanner.scan_directory(src_dir)

        # Step 3: Detect conflicts
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(parsed)
        conflicts = detector.detect_all_conflicts()

        total_duration = time.time() - start

        assert len(parsed) == 20
        assert usages.files_scanned == 10
        assert total_duration < 30.0, f"Full pipeline small took {total_duration:.2f}s"

    def test_full_pipeline_medium(self, tmp_path: Path) -> None:
        """End-to-end: 100 flags + 50 source files."""
        from flagguard.parsers import parse_config
        from flagguard.parsers.ast import SourceScanner
        from flagguard.analysis import FlagSATSolver, ConflictDetector

        # Config
        flags = {}
        for i in range(100):
            flags[f"flag_{i}"] = {
                "on": i % 2 == 0,
                "variations": [True, False],
                "prerequisites": [{"key": f"flag_{i-1}"}] if i > 5 else [],
            }

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"flags": flags}))

        # Source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        for i in range(50):
            (src_dir / f"service_{i}.py").write_text(
                f'if is_enabled("flag_{i}"): pass\nif is_enabled("flag_{i+50}"): pass'
            )

        start = time.time()

        parsed = parse_config(config_path)
        scanner = SourceScanner()
        usages = scanner.scan_directory(src_dir)
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(parsed)
        conflicts = detector.detect_all_conflicts()

        total_duration = time.time() - start

        assert len(parsed) == 100
        assert usages.files_scanned == 50
        assert total_duration < 60.0, f"Full pipeline medium took {total_duration:.2f}s"
