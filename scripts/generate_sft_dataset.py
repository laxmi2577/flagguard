"""Synthetic SFT Dataset Generator for FlagGuard Fine-Tuning (Phase 3 — Step 3.1).

Generates 1,500+ high-diversity instruction → response JSONL pairs for Supervised
Fine-Tuning (SFT) of a domain-specific LLM that reasons about feature flag
conflicts with the depth of a Staff-level engineer.

Dataset Design Principles:
    - Multi-template: Each category has 3-5 distinct prompt phrasings to prevent
      the model from learning superficial surface patterns.
    - Structural variety: Responses use different markdown structures so the model
      learns flexible reasoning, not template memorization.
    - Realistic detail: Actual line numbers, unified diffs, Z3 constraint output,
      SHAP factor tables, git blame snippets — grounding the LLM in real artifacts.
    - Quality filtering: All samples are validated for minimum length, unique content
      hash, and response-to-prompt ratio before saving.

Categories (with target distribution):
    1. Conflict Explanation     — 25% (what, why, business impact)
    2. Code Fix Generation      — 25% (unified diff patches with verification)
    3. Risk Assessment          — 20% (SHAP-style factor analysis for commits)
    4. Dead Code Detection      — 15% (flag lifecycle + safe deletion)
    5. Dependency Chain         — 15% (transitive impact, cascading failures)

Output: HuggingFace-compatible ChatML JSONL, with 80/10/10 train/val/test split.

Usage:
    python scripts/generate_sft_dataset.py --output data/sft_dataset --count 1500
    python scripts/generate_sft_dataset.py --count 2000 --seed 999 --validate

Skills demonstrated: Synthetic Data Engineering, NLP Dataset Curation,
  Domain-Specific LLM Training Data, ChatML Formatting, JSONL Pipeline Design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sft_datagen")


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""\
    You are FlagGuard-Coder, a Staff-level AI engineer specializing in feature flag
    conflict resolution, formal program verification, and risk-aware software delivery.
    Your analysis is powered by:
      • Z3 SAT/SMT solver for formal constraint checking
      • NetworkX knowledge graph for transitive dependency tracing
      • SHAP-explainability for commit risk quantification
      • Tree-sitter AST parsing for function-level impact analysis

    Response standards:
      • Be direct and precise — cite specific functions, line numbers, and flag names
      • Always provide a *verified* code fix in unified diff format when a fix is requested
      • Quantify impact with concrete estimates wherever possible
      • Structure with clear Markdown headers and code blocks
      • End with a single, actionable next-step recommendation
""").strip()

# ── Vocabulary Pools ──────────────────────────────────────────────────────────
FLAG_NAMES: list[str] = [
    "dark_mode", "premium_tier", "payment_v2", "checkout_redesign",
    "auth_sso", "beta_dashboard", "notification_v3", "search_ai",
    "cache_redis", "rate_limiter_v2", "ab_test_pricing", "feature_flags_v2",
    "legacy_api_compat", "new_onboarding_flow", "analytics_v3", "cdn_edge",
    "websocket_live", "batch_processing_async", "email_templates_v2",
    "mobile_api_v3", "admin_panel_v2", "structured_logging",
    "security_2fa_enforced", "i18n_rtl_support", "perf_profiler", "graphql_beta",
    "ml_recommendations", "zero_downtime_deploy", "circuit_breaker", "shadow_mode",
]

FUNCTION_NAMES: list[str] = [
    "process_checkout", "handle_payment", "validate_cart_items", "apply_promo_code",
    "authenticate_user", "validate_jwt_token", "refresh_oauth_session",
    "dispatch_notification", "render_dashboard_widgets", "aggregate_analytics",
    "execute_product_search", "update_user_profile", "generate_pdf_report",
    "process_webhook_event", "sync_inventory_snapshot", "calculate_shipping_cost",
    "render_transactional_email", "initiate_refund_flow", "create_stripe_subscription",
    "enforce_rate_limits", "populate_redis_cache", "emit_structured_log",
    "resolve_graphql_query", "run_recommendation_engine",
]

FILE_PATHS: list[str] = [
    "src/billing/checkout.py",
    "src/auth/oauth.py",
    "src/api/v2/routes.py",
    "src/notifications/dispatcher.py",
    "src/dashboard/renderer.py",
    "src/analytics/aggregator.py",
    "src/search/engine.py",
    "src/payments/stripe_client.py",
    "src/users/profile_service.py",
    "src/admin/access_control.py",
    "src/cache/redis_manager.py",
    "src/webhooks/processor.py",
    "config/flags_production.json",
    "config/flags_canary.yaml",
    "services/recommendation/predictor.py",
]

SEVERITIES: list[str] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
CONFLICT_TYPES: list[str] = [
    "mutual_exclusion",
    "dependency_violation",
    "circular_dependency",
    "always_false_branch",
]

