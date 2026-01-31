"""Unit tests for AST extractors."""

from pathlib import Path

import pytest

from flagguard.parsers.ast.python import PythonFlagExtractor
from flagguard.parsers.ast.javascript import JavaScriptFlagExtractor
from flagguard.parsers.ast.scanner import SourceScanner
from flagguard.parsers.ast.languages import (
    SupportedLanguage,
    get_language_for_file,
    get_supported_extensions,
)


class TestLanguageRegistry:
    """Tests for language registry."""
    
    def test_get_language_for_python(self) -> None:
        """Test detection of Python files."""
        assert get_language_for_file("app.py") == SupportedLanguage.PYTHON
        assert get_language_for_file("/path/to/script.py") == SupportedLanguage.PYTHON
    
    def test_get_language_for_javascript(self) -> None:
        """Test detection of JavaScript files."""
        assert get_language_for_file("app.js") == SupportedLanguage.JAVASCRIPT
        assert get_language_for_file("component.jsx") == SupportedLanguage.JAVASCRIPT
    
    def test_get_language_for_typescript(self) -> None:
        """Test detection of TypeScript files."""
        assert get_language_for_file("app.ts") == SupportedLanguage.TYPESCRIPT
        assert get_language_for_file("component.tsx") == SupportedLanguage.TYPESCRIPT
    
    def test_unsupported_extension(self) -> None:
        """Test unsupported file extensions return None."""
        assert get_language_for_file("app.go") is None
        assert get_language_for_file("app.java") is None
    
    def test_get_supported_extensions(self) -> None:
        """Test getting all supported extensions."""
        extensions = get_supported_extensions()
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".ts" in extensions


class TestPythonFlagExtractor:
    """Tests for Python flag extractor."""
    
    def test_extract_simple_function_call(self, tmp_path: Path) -> None:
        """Test extracting simple is_enabled calls."""
        code = '''
def test():
    if is_enabled("my_flag"):
        pass
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "my_flag"
        assert usages[0].containing_function == "test"
    
    def test_extract_method_call(self, tmp_path: Path) -> None:
        """Test extracting method calls like flags.is_enabled()."""
        code = '''
def process():
    if flags.is_enabled("feature_x"):
        return True
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "feature_x"
    
    def test_extract_negated_check(self, tmp_path: Path) -> None:
        """Test detecting negated flag checks."""
        code = '''
def check():
    if not is_enabled("legacy_mode"):
        pass
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "legacy_mode"
        assert usages[0].negated is True
    
    def test_extract_class_method(self, tmp_path: Path) -> None:
        """Test extracting from class methods."""
        code = '''
class MyClass:
    def method(self):
        if is_enabled("class_feature"):
            pass
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "class_feature"
        assert usages[0].containing_class == "MyClass"
        assert usages[0].containing_function == "method"
    
    def test_extract_multiple_flags(self, tmp_path: Path) -> None:
        """Test extracting multiple flags from one file."""
        code = '''
def multi():
    if is_enabled("flag_a"):
        pass
    if is_enabled("flag_b"):
        pass
    if has_feature("flag_c"):
        pass
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(file_path)
        
        flag_names = {u.flag_name for u in usages}
        assert "flag_a" in flag_names
        assert "flag_b" in flag_names
        # has_feature should also be detected
    
    def test_extract_from_fixture(self, python_sample_dir: Path) -> None:
        """Test extraction from the Python sample fixture."""
        sample_file = python_sample_dir / "app.py"
        if not sample_file.exists():
            pytest.skip("Python sample fixture not found")
        
        extractor = PythonFlagExtractor()
        usages = extractor.extract(sample_file)
        
        # Should find multiple flag usages
        assert len(usages) > 0
        flag_names = {u.flag_name for u in usages}
        assert "premium_checkout" in flag_names


class TestJavaScriptFlagExtractor:
    """Tests for JavaScript flag extractor."""
    
    def test_extract_method_call(self, tmp_path: Path) -> None:
        """Test extracting method calls like flags.isEnabled()."""
        code = '''
