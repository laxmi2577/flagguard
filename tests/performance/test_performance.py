"""Performance tests for FlagGuard.

Benchmarks to ensure acceptable performance for common use cases.
"""

import json
import time
import pytest
from pathlib import Path


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