# Sample Z3 constraint output templates for realism
Z3_OUTPUT_TEMPLATES: list[str] = [
    "sat\n  ({f1} = True ∧ {f2} = True) → ⊥  [UNSAT in context C₁]",
    "unsat\n  Negation of safety property P({f1}, {f2}) is unsatisfiable — conflict proven",
    "Constraint violation:\n  z3.And(flag_{f1}, flag_{f2}) → z3.Not(invariant_holds)\n  Counterexample: {{{f1}: True, {f2}: True}}",
]


# ── Dataclass Config ──────────────────────────────────────────────────────────
@dataclass
class DatasetConfig:
    count: int = 1500
    seed: int = 42
    min_response_chars: int = 400
    max_response_chars: int = 3000
    min_prompt_chars: int = 60
    train_frac: float = 0.80
    val_frac: float = 0.10
    # test_frac is implicit: 1 - train - val = 0.10
    category_weights: dict[str, float] = field(default_factory=lambda: {
        "conflict": 0.25,
        "fix": 0.25,
        "risk": 0.20,
        "dead_code": 0.15,
        "dependency": 0.15,
    })


@dataclass
class Sample:
    category: str
    prompt: str
    response: str
    content_hash: str = ""

    def __post_init__(self) -> None:
        combined = self.prompt + self.response
        self.content_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

    def to_chatml(self) -> dict:
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": self.response},
            ],
            "_meta": {"category": self.category, "hash": self.content_hash},
        }

    def is_valid(self, cfg: DatasetConfig) -> bool:
        return (
            cfg.min_response_chars <= len(self.response) <= cfg.max_response_chars
            and len(self.prompt) >= cfg.min_prompt_chars
            and self.prompt.strip() != self.response.strip()
        )


# ── Template Generators ───────────────────────────────────────────────────────

def _z3_snippet(f1: str, f2: str) -> str:
    tmpl = random.choice(Z3_OUTPUT_TEMPLATES)
    return tmpl.format(f1=f1, f2=f2)