function test() {
    if (flags.isEnabled("my_flag")) {
        return true;
    }
}
'''
        file_path = tmp_path / "test.js"
        file_path.write_text(code)
        
        extractor = JavaScriptFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "my_flag"
    
    def test_extract_launchdarkly_variation(self, tmp_path: Path) -> None:
        """Test extracting LaunchDarkly variation calls."""
        code = '''
function getFeature(user) {
    return ldClient.variation("feature_x", user, false);
}
'''
        file_path = tmp_path / "test.js"
        file_path.write_text(code)
        
        extractor = JavaScriptFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].flag_name == "feature_x"
    
    def test_extract_negated_check(self, tmp_path: Path) -> None:
        """Test detecting negated flag checks in JS."""
        code = '''
function check() {
    if (!flags.isEnabled("legacy_mode")) {
        return "new";
    }
}
'''
        file_path = tmp_path / "test.js"
        file_path.write_text(code)
        
        extractor = JavaScriptFlagExtractor()
        usages = extractor.extract(file_path)
        
        assert len(usages) == 1
        assert usages[0].negated is True
    
    def test_extract_from_fixture(self, javascript_sample_dir: Path) -> None:
        """Test extraction from the JavaScript sample fixture."""
        sample_file = javascript_sample_dir / "app.js"
        if not sample_file.exists():
            pytest.skip("JavaScript sample fixture not found")
        
        extractor = JavaScriptFlagExtractor()
        usages = extractor.extract(sample_file)
        
        # Should find multiple flag usages
        assert len(usages) > 0
        flag_names = {u.flag_name for u in usages}
        assert "premium_checkout" in flag_names


class TestSourceScanner:
    """Tests for unified source scanner."""
    
    def test_scan_python_directory(self, tmp_path: Path) -> None:
        """Test scanning a directory with Python files."""
        # Create test files
        (tmp_path / "app.py").write_text('''
def main():
    if is_enabled("feature"):
        pass
''')
        (tmp_path / "utils.py").write_text('''
def helper():
    if is_enabled("helper_flag"):
        pass
''')
        
        scanner = SourceScanner()
        db = scanner.scan_directory(tmp_path)
        
        assert db.files_scanned == 2
        assert len(db.usages) >= 2
        
        flag_names = db.get_unique_flags()
        assert "feature" in flag_names
        assert "helper_flag" in flag_names
    
    def test_scan_excludes_patterns(self, tmp_path: Path) -> None:
        """Test that exclusion patterns work."""
        # Create a file in excluded directory
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "test.py").write_text('is_enabled("should_skip")')
        
        # Create a file that should be scanned
        (tmp_path / "app.py").write_text('is_enabled("should_find")')
        
        scanner = SourceScanner()
        db = scanner.scan_directory(tmp_path)
        
        flag_names = db.get_unique_flags()
        assert "should_find" in flag_names
        assert "should_skip" not in flag_names
    
    def test_scan_mixed_languages(self, tmp_path: Path) -> None:
        """Test scanning directory with mixed languages."""
        (tmp_path / "app.py").write_text('is_enabled("py_flag")')
        (tmp_path / "app.js").write_text('flags.isEnabled("js_flag")')
        
        scanner = SourceScanner()
        db = scanner.scan_directory(tmp_path)
        
        flag_names = db.get_unique_flags()
        # Should find both Python and JS flags
        assert len(db.usages) >= 2


# Fixtures
@pytest.fixture
def python_sample_dir() -> Path:
    """Path to Python sample source code fixture."""
    return Path(__file__).parent.parent / "fixtures" / "source_code" / "python_sample"


@pytest.fixture
def javascript_sample_dir() -> Path:
    """Path to JavaScript sample source code fixture."""
    return Path(__file__).parent.parent / "fixtures" / "source_code" / "javascript_sample"
