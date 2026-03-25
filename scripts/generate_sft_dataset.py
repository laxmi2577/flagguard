"""Synthetic SFT Dataset Generator for FlagGuard Fine-Tuning (Phase 3 — Step 3.1).

Generates 1,000+ instruction → response JSONL pairs for Supervised
Fine-Tuning (SFT) of a domain-specific LLM. The dataset teaches the
model to explain feature flag conflicts, suggest fixes, and analyze
risk like a senior engineer.

Categories:
    1. Conflict Explanation (explain what a flag conflict means)
    2. Fix Suggestion (suggest code/config changes to resolve conflicts)  
    3. Risk Assessment (analyze commit features for conflict risk)
    4. Dead Code Analysis (explain unreachable flag-guarded code)
    5. Dependency Analysis (explain flag dependency chains)

Output Format (ChatML-compatible JSONL):
    {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Usage:
    python scripts/generate_sft_dataset.py --output data/sft_dataset --count 1000

Skills demonstrated: Synthetic Data Generation, NLP Dataset Curation, ChatML Formatting.
"""

import argparse
import json
import os
import random
from pathlib import Path

# ── Constants ──

SYSTEM_PROMPT = (
    "You are FlagGuard-Coder, an expert AI assistant specializing in feature flag "
    "conflict resolution, code remediation, and risk assessment. You analyze code "
    "using formal verification (Z3 SAT solver), knowledge graphs, and SHAP-based "
    "risk prediction. Always be precise, cite specific functions/files, and provide "
    "actionable fixes in unified diff format when applicable."
)

FLAG_NAMES = [
    "dark_mode", "premium_tier", "payment_v2", "checkout_redesign",
    "auth_sso", "beta_dashboard", "notification_v3", "search_ai",
    "cache_redis", "rate_limiter", "ab_test_pricing", "feature_flags_v2",
    "legacy_api", "new_onboarding", "analytics_v2", "cdn_enabled",
    "websocket_live", "batch_processing", "email_templates_v2",
    "mobile_api_v3", "admin_panel_v2", "logging_structured",
    "security_2fa", "i18n_support", "performance_profiler",
]

FUNCTION_NAMES = [
    "checkout", "process_payment", "validate_cart", "apply_discount",
    "authenticate_user", "validate_token", "refresh_session",
    "send_notification", "render_dashboard", "fetch_analytics",
    "search_products", "update_profile", "generate_report",
    "handle_webhook", "sync_inventory", "calculate_shipping",
    "render_email", "process_refund", "create_subscription",
    "check_rate_limit", "cache_response", "log_event",
]

FILE_PATHS = [
    "src/billing/checkout.py", "src/auth/sso.py", "src/api/routes.py",
    "src/notifications/email.py", "src/dashboard/analytics.py",
    "src/search/engine.py", "src/payments/processor.py",
    "src/users/profile.py", "src/admin/panel.py", "src/cache/redis.py",
    "config/flags_prod.json", "config/flags_staging.yaml",
]

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# ── Template Generators ──

def _gen_conflict_explanation() -> dict:
    """Generate a conflict explanation instruction pair."""
    f1, f2 = random.sample(FLAG_NAMES, 2)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)
    severity = random.choice(SEVERITIES[:2])

    instruction = (
        f"The Z3 SAT solver detected a {severity} conflict between flags "
        f"`{f1}` and `{f2}`. The conflict occurs in `{func}()` at `{fpath}`. "
        f"Both flags are currently enabled but are mutually exclusive. "
        f"Explain this conflict and its business impact."
    )

    response = (
        f"## Conflict Analysis\n\n"
        f"**Severity:** {severity}\n"
        f"**Flags:** `{f1}` ↔ `{f2}` (mutual exclusion violation)\n"
        f"**Location:** `{func}()` in `{fpath}`\n\n"
        f"### What's Happening\n"
        f"The flags `{f1}` and `{f2}` are both enabled in the current configuration, "
        f"but they are declared as mutually exclusive. This means the system is in an "
        f"impossible state — `{func}()` contains a code path that checks both flags, "
        f"and the behavior is undefined when both are true.\n\n"
        f"### Business Impact\n"
        f"- Users may experience inconsistent behavior depending on which flag is evaluated first\n"
        f"- The `{func}()` function may produce incorrect results or throw runtime errors\n"
        f"- This state was likely not tested since it \"shouldn't\" be possible\n\n"
        f"### Recommended Fix\n"
        f"Disable one of the two flags. If `{f1}` is the newer feature, disable `{f2}` "
        f"(the legacy path). If both are needed, refactor `{func}()` to handle the "
        f"combined state explicitly."
    )

    return _format_chatml(instruction, response)