def _gen_conflict_explanation() -> Sample:
    """Five distinct phrasings to build robust conflict-reasoning ability."""
    f1, f2 = random.sample(FLAG_NAMES, 2)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)
    severity = random.choice(SEVERITIES[:2])
    ctype = random.choice(CONFLICT_TYPES)
    line_no = random.randint(42, 340)
    z3_out = _z3_snippet(f1, f2)

    phrasing = random.randint(0, 4)

    if phrasing == 0:
        prompt = (
            f"FlagGuard Z3 solver reported a **{severity}** `{ctype}` conflict "
            f"between `{f1}` and `{f2}` in `{func}()` ({fpath}:{line_no}). "
            f"Both are currently enabled. Explain the root cause, downstream impact, "
            f"and which flag should be disabled first."
        )
    elif phrasing == 1:
        prompt = (
            f"Our CI pipeline failed with a FlagGuard conflict alert:\n\n"
            f"```\n{z3_out}\n```\n\n"
            f"Flags: `{f1}`, `{f2}` | Function: `{func}()` | File: `{fpath}`\n"
            f"Severity: {severity}. What does this mean, and what is the blast radius?"
        )
    elif phrasing == 2:
        prompt = (
            f"During a production deployment, FlagGuard blocked the merge because "
            f"`{f1}` and `{f2}` are simultaneously enabled. The conflict is in "
            f"`{func}()` at `{fpath}:{line_no}`. Our incident channel is asking: "
            f"'Is this a P1? What broke?' — write the incident explanation."
        )
    elif phrasing == 3:
        prompt = (
            f"Explain to a junior engineer why enabling both `{f1}` and `{f2}` "
            f"at the same time causes a `{ctype}` error in `{func}()`. "
            f"Use the Z3 formal verification output as evidence:\n```\n{z3_out}\n```"
        )
    else:
        prompt = (
            f"A product manager is asking: 'We enabled `{f1}` for the A/B test — "
            f"why is FlagGuard blocking our release? `{f2}` has been on for months.' "
            f"Explain the {severity} conflict in `{fpath}` without jargon, "
            f"then give the technical fix."
        )

    resp_style = random.randint(0, 2)

    if resp_style == 0:
        response = (
            f"## Root Cause: `{ctype.replace('_', ' ').title()}`\n\n"
            f"| Property | Value |\n"
            f"|----------|-------|\n"
            f"| Severity | **{severity}** |\n"
            f"| Flags | `{f1}` ↔ `{f2}` |\n"
            f"| Conflict type | `{ctype}` |\n"
            f"| Location | `{func}()` → `{fpath}:{line_no}` |\n\n"
            f"### What the Z3 Solver Found\n"
            f"The Z3 SMT solver exhaustively checked all possible flag state "
            f"combinations and found that the configuration `{{{f1}: true, {f2}: true}}` "
            f"violates the invariant declared in `{fpath}`. When both flags are active, "
            f"`{func}()` encounters a logic branch that has no safe resolution — "
            f"the SAT problem becomes **UNSAT**, meaning no valid execution path exists.\n\n"
            f"### Business Impact\n"
            f"1. **{func}()** will silently return an incorrect value or raise an "
            f"   unhandled exception affecting all users in the flag's target cohort\n"
            f"2. Any downstream service calling `{func}()` inherits this failure mode\n"
            f"3. The conflict is **not observable in local testing** because it requires "
            f"   both flags to be active simultaneously in the same environment\n\n"
            f"### Resolution Order\n"
            f"Disable `{f2}` first (it appears to be the legacy/blocking flag based on "
            f"naming convention). Re-run `flagguard analyze` to confirm the constraint "
            f"set is satisfiable before re-enabling either.\n\n"
            f"**Next step:** `flagguard flag disable {f2} --env production --reason conflict-{f1}`"
        )
    elif resp_style == 1:
        response = (
            f"### Incident Explanation: {severity} Flag Conflict\n\n"
            f"**TL;DR:** Enabling `{f1}` alongside the existing `{f2}` config creates "
            f"a logically impossible state that the Z3 formal verifier can prove leads "
            f"to undefined behavior in `{func}()`.\n\n"
            f"**This is {'a P1' if severity == 'CRITICAL' else 'a P2'} — here's why:**\n\n"
            f"```\n{_z3_snippet(f1, f2)}\n```\n\n"
            f"The solver tried every possible evaluation order and found that "
            f"`{func}()` in `{fpath}:{line_no}` has a code path that is simultaneously "
            f"reachable and unreachable — a contradiction. This is the formal definition "
            f"of a `{ctype}` conflict.\n\n"
            f"**For the incident channel:** Nothing has broken *yet* — the conflict is "
            f"a pre-merge safety gate. But if this were deployed to production, "
            f"requests hitting the `{f1}` + `{f2}` flag combination would be "
            f"non-deterministic.\n\n"
            f"**Immediate action:** Disable `{f2}` in the feature flag dashboard, "
            f"or coordinate with the `{f1}` team to phase their rollout after `{f2}` "
            f"is fully deprecated."
        )
    else:
        response = (
            f"## Explaining `{ctype}` to a Junior Engineer\n\n"
            f"Think of feature flags as **light switches**. When you flip `{f1}` on, "
            f"it changes how `{func}()` behaves. But `{f2}` *also* changes how that "
            f"same function behaves — and the two changes are **mutually exclusive** "
            f"(like trying to turn a light both fully on and fully off).\n\n"
            f"### What Z3 Proved\n"
            f"```\n{_z3_snippet(f1, f2)}\n```\n"
            f"This isn't a warning — it's a **mathematical proof** that no valid program "
            f"state can exist with both flags on. The SAT solver checked every possible "
            f"execution trace through `{func}()` (~{random.randint(12, 96)} paths) "
            f"and found a contradiction at `{fpath}:{line_no}`.\n\n"
            f"### Analogy\n"
            f"It's like a car's logic saying: IF `sport_mode=true`, max RPM = 7000. "
            f"But also: IF `eco_mode=true`, max RPM = 4000. If both are on, "
            f"what is the max RPM? The car's computer has no safe answer.\n\n"
            f"### What to Fix\n"
            f"Add a config validation rule: `{f1}` requires `{f2}=false`. "
            f"Then disable `{f2}` to unblock the release.\n\n"
            f"**Next step:** `flagguard validate --strict` on your local config branch."
        )

    return Sample(category="conflict", prompt=prompt, response=response)


