"""Flag usage tracking models."""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Set


@dataclass
class FlagUsage:
    """A location where a feature flag is checked in source code."""
    flag_name: str
    file_path: str
    line_number: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    containing_function: Optional[str] = None
    containing_class: Optional[str] = None
    check_type: str = "if"
    negated: bool = False
    code_snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "flag_name": self.flag_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "containing_function": self.containing_function,
            "containing_class": self.containing_class,
            "check_type": self.check_type,
            "negated": self.negated,
            "code_snippet": self.code_snippet,
        }

    @property
    def location(self) -> str:
        return f"{self.file_path}:{self.line_number}"


@dataclass
class FlagUsageDatabase:
    """Collection of all flag usages in a codebase."""
    usages: List[FlagUsage]
    files_scanned: int
    scan_time_seconds: float
    errors: List[str] = field(default_factory=list)

    def get_by_flag(self, flag_name: str) -> List[FlagUsage]:
        return [u for u in self.usages if u.flag_name == flag_name]

    def get_by_file(self, file_path: str) -> List[FlagUsage]:
        return [u for u in self.usages if u.file_path == file_path]

    def get_unique_flags(self) -> Set[str]:
        return {u.flag_name for u in self.usages}

    def to_dict(self) -> dict[str, Any]:
        return {
            "usages": [u.to_dict() for u in self.usages],
            "files_scanned": self.files_scanned,
            "scan_time_seconds": self.scan_time_seconds,
            "unique_flags": list(self.get_unique_flags()),
            "errors": self.errors,
        }