def _gen_fix_suggestion() -> dict:
    """Generate a fix suggestion instruction pair."""
    f1, f2 = random.sample(FLAG_NAMES, 2)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)

    instruction = (
        f"Flag `{f1}` depends on `{f2}`, but `{f2}` is currently disabled. "
        f"The function `{func}()` in `{fpath}` checks `{f1}` without verifying "
        f"its dependency. Generate a code fix."
    )

    response = (
        f"## Fix: Add Dependency Guard\n\n"
        f"The function `{func}()` checks `is_enabled(\"{f1}\")` but doesn't verify "
        f"that its dependency `{f2}` is also active. This creates a silent failure path.\n\n"
        f"### Suggested Fix\n"
        f"```diff\n"
        f"--- a/{fpath}\n"
        f"+++ b/{fpath}\n"
        f"@@ -42,7 +42,9 @@\n"
        f" def {func}(request):\n"
        f"-    if is_enabled(\"{f1}\"):\n"
        f"+    if is_enabled(\"{f1}\") and is_enabled(\"{f2}\"):\n"
        f"         return new_{func}_flow(request)\n"
        f"+    elif is_enabled(\"{f1}\") and not is_enabled(\"{f2}\"):\n"
        f"+        logger.warning(\"Dependency violation: {f1} requires {f2}\")\n"
        f"+        return fallback_{func}_flow(request)\n"
        f"     return legacy_{func}_flow(request)\n"
        f"```\n\n"
        f"### Verification\n"
        f"After applying this fix, run `flagguard analyze` to verify the Z3 solver "
        f"no longer reports a dependency violation for `{f1}` → `{f2}`."
    )

    return _format_chatml(instruction, response)


def _gen_risk_assessment() -> dict:
    """Generate a risk assessment instruction pair."""
    files = random.randint(1, 25)
    added = random.randint(5, 500)
    deleted = random.randint(2, 300)
    flags = random.randint(0, 8)
    hour = random.randint(0, 23)
    has_tests = random.choice([True, False])
    experience = random.randint(1, 200)

    is_risky = flags >= 3 and (hour < 6 or hour > 21) and not has_tests

    instruction = (
        f"Assess the conflict risk for this commit:\n"
        f"- Files modified: {files}\n"
        f"- Lines added: {added}, deleted: {deleted}\n"
        f"- Flag mentions in diff: {flags}\n"
        f"- Commit hour: {hour}:00\n"
        f"- Test changes included: {'yes' if has_tests else 'no'}\n"
        f"- Author total commits: {experience}"
    )

    if is_risky:
        score = random.randint(65, 95)
        level = "HIGH" if score < 80 else "CRITICAL"
        response = (
            f"## Risk Assessment: {level} ({score}%)\n\n"
            f"This commit has several risk indicators:\n"
            f"- **{flags} flag mentions** in the diff — high flag interaction density\n"
            f"- **Commit at {hour}:00** — outside business hours (fatigue risk)\n"
            f"- **No test changes** — flag behavior changes are untested\n"
            f"- Author has {experience} commits (experience: "
            f"{'junior' if experience < 20 else 'mid-level'})\n\n"
            f"### Recommendation\n"
            f"⚠️ Request additional code review before merging. Ensure flag interactions "
            f"are covered by integration tests. Run `flagguard analyze` to verify no "
            f"new conflicts are introduced."
        )
    else:
        score = random.randint(5, 35)
        response = (
            f"## Risk Assessment: LOW ({score}%)\n\n"
            f"This commit appears safe:\n"
            f"- Flag mentions: {flags} (minimal interaction)\n"
            f"- Commit during business hours ({hour}:00)\n"
            f"- {'Tests included' if has_tests else 'Standard change'}\n"
            f"- Author has {experience} commits (experienced contributor)\n\n"
            f"### Recommendation\n"
            f"✅ Standard review process is sufficient. No elevated risk detected."
        )

    return _format_chatml(instruction, response)


def _gen_dead_code() -> dict:
    """Generate a dead code analysis instruction pair."""
    flag = random.choice(FLAG_NAMES)
    func = random.choice(FUNCTION_NAMES)
    fpath = random.choice(FILE_PATHS)
    start = random.randint(50, 200)
    end = start + random.randint(5, 30)

    instruction = (
        f"FlagGuard detected dead code in `{fpath}` (lines {start}-{end}). "
        f"The code block inside `{func}()` requires flag `{flag}` to be enabled, "
        f"but `{flag}` has been permanently disabled for 90+ days. "
        f"Analyze this dead code block."
    )

    response = (
        f"## Dead Code Analysis\n\n"
        f"**File:** `{fpath}` (lines {start}-{end})\n"
        f"**Function:** `{func}()`\n"
        f"**Guarding Flag:** `{flag}` (disabled 90+ days)\n\n"
        f"### Why It's Dead\n"
        f"The code at lines {start}-{end} is guarded by `is_enabled(\"{flag}\")`, "
        f"but the flag `{flag}` has been permanently disabled across all environments "
        f"(dev, staging, prod) for over 90 days. This code can never execute.\n\n"
        f"### Risks of Keeping It\n"
        f"- **Maintenance burden:** New developers may try to understand or modify this code\n"
        f"- **Bundle bloat:** {end - start} lines of unreachable code\n"
        f"- **False sense of coverage:** Tests covering this path waste CI time\n\n"
        f"### Recommendation\n"
        f"Delete lines {start}-{end} and remove the `{flag}` flag from configuration. "
        f"If the feature is planned for re-release, archive it in a feature branch instead."
    )

    return _format_chatml(instruction, response)