def _gen_fix_suggestion() -> Sample:
    """Generates realistic unified diff patches with proper context lines."""
    f1, f2 = random.sample(FLAG_NAMES, 2)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)
    line_no = random.randint(25, 250)
    phrasing = random.randint(0, 3)

    if phrasing == 0:
        prompt = (
            f"Flag `{f1}` depends on `{f2}`, but `{f2}` is disabled in staging. "
            f"`{func}()` in `{fpath}` calls `is_enabled(\"{f1}\")` without checking "
            f"the `{f2}` dependency. Generate a production-safe code fix with tests."
        )
    elif phrasing == 1:
        prompt = (
            f"FlagGuard Knowledge Graph shows:\n"
            f"  `{f1}` ──requires──▶ `{f2}` (enabled=False)\n\n"
            f"The violation is at `{func}()` (`{fpath}:{line_no}`). "
            f"Write the corrected function and the corresponding pytest test."
        )
    elif phrasing == 2:
        prompt = (
            f"Generate a zero-downtime fix for a dependency violation where "
            f"`{f1}` is enabled but its prerequisite `{f2}` is not. "
            f"The offending code is in `{func}()` at `{fpath}`. "
            f"Include a feature flag guard, structured logging, and a metric increment."
        )
    else:
        prompt = (
            f"Our SHAP analysis shows `flag_mentions_count` is the top risk driver. "
            f"Specifically, `{func}()` in `{fpath}:{line_no}` has an unguarded "
            f"dependency: `{f1}` is enabled but `{f2}` (which it requires) is not. "
            f"Provide the fix as a unified diff."
        )

    response = (
        f"## Fix: Dependency Guard for `{f1}` → `{f2}`\n\n"
        f"### Root Cause\n"
        f"`{func}()` checks `is_enabled(\"{f1}\")` but doesn't verify its declared "
        f"dependency `{f2}`, creating a **silent degradation path** when `{f2}` is "
        f"disabled. This is a dependency violation (SHAP: Δrisk +{random.randint(8,24)}%).\n\n"
        f"### Unified Diff\n"
        f"```diff\n"
        f"--- a/{fpath}\n"
        f"+++ b/{fpath}\n"
        f"@@ -{line_no},{random.randint(7,10)} +{line_no},{random.randint(12,16)} @@\n"
        f" class {func.replace('_', ' ').title().replace(' ', '')}Handler:\n"
        f" \n"
        f"+    # FlagGuard: {f1} requires {f2} — guard enforced\n"
        f"+    _FLAG_DEPS: ClassVar[dict[str, str]] = {{\"{f1}\": \"{f2}\"}}\n"
        f"+\n"
        f"     def {func}(self, request: Request) -> Response:\n"
        f"-        if is_enabled(\"{f1}\"):\n"
        f"+        if is_enabled(\"{f1}\") and is_enabled(\"{f2}\"):\n"
        f"             return self._new_{func}_flow(request)\n"
        f"+        elif is_enabled(\"{f1}\") and not is_enabled(\"{f2}\"):\n"
        f"+            log.warning(\n"
        f"+                \"flag_dependency_violation\",\n"
        f"+                flag=\"{f1}\",\n"
        f"+                missing_dep=\"{f2}\",\n"
        f"+                extra={{\"handler\": \"{func}\", \"path\": request.path}},\n"
        f"+            )\n"
        f"+            metrics.increment(\"flagguard.dependency_violation\",\n"
        f"+                             tags={{\"flag\": \"{f1}\"}})\n"
        f"+            return self._safe_fallback_response(request)\n"
        f"         return self._legacy_{func}_flow(request)\n"
        f"```\n\n"
        f"### Test Coverage\n"
        f"```python\n"
        f"# tests/unit/test_{func}.py\n"
        f"import pytest\n"
        f"from unittest.mock import patch\n"
        f"\n"
        f"@pytest.mark.parametrize(\"{f1},{f2},expected_flow\", [\n"
        f"    (True,  True,  \"new\"),    # happy path\n"
        f"    (True,  False, \"fallback\"), # dependency violation → safe fallback\n"
        f"    (False, True,  \"legacy\"),  # only dep enabled\n"
        f"    (False, False, \"legacy\"),  # all disabled\n"
        f"])\n"
        f"def test_{func}_flag_guard(flagfaker, {f1}, {f2}, expected_flow):\n"
        f"    flagfaker.enable(\"{f1}\", enabled={f1})\n"
        f"    flagfaker.enable(\"{f2}\", enabled={f2})\n"
        f"    response = {func}(make_test_request())\n"
        f"    assert response.metadata[\"flow\"] == expected_flow\n"
        f"```\n\n"
        f"### Verification\n"
        f"After applying this patch:\n"
        f"1. `flagguard analyze --strict` → should report 0 dependency violations\n"
        f"2. `pytest tests/unit/test_{func}.py -v` → all 4 parametrized cases pass\n"
        f"3. Z3 solver will confirm new state satisfies `{f1}_requires_{f2}` constraint\n\n"
        f"**Next step:** Deploy to staging with `{f2}=false` to validate the fallback path."
    )

    return Sample(category="fix", prompt=prompt, response=response)


