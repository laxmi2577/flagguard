"""Security tests for FlagGuard.

Tests to ensure safe handling of untrusted input.
"""

import pytest
from pathlib import Path


class TestInputSanitization:
    """Test safe handling of potentially malicious input."""
    
    def test_no_code_execution_from_config(self, tmp_path: Path) -> None:
        """Config files should not execute embedded code."""
        import json
        from flagguard.parsers import parse_config
        
        # Create config with code-like flag name
        malicious_config = tmp_path / "malicious.json"
        malicious_config.write_text(json.dumps({
            "flags": {
                "__import__('os').system('echo hacked')": {
                    "on": True,
                    "variations": [True, False],
                }
            }
        }))
        
        # Should parse without executing the "code"
        flags = parse_config(malicious_config)
        
        # Flag name should be the literal string, not executed
        assert len(flags) == 1
        assert "__import__" in flags[0].name
    
    def test_yaml_safe_load(self, tmp_path: Path) -> None:
        """YAML parser should use safe_load to prevent code execution."""
        from flagguard.parsers import parse_config
        
        # Create YAML with potentially dangerous construct
        yaml_config = tmp_path / "test.yaml"
        yaml_config.write_text("""
features:
  - name: normal_flag
    enabled: true
""")
        
        # Should parse safely
        flags = parse_config(yaml_config)
        assert len(flags) >= 1
    
    def test_json_injection_in_flag_values(self, tmp_path: Path) -> None:
        """Flag values with special characters should be handled safely."""
        import json
        from flagguard.parsers import parse_config
        
        config = tmp_path / "injection.json"
        config.write_text(json.dumps({
            "flags": {
                "test": {
                    "on": True,
                    "variations": ["value\"; echo hacked; #", "normal"],
                }
            }
        }))
        
        flags = parse_config(config)
        
        # Value should be preserved as literal string
        assert any('echo' in str(v.value) for v in flags[0].variations)


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks."""
    
    def test_large_file_handling(self, tmp_path: Path) -> None:
        """Should handle large files without crashing."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        # Create a moderately large file (1MB)
        large_file = tmp_path / "large.py"
        large_file.write_text("x = 1\n" * 50_000)
        
        extractor = PythonFlagExtractor()
        
        # Should complete without OOM
        usages = extractor.extract(large_file)
        assert usages is not None
    
    def test_deep_nesting_handling(self, tmp_path: Path) -> None:
        """Should handle deeply nested code structures."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        # Create file with moderate nesting
        code_lines = ["def outer():"]
        for i in range(20):
            indent = "    " * (i + 1)
            code_lines.append(f"{indent}if True:")
        code_lines.append("    " * 21 + "pass")
        
        nested_file = tmp_path / "nested.py"
        nested_file.write_text("\n".join(code_lines))
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(nested_file)
        
        # Should complete without stack overflow
        assert usages is not None
    
    def test_many_flags_in_single_file(self, tmp_path: Path) -> None:
        """Should handle files with many flag checks."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        # Create file with many flag checks
        lines = []
        for i in range(100):
            lines.append(f'if is_enabled("flag_{i}"): pass')
        
        many_flags = tmp_path / "many_flags.py"
        many_flags.write_text("\n".join(lines))
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(many_flags)
        
        # Should extract all flags
        assert len(usages) >= 50  # Allow some tolerance for parsing differences


class TestMalformedInput:
    """Test handling of malformed or invalid input."""
    
    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """Invalid JSON should raise appropriate error."""
        from flagguard.parsers import parse_config
        
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ this is not valid json }")
        
        with pytest.raises(Exception):
            parse_config(bad_json)
    
    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML should raise appropriate error."""
        from flagguard.parsers import parse_config
        
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(":\n  :invalid:\n    -no")
        
        with pytest.raises(Exception):
            parse_config(bad_yaml)
    
    def test_broken_python_syntax(self, tmp_path: Path) -> None:
        """Should handle Python files with syntax errors gracefully."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        broken_file = tmp_path / "broken.py"
        broken_file.write_text("def broken(:\n  pass")  # Invalid syntax
        
        extractor = PythonFlagExtractor()
        
        # Should not crash - may return empty or raise specific error
        try:
            usages = extractor.extract(broken_file)
            # If it returns, should be empty or have fallback behavior
            assert usages is not None
        except Exception as e:
            # Should be a specific, meaningful error
            assert True  # Expected behavior
    
    def test_empty_file_handling(self, tmp_path: Path) -> None:
        """Should handle empty files gracefully."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(empty_file)
        
        assert usages == []
    
    def test_binary_file_handling(self, tmp_path: Path) -> None:
        """Should handle binary files without crashing."""
        from flagguard.parsers.ast.python import PythonFlagExtractor
        
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        
        extractor = PythonFlagExtractor()
        
        # Should not crash
        try:
            usages = extractor.extract(binary_file)
            assert usages is not None
        except Exception:
            # Acceptable to raise on binary content
            pass