def _gen_dependency_analysis() -> dict:
    """Generate a dependency chain explanation."""
    flags = random.sample(FLAG_NAMES, 3)

    instruction = (
        f"Explain the dependency chain: `{flags[0]}` → `{flags[1]}` → `{flags[2]}`. "
        f"What are the risks if `{flags[1]}` is disabled?"
    )

    response = (
        f"## Dependency Chain Analysis\n\n"
        f"```\n"
        f"{flags[0]} ──depends on──▶ {flags[1]} ──depends on──▶ {flags[2]}\n"
        f"```\n\n"
        f"### Chain Explanation\n"
        f"- `{flags[0]}` requires `{flags[1]}` to function correctly\n"
        f"- `{flags[1]}` in turn relies on `{flags[2]}` for its core behavior\n"
        f"- This creates a transitive dependency: `{flags[0]}` indirectly depends on `{flags[2]}`\n\n"
        f"### Impact of Disabling `{flags[1]}`\n"
        f"If `{flags[1]}` is disabled:\n"
        f"1. `{flags[0]}` will malfunction — its dependency is broken\n"
        f"2. `{flags[2]}` remains unaffected (no upstream dependency)\n"
        f"3. Any function that checks `is_enabled(\"{flags[0]}\")` will enter an untested state\n\n"
        f"### Recommendation\n"
        f"Before disabling `{flags[1]}`, first disable `{flags[0]}` to prevent cascading failures. "
        f"Use `flagguard analyze` to verify the full impact radius."
    )

    return _format_chatml(instruction, response)


def _format_chatml(instruction: str, response: str) -> dict:
    """Format as ChatML-compatible JSONL entry."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ]
    }


# ── Main Pipeline ──

GENERATORS = [
    (_gen_conflict_explanation, 0.25),
    (_gen_fix_suggestion, 0.25),
    (_gen_risk_assessment, 0.20),
    (_gen_dead_code, 0.15),
    (_gen_dependency_analysis, 0.15),
]


def generate_dataset(count: int = 1000, seed: int = 42) -> list[dict]:
    """Generate the synthetic SFT dataset.

    Args:
        count: Total number of samples to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of ChatML-formatted instruction pairs.
    """
    random.seed(seed)
    dataset = []

    for _ in range(count):
        # Weighted random selection of category
        r = random.random()
        cumulative = 0.0
        for gen_fn, weight in GENERATORS:
            cumulative += weight
            if r <= cumulative:
                dataset.append(gen_fn())
                break

    random.shuffle(dataset)
    return dataset


def save_dataset(
    dataset: list[dict],
    output_dir: str = "data/sft_dataset",
):
    """Save dataset as JSONL, split into train/val/test.

    Split: 80% train / 10% val / 10% test
    """
    os.makedirs(output_dir, exist_ok=True)

    total = len(dataset)
    train_end = int(total * 0.8)
    val_end = int(total * 0.9)

    splits = {
        "train": dataset[:train_end],
        "val": dataset[train_end:val_end],
        "test": dataset[val_end:],
    }

    for split_name, split_data in splits.items():
        path = os.path.join(output_dir, f"{split_name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for item in split_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  {split_name}: {len(split_data)} samples → {path}")

    # Also save the full dataset
    full_path = os.path.join(output_dir, "full_dataset.jsonl")
    with open(full_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n  Full dataset: {total} samples → {full_path}")

    # Print category distribution
    print(f"\n  Category distribution:")
    cats = {"conflict": 0, "fix": 0, "risk": 0, "dead_code": 0, "dependency": 0}
    for item in dataset:
        user_msg = item["messages"][1]["content"].lower()
        if "conflict" in user_msg or "mutual" in user_msg:
            cats["conflict"] += 1
        elif "fix" in user_msg or "depends" in user_msg and "generate" in user_msg:
            cats["fix"] += 1
        elif "risk" in user_msg or "assess" in user_msg:
            cats["risk"] += 1
        elif "dead code" in user_msg:
            cats["dead_code"] += 1
        else:
            cats["dependency"] += 1

    for cat, count in cats.items():
        print(f"    {cat}: {count} ({count/total*100:.0f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic SFT dataset for FlagGuard fine-tuning."
    )
    parser.add_argument(
        "--output", type=str, default="data/sft_dataset",
        help="Output directory (default: data/sft_dataset)"
    )
    parser.add_argument(
        "--count", type=int, default=1000,
        help="Number of samples to generate (default: 1000)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    print(f"Generating {args.count} SFT instruction pairs...")
    dataset = generate_dataset(args.count, args.seed)

    print(f"\nSaving to {args.output}/")
    save_dataset(dataset, args.output)

    print(f"\n✅ SFT dataset generation complete!")
    print(f"   Next: Upload to HuggingFace or use in QLoRA training notebook.")


if __name__ == "__main__":
    main()