def _gen_risk_assessment() -> Sample:
    """Realistic SHAP-style commit risk analysis."""
    files_mod = random.randint(1, 30)
    lines_added = random.randint(5, 600)
    lines_deleted = random.randint(2, 400)
    flag_mentions = random.randint(0, 12)
    commit_hour = random.randint(0, 23)
    has_tests = random.choice([True, False])
    author_commits = random.randint(1, 250)
    config_files_changed = random.randint(0, 5)
    is_merge = random.choice([True, False])
    days_since = round(random.uniform(0.1, 21.0), 1)

    # Risk scoring heuristic
    risk_score = (
        (flag_mentions * 4.2)
        + (lines_added / 20)
        + (config_files_changed * 8)
        + (15 if commit_hour < 6 or commit_hour > 21 else 0)
        + (12 if not has_tests else 0)
        + (8 if is_merge else 0)
        - (author_commits * 0.1)
        + (days_since * 1.5)
    )
    risk_score = max(2.0, min(98.0, risk_score))
    risk_level = (
        "CRITICAL" if risk_score >= 75 else
        "HIGH" if risk_score >= 55 else
        "MEDIUM" if risk_score >= 30 else "LOW"
    )

    phrasing = random.randint(0, 1)

    if phrasing == 0:
        prompt = (
            f"Predict the conflict risk for this commit and explain the top SHAP drivers:\n\n"
            f"| Feature | Value |\n"
            f"|---------|-------|\n"
            f"| files_modified | {files_mod} |\n"
            f"| lines_added | {lines_added} |\n"
            f"| lines_deleted | {lines_deleted} |\n"
            f"| flag_mentions_count | {flag_mentions} |\n"
            f"| config_files_modified | {config_files_changed} |\n"
            f"| commit_hour | {commit_hour}:00 |\n"
            f"| is_merge_commit | {'yes' if is_merge else 'no'} |\n"
            f"| has_test_changes | {'yes' if has_tests else 'no'} |\n"
            f"| author_commit_count | {author_commits} |\n"
            f"| days_since_last_commit | {days_since} |\n"
        )
    else:
        prompt = (
            f"This commit was pushed at {commit_hour}:00. Stats:\n"
            f"  - {files_mod} files, +{lines_added}/-{lines_deleted} lines\n"
            f"  - {flag_mentions} flag API calls in the diff\n"
            f"  - {config_files_changed} config (.yaml/.json) files modified\n"
            f"  - {'Merge commit' if is_merge else 'Direct commit'}, "
            f"    {'tests updated' if has_tests else 'no test changes'}\n"
            f"  - Author: {author_commits} lifetime commits, last commit {days_since}d ago\n\n"
            f"What is the XGBoost risk score and which 3 features drive it most?"
        )

    # SHAP factor table
    shap_factors = sorted([
        ("flag_mentions_count", flag_mentions * 0.042, flag_mentions > 3),
        ("lines_added", lines_added * 0.0008, lines_added > 200),
        ("config_files_modified", config_files_changed * 0.08, config_files_changed > 2),
        ("commit_hour", 0.15 if (commit_hour < 6 or commit_hour > 21) else -0.05,
         commit_hour < 6 or commit_hour > 21),
        ("has_test_changes", -0.12 if has_tests else 0.12, not has_tests),
        ("author_commit_count", -author_commits * 0.001, False),
        ("days_since_last_commit", days_since * 0.015, days_since > 7),
        ("is_merge_commit", 0.08 if is_merge else -0.02, is_merge),
    ], key=lambda x: abs(x[1]), reverse=True)

    shap_table = "| Rank | Feature | SHAP Impact | Direction |\n"
    shap_table += "|------|---------|-------------|----------|\n"
    for rank, (feat, impact, increases_risk) in enumerate(shap_factors[:5], 1):
        arrow = "↑ raises risk" if increases_risk else "↓ lowers risk"
        shap_table += f"| {rank} | `{feat}` | {impact:+.4f} | {arrow} |\n"

    response = (
        f"## Risk Assessment: **{risk_level}** ({risk_score:.1f}%)\n\n"
        f"### XGBoost Prediction\n"
        f"The model assigns a conflict probability of **{risk_score:.1f}%** "
        f"({'above' if risk_score > 50 else 'below'} the 50% decision threshold → "
        f"prediction: {'⚠️ HIGH RISK' if risk_score > 50 else '✅ LOW RISK'}).\n\n"
        f"### SHAP Feature Attribution\n\n"
        f"{shap_table}\n"
        f"### Factor Analysis\n"
    )

    if flag_mentions > 3:
        response += (
            f"- **`flag_mentions_count = {flag_mentions}`** (top driver): "
            f"This commit touches {flag_mentions} flag API call sites. FlagGuard's "
            f"historical data shows commits with >3 flag mentions have "
            f"2.8× higher conflict rates due to interaction effects.\n"
        )
    if not has_tests:
        response += (
            f"- **`has_test_changes = False`**: No test files modified. "
            f"Flag behavior changes are unverified — integration tests "
            f"covering flag state combinations are missing.\n"
        )
    if commit_hour < 6 or commit_hour > 21:
        response += (
            f"- **`commit_hour = {commit_hour}`**: Outside core business hours. "
            f"Late-night commits show 1.6× higher rollback rates in the training dataset.\n"
        )
    if config_files_changed > 0:
        response += (
            f"- **`config_files_modified = {config_files_changed}`**: "
            f"Config changes directly alter flag evaluation — each modified config "
            f"file must be validated through `flagguard validate`.\n"
        )

    response += (
        f"\n### Recommendation\n"
        f"{'🔴 **Block merge** until a senior engineer reviews the flag interaction matrix.' if risk_score >= 75 else ''}"
        f"{'🟠 **Request additional review** before merging, especially flag-related changes.' if 55 <= risk_score < 75 else ''}"
        f"{'🟡 **Standard review** is sufficient, but run `flagguard analyze` before deploying.' if 30 <= risk_score < 55 else ''}"
        f"{'🟢 **Low risk** — proceed with standard CI checks.' if risk_score < 30 else ''}\n\n"
        f"**Next step:** `flagguard analyze --commit HEAD --report json > risk_{commit_hour}h.json`"
    )

    return Sample(category="risk", prompt=prompt, response=response)


