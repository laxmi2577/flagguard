"""Prompt templates for LLM explanations.

This module provides carefully crafted prompts for generating
human-readable explanations of technical analysis results.
"""

# =============================================================================
# Core Prompt Templates
# =============================================================================

CONFLICT_EXPLANATION_PROMPT = """You are a senior software engineer explaining a feature flag conflict.

**Conflict Details:**
- Flags involved: {flags}
- Impossible state: {state}
- Reason: {reason}
- Affected code: {locations}

**Your task:**
1. Explain what this conflict means in plain English
2. Describe why it's a problem
3. Suggest how to fix it

**Guidelines:**
- Be concise (3-5 sentences)
- Use clear, non-technical language where possible
- Focus on the business impact
- Provide actionable advice

**Response:**
"""

DEAD_CODE_EXPLANATION_PROMPT = """You are a code reviewer explaining dead code caused by feature flags.

**Dead Code Details:**
- File: {file_path}
- Lines: {start_line}-{end_line}
- Required flags: {required_flags}
- Why unreachable: {reason}

**Your task:**
1. Explain why this code can never run
2. Describe the risk of keeping it
3. Recommend what to do (delete, fix flags, etc.)

**Guidelines:**
- Be concise (3-4 sentences)
- Explain like you're talking to a junior developer
- Be specific about the solution

**Response:**
"""

EXECUTIVE_SUMMARY_PROMPT = """You are writing an executive summary of a feature flag analysis.

**Analysis Results:**
- Total flags analyzed: {total_flags}
- Conflicts found: {conflict_count}
- Critical: {critical_count}
- Dead code blocks: {dead_code_count}
- Files scanned: {files_scanned}

**Top Issues:**
{top_issues}

**Your task:**
Write a 2-3 paragraph executive summary that:
1. Summarizes the overall health of the flag configuration
2. Highlights the most important issues
3. Recommends immediate actions

**Guidelines:**
- Be professional and clear
- Focus on business impact
- Prioritize actionable recommendations

**Response:**
"""

DEPENDENCY_EXPLANATION_PROMPT = """Explain the following feature flag dependency chain:

{dependency_chain}

In 2-3 sentences, explain:
1. What this dependency means
2. Potential risks of this setup"""

FIX_SUGGESTION_PROMPT = """You are suggesting a fix for a feature flag conflict.

**Conflict:**
{conflict_description}

**Current Code:**
```
{code_snippet}
```

**Suggest:**
1. The specific change needed
2. Any code modifications required
3. How to test the fix

**Response:**
"""


# =============================================================================
# Formatting Helper Functions
# =============================================================================

def format_conflict_prompt(
    flags: list[str],
    state: dict[str, bool],
    reason: str,
    locations: list[str] | None = None,
) -> str:
    """Format the conflict explanation prompt.
    
    Args:
        flags: List of flag names involved in the conflict
        state: Dictionary of flag states that cause the conflict
        reason: Technical reason for the conflict
        locations: Optional list of affected code locations
        
    Returns:
        Formatted prompt string ready for LLM
    """
    state_str = ", ".join(f"{k}={'ON' if v else 'OFF'}" for k, v in state.items())
    locations_str = "\n".join(f"  - {loc}" for loc in (locations or [])) or "None specified"
    
    return CONFLICT_EXPLANATION_PROMPT.format(
        flags=", ".join(flags),
        state=state_str,
        reason=reason,
        locations=locations_str,
    )


def format_dead_code_prompt(
    file_path: str,
    start_line: int,
    end_line: int,
    required_flags: dict[str, bool],
    reason: str,
) -> str:
    """Format the dead code explanation prompt.
    
    Args:
        file_path: Path to the file containing dead code
        start_line: Starting line number of dead code
        end_line: Ending line number of dead code
        required_flags: Flag states required for code to execute
        reason: Why the code is unreachable
        
    Returns:
        Formatted prompt string
    """
    flags_str = ", ".join(f"{k}={'ON' if v else 'OFF'}" for k, v in required_flags.items())
    
    return DEAD_CODE_EXPLANATION_PROMPT.format(
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        required_flags=flags_str,
        reason=reason,
    )


def format_executive_summary_prompt(
    total_flags: int,
    conflict_count: int,
    critical_count: int,
    dead_code_count: int,
    files_scanned: int,
    top_issues: list[str],
) -> str:
    """Format the executive summary prompt.
    
    Args:
        total_flags: Number of flags analyzed
        conflict_count: Total conflicts detected
        critical_count: Number of critical conflicts
        dead_code_count: Dead code blocks found
        files_scanned: Source files scanned
        top_issues: List of top issue descriptions
        
    Returns:
        Formatted prompt string
    """
    issues_str = "\n".join(f"  {i+1}. {issue}" for i, issue in enumerate(top_issues))
    
    return EXECUTIVE_SUMMARY_PROMPT.format(
        total_flags=total_flags,
        conflict_count=conflict_count,
        critical_count=critical_count,
        dead_code_count=dead_code_count,
        files_scanned=files_scanned,
        top_issues=issues_str or "  None",
    )


def format_fix_suggestion_prompt(
    conflict_description: str,
    code_snippet: str,
) -> str:
    """Format the fix suggestion prompt.
    
    Args:
        conflict_description: Description of the conflict
        code_snippet: Relevant code snippet
        
    Returns:
        Formatted prompt string
    """
    return FIX_SUGGESTION_PROMPT.format(
        conflict_description=conflict_description,
        code_snippet=code_snippet,
    )

