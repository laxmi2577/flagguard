"""Terraform & Infrastructure-as-Code Integration API routes.

Detect and analyze feature flags defined in Terraform, Pulumi,
CloudFormation, and other IaC configurations.
"""

import json
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import User
from flagguard.api.auth import get_current_user, require_role

router = APIRouter(prefix="/iac", tags=["Terraform / IaC Integration"])


# --- Schemas ---
class IaCFlag(BaseModel):
    name: str
    source: str  # terraform, pulumi, cloudformation
    file: str
    line: int | None = None
    resource_type: str
    enabled: bool | None = None
    value: str | None = None

class IaCAnalysisResult(BaseModel):
    source_type: str
    total_flags_found: int
    flags: list[IaCFlag]
    warnings: list[str]


# --- Routes ---
@router.post("/analyze", response_model=IaCAnalysisResult)
def analyze_iac_file(
    iac_file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
):
    """Analyze a Terraform/IaC file for feature flag definitions (analyst+ only)."""
    content = iac_file.file.read().decode("utf-8", errors="replace")
    filename = iac_file.filename or "unknown"

    flags = []
    warnings = []
    source_type = "unknown"

    if filename.endswith((".tf", ".tf.json")):
        source_type = "terraform"
        flags, warnings = _parse_terraform(content, filename)
    elif filename.endswith((".yaml", ".yml")):
        source_type = _detect_iac_yaml_type(content)
        flags, warnings = _parse_yaml_iac(content, filename, source_type)
    elif filename.endswith(".json"):
        source_type = "cloudformation" if '"AWSTemplateFormatVersion"' in content else "terraform-json"
        flags, warnings = _parse_json_iac(content, filename, source_type)
    else:
        warnings.append(f"Unsupported file type: {filename}. Supported: .tf, .yaml, .yml, .json")

    return IaCAnalysisResult(
        source_type=source_type,
        total_flags_found=len(flags),
        flags=flags,
        warnings=warnings,
    )


@router.get("/supported-formats")
def supported_formats():
    """List supported IaC formats and what FlagGuard detects in each."""
    return {
        "formats": [
            {
                "name": "Terraform (.tf)",
                "detects": ["variable blocks with flag-like names", "LaunchDarkly provider resources",
                            "feature_flag resources", "conditional expressions"],
            },
            {
                "name": "Terraform JSON (.tf.json)",
                "detects": ["variable definitions", "resource blocks with flag patterns"],
            },
            {
                "name": "CloudFormation (.yaml/.json)",
                "detects": ["AWS AppConfig feature flags", "SSM parameters with flag patterns",
                            "Condition blocks"],
            },
            {
                "name": "Pulumi (.yaml)",
                "detects": ["Config values with flag patterns", "Feature flag resources"],
            },
        ]
    }


# --- Parsers ---
def _parse_terraform(content: str, filename: str) -> tuple[list[IaCFlag], list[str]]:
    """Parse Terraform HCL for feature flags."""
    flags = []
    warnings = []

    # Match variable blocks that look like feature flags
    var_pattern = re.compile(
        r'variable\s+"(\w*(?:flag|feature|toggle|enabled|enable|ff_)\w*)"\s*\{([^}]*)\}',
        re.IGNORECASE | re.DOTALL
    )
    for match in var_pattern.finditer(content):
        name = match.group(1)
        body = match.group(2)
        default_match = re.search(r'default\s*=\s*(true|false|"[^"]*")', body, re.IGNORECASE)
        enabled = None
        value = None
        if default_match:
            val = default_match.group(1).strip('"')
            if val.lower() in ("true", "false"):
                enabled = val.lower() == "true"
            value = val

        flags.append(IaCFlag(
            name=name, source="terraform", file=filename,
            line=content[:match.start()].count('\n') + 1,
            resource_type="variable", enabled=enabled, value=value,
        ))

    # Match LaunchDarkly or feature flag resources
    resource_pattern = re.compile(
        r'resource\s+"(\w*(?:feature_flag|launchdarkly|flag)\w*)"\s+"(\w+)"\s*\{',
        re.IGNORECASE
    )
    for match in resource_pattern.finditer(content):
        flags.append(IaCFlag(
            name=match.group(2), source="terraform", file=filename,
            line=content[:match.start()].count('\n') + 1,
            resource_type=match.group(1), enabled=None, value=None,
        ))

    if not flags:
        warnings.append("No feature flag patterns found in Terraform file.")

    return flags, warnings


def _parse_yaml_iac(content: str, filename: str, source_type: str) -> tuple[list[IaCFlag], list[str]]:
    """Parse YAML IaC files for feature flags."""
    import yaml
    flags = []
    warnings = []

    try:
        data = yaml.safe_load(content)
    except Exception as e:
        warnings.append(f"YAML parse error: {str(e)}")
        return flags, warnings

    if not isinstance(data, dict):
        warnings.append("YAML root is not a dictionary")
        return flags, warnings

    # Search for flag-like keys recursively
    _find_flags_in_dict(data, flags, filename, source_type)

    if not flags:
        warnings.append("No feature flag patterns found.")

    return flags, warnings


def _parse_json_iac(content: str, filename: str, source_type: str) -> tuple[list[IaCFlag], list[str]]:
    """Parse JSON IaC files for feature flags."""
    flags = []
    warnings = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        warnings.append(f"JSON parse error: {str(e)}")
        return flags, warnings

    _find_flags_in_dict(data, flags, filename, source_type)

    if not flags:
        warnings.append("No feature flag patterns found.")

    return flags, warnings


def _find_flags_in_dict(data: dict, flags: list, filename: str, source: str, prefix: str = ""):
    """Recursively find flag-like keys in a dictionary."""
    flag_patterns = re.compile(r'(?:flag|feature|toggle|enabled|enable|ff_)', re.IGNORECASE)

    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if flag_patterns.search(key):
                enabled = None
                val_str = str(value) if value is not None else None
                if isinstance(value, bool):
                    enabled = value
                elif isinstance(value, str) and value.lower() in ("true", "false"):
                    enabled = value.lower() == "true"

                flags.append(IaCFlag(
                    name=full_key, source=source, file=filename,
                    resource_type="config", enabled=enabled, value=val_str,
                ))

            if isinstance(value, dict):
                _find_flags_in_dict(value, flags, filename, source, full_key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        _find_flags_in_dict(item, flags, filename, source, f"{full_key}[{i}]")


def _detect_iac_yaml_type(content: str) -> str:
    """Detect if YAML is CloudFormation, Pulumi, or generic."""
    if "AWSTemplateFormatVersion" in content:
        return "cloudformation"
    if "pulumi" in content.lower():
        return "pulumi"
    return "generic-yaml"