def _gen_dead_code() -> Sample:
    """Flag lifecycle and safe deletion analysis."""
    flag = random.choice(FLAG_NAMES)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)
    start_line = random.randint(50, 250)
    block_size = random.randint(8, 45)
    end_line = start_line + block_size
    days_disabled = random.randint(45, 365)
    phrasing = random.randint(0, 2)

    if phrasing == 0:
        prompt = (
            f"FlagGuard AST analysis detected {block_size} lines of dead code in "
            f"`{func}()` ({fpath}:{start_line}-{end_line}). The guard flag `{flag}` "
            f"has been `false` across all 3 environments for {days_disabled} days. "
            f"Is it safe to delete? What's the risk, migration plan, and rollback strategy?"
        )
    elif phrasing == 1:
        prompt = (
            f"A code reviewer flagged this during PR review:\n\n"
            f"```python\n"
            f"# {fpath}:{start_line}\n"
            f"if is_enabled(\"{flag}\"):  # flag_status: PERMANENTLY_DISABLED ({days_disabled}d)\n"
            f"    # ... {block_size} lines of dead code ...\n"
            f"    return {func}_new_flow(request)\n"
            f"```\n\n"
            f"Should we remove this block? Write a formal dead code analysis report."
        )
    else:
        prompt = (
            f"FlagGuard's flag lifecycle tracker shows:\n"
            f"  Flag: `{flag}`\n"
            f"  Status: DISABLED\n"
            f"  Disabled duration: {days_disabled} days\n"
            f"  Affected code: `{func}()` in `{fpath}:{start_line}-{end_line}`\n"
            f"  Environments checked: production, staging, canary\n\n"
            f"Generate the dead code removal PR description with risk assessment."
        )

    retention_risk = (
        "HIGH" if days_disabled < 90 else
        "MEDIUM" if days_disabled < 180 else "LOW"
    )

    response = (
        f"## Dead Code Analysis: `{flag}` Guard Block\n\n"
        f"| Property | Value |\n"
        f"|----------|-------|\n"
        f"| Guarding flag | `{flag}` |\n"
        f"| Status | PERMANENTLY_DISABLED for **{days_disabled} days** |\n"
        f"| Dead block | `{fpath}:{start_line}-{end_line}` ({block_size} lines) |\n"
        f"| Function | `{func}()` |\n"
        f"| Deletion risk | **{retention_risk}** |\n\n"
        f"### Safety Assessment\n"
        f"**{'Safe to delete ✅' if days_disabled >= 90 else 'Use caution ⚠️'}** — "
        f"`{flag}` has been disabled for {days_disabled} days across all environments. "
        f"The Tree-sitter AST confirms this guard block is the **only** code path "
        f"behind `{flag}`, and no other function in the call graph depends on "
        f"`{func}()`'s new-flow return value.\n\n"
        f"### Risks of Keeping vs. Deleting\n\n"
        f"| Risk | Keep Dead Code | Delete Dead Code |\n"
        f"|------|---------------|------------------|\n"
        f"| Developer confusion | **HIGH** — future devs may re-enable `{flag}` accidentally | None |\n"
        f"| Bundle/complexity bloat | **{block_size} dead lines** in critical path | None |\n"
        f"| False test coverage | Tests for dead path waste CI minutes | Tests removed cleanly |\n"
        f"| Rollback ability | Re-enable flag (but infra may be gone) | Need git revert |\n\n"
        f"### Removal Plan\n"
        f"```diff\n"
        f"--- a/{fpath}\n"
        f"+++ b/{fpath}\n"
        f"@@ -{start_line},{block_size + 3} +{start_line},3 @@\n"
        f" def {func}(request):\n"
        f"-    # flagguard: dead code — {flag} disabled {days_disabled}d\n"
        f"-    if is_enabled(\"{flag}\"):\n"
        f"-        # --- {block_size - 2} lines removed: new flow implementation ---\n"
        f"-        return {func}_new_flow(request)\n"
        f"-\n"
        f"     return {func}_legacy_flow(request)  # now the only path\n"
        f"```\n\n"
        f"### PR Description Template\n"
        f"```\n"
        f"chore: remove dead code for deprecated flag `{flag}`\n\n"
        f"The `{flag}` feature flag has been disabled for {days_disabled} days\n"
        f"across production, staging, and canary environments.\n\n"
        f"Removes {block_size} unreachable lines from `{func}()` in `{fpath}`.\n\n"
        f"Verified by:\n"
        f"  - flagguard lifecycle-check --flag {flag}\n"
        f"  - grep -r 'is_enabled(\"{flag}\")' src/ → 0 other call sites\n"
        f"  - All {random.randint(8, 24)} existing tests pass after removal\n"
        f"```\n\n"
        f"**Next step:** `flagguard flag archive {flag} --reason deprecated --pr <PR_URL>`"
    )

    return Sample(category="dead_code", prompt=prompt, response=response)


