"""Source code scanner for flag extraction.

This module provides the SourceScanner class that orchestrates
scanning directories for feature flag usage across multiple languages.
"""

import time
from pathlib import Path
from typing import Callable

from flagguard.core.models import FlagUsage, FlagUsageDatabase
from flagguard.core.logging import get_logger

logger = get_logger("scanner")


class SourceScanner:
    """Scans source code directories for feature flag usage.
    
    Coordinates language-specific extractors to find all flag checks
    in a codebase.
    
    Attributes:
        supported_extensions: Set of file extensions to scan
        exclude_patterns: Patterns to exclude from scanning
    """
    
    DEFAULT_EXCLUDES = {
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
    }
    
    def __init__(
        self,
        exclude_patterns: set[str] | None = None,
    ) -> None:
        """Initialize the scanner.
        
        Args:
            exclude_patterns: Additional directory names to exclude
        """
        self.exclude_patterns = self.DEFAULT_EXCLUDES.copy()
        if exclude_patterns:
            self.exclude_patterns.update(exclude_patterns)
        
        self._extractors: dict[str, Callable[[Path], list[FlagUsage]]] = {}
        self._setup_extractors()
    
    def _setup_extractors(self) -> None:
        """Setup language-specific extractors."""
        # Import extractors lazily
        try:
            from flagguard.parsers.ast.python import PythonFlagExtractor
            py_extractor = PythonFlagExtractor()
            self._extractors[".py"] = py_extractor.extract
        except ImportError:
            logger.warning("Python extractor not available")
        
        try:
            from flagguard.parsers.ast.javascript import JavaScriptFlagExtractor
            js_extractor = JavaScriptFlagExtractor()
            self._extractors[".js"] = js_extractor.extract
            self._extractors[".ts"] = js_extractor.extract
            self._extractors[".jsx"] = js_extractor.extract
            self._extractors[".tsx"] = js_extractor.extract
        except ImportError:
            logger.warning("JavaScript extractor not available")
    
    def scan_directory(
        self,
        root: Path,
        max_files: int | None = None,
    ) -> FlagUsageDatabase:
        """Scan a directory for feature flag usages.
        
        Args:
            root: Root directory to scan
            max_files: Maximum number of files to scan (None for no limit)
            
        Returns:
            FlagUsageDatabase containing all found usages
        """
        start_time = time.time()
        
        usages: list[FlagUsage] = []
        errors: list[str] = []
        files_scanned = 0
        
        for file_path in self._iter_files(root):
            if max_files and files_scanned >= max_files:
                break
            
            try:
                file_usages = self._scan_file(file_path)
                usages.extend(file_usages)
                files_scanned += 1
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                logger.debug(f"Error scanning {file_path}: {e}")
        
        scan_time = time.time() - start_time
        logger.info(f"Scanned {files_scanned} files in {scan_time:.2f}s")
        
        return FlagUsageDatabase(
            usages=usages,
            files_scanned=files_scanned,
            scan_time_seconds=scan_time,
            errors=errors,
        )
    
    def _iter_files(self, root: Path) -> list[Path]:
        """Iterate over scannable files in a directory."""
        files: list[Path] = []
        
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            
            # Check if in excluded directory
            if any(exclude in path.parts for exclude in self.exclude_patterns):
                continue
            
            # Check if we have an extractor for this extension
            if path.suffix in self._extractors:
                files.append(path)
        
        return files
    
    def _scan_file(self, file_path: Path) -> list[FlagUsage]:
        """Scan a single file for flag usages."""
        extractor = self._extractors.get(file_path.suffix)
        if not extractor:
            return []
        
        return extractor(file_path)
    
    def scan_file(self, file_path: Path) -> list[FlagUsage]:
        """Scan a single file for flag usages.
        
        Public method for scanning individual files.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            List of FlagUsage objects found
        """
        return self._scan_file(file_path)
