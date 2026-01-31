"""Prompt templates for LLM explanations."""

CONFLICT_EXPLANATION_PROMPT = """You are a senior software engineer explaining a feature flag conflict.

Conflict Details:
- Flags involved: {flags}
- Conflicting values: {values}
- Reason: {reason}

Explain in 3-4 sentences:
1. What this conflict means
2. Why it's a problem
3. How to fix it

Be concise and technical but accessible."""

DEAD_CODE_EXPLANATION_PROMPT = """You are a senior software engineer explaining dead code.

Dead Code Details:
- File: {file_path}
- Lines: {start_line}-{end_line}
- Required flags: {flags}
- Code snippet: {code}

Explain in 2-3 sentences:
1. Why this code can never execute
2. What action to take (remove or fix flag config)

Be concise."""

EXECUTIVE_SUMMARY_PROMPT = """You are a software architect writing an executive summary.

Analysis Results:
- Total flags analyzed: {flag_count}
- Conflicts found: {conflict_count}
- Dead code blocks: {dead_code_count}
- Estimated dead lines: {dead_lines}

Top issues:
{top_issues}

Write a brief (3-5 sentences) executive summary for a non-technical audience.
Focus on business impact and recommended next steps."""

DEPENDENCY_EXPLANATION_PROMPT = """Explain the following feature flag dependency chain:

{dependency_chain}

In 2-3 sentences, explain:
1. What this dependency means
2. Potential risks of this setup"""