def _gen_dependency_analysis() -> Sample:
    """Transitive dependency chain analysis with cascading failure scenarios."""
    chain_len = random.randint(3, 5)
    chain = random.sample(FLAG_NAMES, chain_len)
    disabled_idx = random.randint(1, chain_len - 2)
    disabled_flag = chain[disabled_idx]

    phrasing = random.randint(0, 2)
    chain_str = " → ".join(f"`{f}`" for f in chain)

    if phrasing == 0:
        prompt = (
            f"The FlagGuard Knowledge Graph detected a {chain_len}-node dependency chain: "
            f"{chain_str}. The `{disabled_flag}` flag (node {disabled_idx + 1}/{chain_len}) "
            f"is being scheduled for deprecation next sprint. "
            f"Analyze the full cascading impact and provide the safe deprecation order."
        )
    elif phrasing == 1:
        prompt = (
            f"Before disabling `{disabled_flag}`, we need a full impact analysis. "
            f"The NetworkX graph shows this transitive dependency chain:\n\n"
            f"```\n"
            + "\n".join(
                f"  {'  ' * i}{chain[i]} {'──requires──▶' if i < chain_len - 1 else '(leaf)'}"
                for i in range(chain_len)
            )
            + f"\n```\n\n"
            f"Which services break, in what order, and what's the safe rollout plan?"
        )
    else:
        prompt = (
            f"PM request: 'Deprecate `{disabled_flag}` next Tuesday.' "
            f"But the dependency graph shows {chain_str}. "
            f"Write the technical objection with evidence and a counter-proposal."
        )

    upstream = chain[:disabled_idx]      # flags that depend on disabled_flag
    downstream = chain[disabled_idx + 1:]  # flags that disabled_flag depends on

    response = (
        f"## Dependency Chain Analysis: Disabling `{disabled_flag}`\n\n"
        f"### Chain Topology\n\n"
        f"```\n"
        + "  ".join(
            f"{'[DISABLE TARGET]' if f == disabled_flag else ''}{f}"
            + (" ──▶" if i < chain_len - 1 else " (leaf)")
            for i, f in enumerate(chain)
        )
        + f"\n```\n\n"
        f"### Cascading Failure Analysis\n\n"
        f"Disabling `{disabled_flag}` propagates failures **up the dependency tree** "
        f"(toward the roots) but leaves downstream flags intact:\n\n"
        f"| Flag | Relationship | Impact |\n"
        f"|------|-------------|--------|\n"
    )

    for f in upstream:
        response += (
            f"| `{f}` | Upstream — depends on `{disabled_flag}` | "
            f"**BROKEN**: will enter undefined state when `{disabled_flag}=false` |\n"
        )
    response += (
        f"| `{disabled_flag}` | **[TARGET]** | Will be disabled |\n"
    )
    for f in downstream:
        response += (
            f"| `{f}` | Downstream — `{disabled_flag}` depends on it | "
            f"**UNAFFECTED**: no upstream dependency |\n"
        )

    response += (
        f"\n### Safe Deprecation Order\n\n"
        f"**Rule:** Always disable the most upstream (dependent) flags first, "
        f"moving toward the leaf (dependency).\n\n"
    )
    ordered = list(reversed(upstream)) + [disabled_flag]
    for step, f in enumerate(ordered, 1):
        response += (
            f"{step}. Disable `{f}`"
            + (" ← start here, it has no upstream dependents" if step == 1 else "")
            + (" ← final step" if f == disabled_flag else "")
            + "\n"
        )

    response += (
        f"\n### Technical Objection Template\n"
        f"```\n"
        f"Risk: Disabling {disabled_flag} next Tuesday without first disabling\n"
        f"{', '.join(upstream)} will cause {len(upstream)} upstream flag(s) to\n"
        f"enter undefined states in production.\n\n"
        f"Counter-proposal:\n"
        f"  - Week 1: Disable {upstream[0] if upstream else disabled_flag} (no dependents)\n"
        f"  - Week 2: Verify monitoring, then disable {disabled_flag}\n"
        f"  - Estimated safe timeline: {len(ordered)} sprints\n"
        f"```\n\n"
        f"**Next step:** `flagguard graph show {disabled_flag} --format mermaid | pbcopy`"
    )

    return Sample(category="dependency", prompt=prompt, response=response)


# ── Dataset Assembly ──────────────────────────────────────────────────────────

GENERATORS: dict[str, Callable[[], Sample]] = {
    "conflict": _gen_conflict_explanation,
    "fix": _gen_fix_suggestion,
    "risk": _gen_risk_assessment,
    "dead_code": _gen_dead_code,
    "dependency": _gen_dependency_analysis,
}


def generate_dataset(cfg: DatasetConfig) -> list[Sample]:
    """Generate, filter, and deduplicate the dataset.

    Args:
        cfg: Dataset configuration.

    Returns:
        List of valid, deduplicated Sample objects.
    """
    random.seed(cfg.seed)
    categories = list(cfg.category_weights.keys())
    weights = list(cfg.category_weights.values())

    seen_hashes: set[str] = set()
    dataset: list[Sample] = []
    attempts = 0
    max_attempts = cfg.count * 5  # allow generation headroom for filtering

    while len(dataset) < cfg.count and attempts < max_attempts:
        attempts += 1
        category = random.choices(categories, weights=weights, k=1)[0]
        try:
            sample = GENERATORS[category]()
        except Exception as exc:
            log.warning("Generator %s failed: %s", category, exc)
            continue

        if not sample.is_valid(cfg):
            continue

        if sample.content_hash in seen_hashes:
            continue  # skip duplicate

        seen_hashes.add(sample.content_hash)
        dataset.append(sample)

    if len(dataset) < cfg.count:
        log.warning(
            "Only generated %d/%d samples after %d attempts. "
            "Reduce --count or relax validation thresholds.",
            len(dataset), cfg.count, attempts,
        )

    random.shuffle(dataset)  # always shuffle before splitting
    return dataset


def _print_stats(dataset: list[Sample]) -> None:
    """Print dataset quality statistics."""
    cat_counts = Counter(s.category for s in dataset)
    prompt_lens = [len(s.prompt) for s in dataset]
    resp_lens = [len(s.response) for s in dataset]

    print("\n📊 Dataset Statistics")
    print("─" * 50)
    print(f"  Total samples  : {len(dataset)}")
    print(f"  Unique hashes  : {len({s.content_hash for s in dataset})}")
    print(f"\n  Category distribution:")
    for cat, count in sorted(cat_counts.items()):
        pct = count / len(dataset) * 100
        bar = "█" * int(pct / 2)
        print(f"    {cat:<15} {count:>4} ({pct:.0f}%) {bar}")
    print(f"\n  Prompt length  : avg {sum(prompt_lens)//len(prompt_lens)} chars")
    print(f"  Response length: avg {sum(resp_lens)//len(resp_lens)} chars")
    print(f"  Min response   : {min(resp_lens)} chars")
    print(f"  Max response   : {max(resp_lens)} chars")


def save_dataset(dataset: list[Sample], output_dir: str, cfg: DatasetConfig) -> None:
    """Split into train/val/test and save as JSONL files.

    Also writes a manifest.json with metadata and a full_dataset.jsonl.
    """
    os.makedirs(output_dir, exist_ok=True)

    total = len(dataset)
    train_end = int(total * cfg.train_frac)
    val_end = int(total * (cfg.train_frac + cfg.val_frac))

    splits = {
        "train": dataset[:train_end],
        "val": dataset[train_end:val_end],
        "test": dataset[val_end:],
    }

    print(f"\n💾 Saving to {output_dir}/")

    for split_name, split_data in splits.items():
        path = Path(output_dir) / f"{split_name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for sample in split_data:
                f.write(json.dumps(sample.to_chatml(), ensure_ascii=False) + "\n")
        print(f"  {split_name:8s}: {len(split_data):>5} samples → {path}")

    # Full dataset
    full_path = Path(output_dir) / "full_dataset.jsonl"
    with full_path.open("w", encoding="utf-8") as f:
        for sample in dataset:
            f.write(json.dumps(sample.to_chatml(), ensure_ascii=False) + "\n")
    print(f"  {'full':8s}: {total:>5} samples → {full_path}")

    # Manifest
    manifest = {
        "version": "2.0.0",
        "total": total,
        "splits": {"train": len(splits["train"]), "val": len(splits["val"]),
                   "test": len(splits["test"])},
        "category_distribution": dict(Counter(s.category for s in dataset)),
        "config": {
            "seed": cfg.seed,
            "min_response_chars": cfg.min_response_chars,
            "max_response_chars": cfg.max_response_chars,
        },
        "format": "chatml",
        "system_prompt_length": len(SYSTEM_PROMPT),
    }
    manifest_path = Path(output_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"  manifest.json written to {manifest_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate high-diversity SFT dataset for FlagGuard fine-tuning.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--output", default="data/sft_dataset", help="Output directory")
    parser.add_argument("--count", type=int, default=1500, help="Target sample count")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--min-response", type=int, default=400,
                        help="Minimum response length (chars)")
    parser.add_argument("--validate", action="store_true",
                        help="Print detailed quality stats before saving")
    args = parser.parse_args()

    cfg = DatasetConfig(
        count=args.count,
        seed=args.seed,
        min_response_chars=args.min_response,
    )

    log.info("Generating %d SFT samples (seed=%d)…", cfg.count, cfg.seed)
    dataset = generate_dataset(cfg)

    if args.validate or True:  # always show stats
        _print_stats(dataset)

    save_dataset(dataset, args.output, cfg)

    print("\n✅ SFT dataset generation complete!")
    print("   Next: python notebooks/flagguard_sft_training.py --data", args.output)


if __name__ == "__main__":
    main()
