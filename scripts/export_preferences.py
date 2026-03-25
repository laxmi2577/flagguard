"""Export Preference Data for DPO Alignment (Phase 3 — Step 3.3).

Reads 👍/👎 feedback from the SQLAlchemy `llm_feedback` table and converts
it into a DPO-compatible JSONL file (prompt / chosen / rejected triples)
for use with `trl.DPOTrainer`.

Pairing Strategy:
    REAL pairs:      Same prompt has both 👍 and 👎 responses — highest quality.
    SYNTHETIC-neg:   Prompt has only 👍 — generates a diverse synthetic rejected.
    SYNTHETIC-pos:   Prompt has only 👎 — generates a formal synthetic chosen.

Quality Filters:
    - Skips pairs where chosen ≈ rejected (cosine-sim proxy via token-overlap)
    - Deduplicates pairs by SHA-256 hash of (prompt, chosen, rejected)
    - Skips responses shorter than MIN_RESPONSE_CHARS as likely truncated
    - Reports a full export analytics table at the end

Usage:
    # From real UI feedback (requires users to have rated outputs):
    python scripts/export_preferences.py --output data/preference_data.jsonl

    # Synthetic bootstrap (for initial DPO training before real feedback):
    python scripts/export_preferences.py --synthetic --synthetic-count 500

    # Combine both:
    python scripts/export_preferences.py --synthetic --append-real
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dpo_exporter")

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_RESPONSE_CHARS: int = 80
MAX_SIMILARITY_RATIO: float = 0.85  # skip if chosen/rejected are too similar
SYNTHETIC_CHOSEN_TEMPLATES: list[str] = [
    (
        "## Analysis\n\n"
        "Using the Z3 SAT solver and NetworkX knowledge graph, I can formally verify "
        "the conflict state and provide a precise resolution.\n\n"
        "### Constraint Violation\n"
        "The flags `{f1}` and `{f2}` declare a mutual exclusion constraint, but both "
        "are currently `enabled=true`. The Z3 solver proves that no valid program state "
        "satisfies `f1=true ∧ f2=true ∧ invariant_holds`.\n\n"
        "### Recommended Fix\n"
        "```diff\n"
        "-  \"{f2}\": true\n"
        "+  \"{f2}\": false  # deprecated path — {f1} supersedes this\n"
        "```\n\n"
        "**Next step:** `flagguard flag disable {f2} --env production --reason superseded-by-{f1}`"
    ),
    (
        "## Formal Verification Report\n\n"
        "| Property | Value |\n"
        "|----------|-------|\n"
        "| Flags | `{f1}` ↔ `{f2}` |\n"
        "| Conflict type | Mutual exclusion violation |\n"
        "| Severity | HIGH |\n\n"
        "### Root Cause\n"
        "I traced the call graph using FlagGuard's AST analyzer and found that `{f1}` "
        "and `{f2}` share a code path in the request-handling layer. When both are "
        "enabled, the execution enters a branch that has contradictory return semantics "
        "— undefined behavior that Z3 proves is unreachable under safe constraints.\n\n"
        "### Resolution\n"
        "Disable `{f2}` (the legacy path). Run `flagguard analyze --strict` to verify "
        "the constraint set becomes satisfiable after the change."
    ),
]
SYNTHETIC_REJECTED_TEMPLATES: list[str] = [
    "The flags {f1} and {f2} might conflict. You should check your configuration.",
    "I think there's an issue with those flags. Try disabling one of them and see if it helps.",
    "There appears to be a problem with the flag settings. I recommend reviewing the documentation.",
    "These flags seem to have a conflict. Please consult your feature flag dashboard.",
    "You may have a conflict here. Try disabling {f2} and redeploying.",
    "I'm not certain about the exact cause, but the configuration appears inconsistent.",
]


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class PreferencePair:
    prompt: str
    chosen: str
    rejected: str
    pair_type: str  # "real", "synthetic_neg", "synthetic_pos"

    @property
    def content_hash(self) -> str:
        payload = f"{self.prompt}|{self.chosen}|{self.rejected}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def similarity_ratio(self) -> float:
        """Rough token-overlap similarity between chosen and rejected."""
        chosen_tokens = set(self.chosen.lower().split())
        rejected_tokens = set(self.rejected.lower().split())
        if not chosen_tokens or not rejected_tokens:
            return 0.0
        intersection = chosen_tokens & rejected_tokens
        return len(intersection) / max(len(chosen_tokens), len(rejected_tokens))

    def is_valid(self) -> bool:
        """Quality filter — skip trivially similar or too-short pairs."""
        if len(self.chosen) < MIN_RESPONSE_CHARS:
            return False
        if len(self.rejected) < MIN_RESPONSE_CHARS:
            return False
        if self.chosen.strip() == self.rejected.strip():
            return False
        if self.similarity_ratio() > MAX_SIMILARITY_RATIO:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "_meta": {"pair_type": self.pair_type, "hash": self.content_hash},
        }


# ── DB Export ─────────────────────────────────────────────────────────────────

def export_from_database(output_path: str) -> list[PreferencePair]:
    """Load feedback from SQLAlchemy and construct real preference pairs.

    Returns:
        List of valid PreferencePair objects.
    """
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import LLMFeedback
    except ImportError:
        log.error("FlagGuard not installed. Run: pip install -e .")
        sys.exit(1)

    db = SessionLocal()
    try:
        records = db.query(LLMFeedback).order_by(LLMFeedback.created_at).all()
    finally:
        db.close()

    log.info("Loaded %d feedback records from DB.", len(records))
    if not records:
        log.warning("No feedback records found. Users need to rate LLM outputs in the UI first.")
        return []

    # Group by prompt: {prompt -> {feedback_type -> [responses]}}
    groups: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"positive": [], "negative": []}
    )
    for rec in records:
        if rec.response and len(rec.response) >= MIN_RESPONSE_CHARS:
            groups[rec.prompt][rec.feedback].append(rec.response)

    pairs: list[PreferencePair] = []

    for prompt, responses in groups.items():
        pos_list = responses["positive"]
        neg_list = responses["negative"]

        if pos_list and neg_list:
            # Best case — real human preference signal
            for chosen in pos_list:
                for rejected in neg_list:
                    p = PreferencePair(
                        prompt=prompt,
                        chosen=chosen,
                        rejected=rejected,
                        pair_type="real",
                    )
                    if p.is_valid():
                        pairs.append(p)

        elif pos_list:
            # Only positive: inject synthetic rejected
            for chosen in pos_list:
                rejected = random.choice(SYNTHETIC_REJECTED_TEMPLATES)
                # Inject flag names if detectable from prompt
                f1, f2 = _extract_flags_from_prompt(prompt)
                rejected = rejected.format(f1=f1, f2=f2)
                p = PreferencePair(
                    prompt=prompt,
                    chosen=chosen,
                    rejected=rejected,
                    pair_type="synthetic_neg",
                )
                if p.is_valid():
                    pairs.append(p)

        elif neg_list:
            f1, f2 = _extract_flags_from_prompt(prompt)
            for rejected in neg_list:
                chosen_tmpl = random.choice(SYNTHETIC_CHOSEN_TEMPLATES)
                chosen = chosen_tmpl.format(f1=f1, f2=f2)
                p = PreferencePair(
                    prompt=prompt,
                    chosen=chosen,
                    rejected=rejected,
                    pair_type="synthetic_pos",
                )
                if p.is_valid():
                    pairs.append(p)

    return pairs


def _extract_flags_from_prompt(prompt: str) -> tuple[str, str]:
    """Heuristically extract flag names from a prompt for synthetic templates."""
    import re
    backtick_words = re.findall(r"`([a-z_][a-z_0-9]*)`", prompt)
    flags = [w for w in backtick_words if "_" in w]
    if len(flags) >= 2:
        return flags[0], flags[1]
    if len(flags) == 1:
        return flags[0], "legacy_feature"
    return "feature_flag_a", "feature_flag_b"


# ── Synthetic Generation ──────────────────────────────────────────────────────

_FLAG_PAIRS: list[tuple[str, str]] = [
    ("dark_mode", "premium_tier"),
    ("payment_v2", "checkout_redesign"),
    ("auth_sso", "legacy_api_compat"),
    ("beta_dashboard", "analytics_v3"),
    ("notification_v3", "email_templates_v2"),
    ("search_ai", "legacy_search"),
    ("mobile_api_v3", "mobile_api_v2"),
    ("zero_downtime_deploy", "shadow_mode"),
    ("ml_recommendations", "static_recommendations"),
    ("graphql_beta", "rest_api_v1"),
]


def generate_synthetic_pairs(count: int = 500, seed: int = 42) -> list[PreferencePair]:
    """Bootstrap synthetic DPO pairs before real feedback accumulates.

    Each pair uses a unique prompt phrasing + chosen template + rejected template
    to maximize diversity and prevent spurious memorization.

    Returns:
        List of validated PreferencePair objects.
    """
    random.seed(seed)
    pairs: list[PreferencePair] = []

    prompt_phrasings = [
        "The Z3 solver detected a {severity} conflict between `{f1}` and `{f2}`. Both are enabled but mutually exclusive. Explain this conflict.",
        "FlagGuard blocked our deployment: flags `{f1}` and `{f2}` are both active but incompatible. What's the root cause and fix?",
        "Our CI pipeline shows:\n  CONFLICT [{severity}]: {f1} ↔ {f2} (mutual exclusion)\nExplain this for the incident post-mortem.",
        "A junior engineer enabled `{f1}` for an A/B test, but `{f2}` was already on. Now FlagGuard is blocking the merge. Why, and how do we fix it?",
        "Generate an incident summary for: {f1} and {f2} are simultaneously enabled, causing undefined behavior in production checkout.",
    ]
    severities = ["CRITICAL", "HIGH", "MEDIUM"]
    attempts = 0
    seen: set[str] = set()

    while len(pairs) < count and attempts < count * 4:
        attempts += 1
        f1, f2 = random.choice(_FLAG_PAIRS)
        severity = random.choice(severities)
        prompt = random.choice(prompt_phrasings).format(f1=f1, f2=f2, severity=severity)

        chosen_tmpl = random.choice(SYNTHETIC_CHOSEN_TEMPLATES)
        chosen = chosen_tmpl.format(f1=f1, f2=f2)

        rejected_tmpl = random.choice(SYNTHETIC_REJECTED_TEMPLATES)
        rejected = rejected_tmpl.format(f1=f1, f2=f2)

        p = PreferencePair(
            prompt=prompt, chosen=chosen, rejected=rejected,
            pair_type="synthetic_neg",
        )
        if p.is_valid() and p.content_hash not in seen:
            seen.add(p.content_hash)
            pairs.append(p)

    log.info("Generated %d synthetic pairs (target=%d, attempts=%d)", len(pairs), count, attempts)
    return pairs


# ── Deduplication & Saving ────────────────────────────────────────────────────

def _deduplicate(pairs: list[PreferencePair]) -> list[PreferencePair]:
    """Remove hash-identical pairs, keeping the first occurrence."""
    seen: set[str] = set()
    result: list[PreferencePair] = []
    for p in pairs:
        h = p.content_hash
        if h not in seen:
            seen.add(h)
            result.append(p)
    removed = len(pairs) - len(result)
    if removed:
        log.info("Deduplication: removed %d duplicate pairs.", removed)
    return result


def save_pairs(pairs: list[PreferencePair], output_path: str) -> None:
    """Write pairs to JSONL and print an analytics report."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    # Analytics
    from collections import Counter
    type_counts = Counter(p.pair_type for p in pairs)
    avg_chosen_len = sum(len(p.chosen) for p in pairs) // max(len(pairs), 1)
    avg_rejected_len = sum(len(p.rejected) for p in pairs) // max(len(pairs), 1)

    log.info("=" * 55)
    log.info("DPO EXPORT REPORT")
    log.info("=" * 55)
    log.info("  Output         : %s", output_path)
    log.info("  Total pairs    : %d", len(pairs))
    log.info("")
    log.info("  Pair type breakdown:")
    for ptype, cnt in sorted(type_counts.items()):
        pct = cnt / len(pairs) * 100
        log.info("    %-20s %4d  (%5.1f%%)", ptype, cnt, pct)
    log.info("")
    log.info("  Avg chosen len  : %d chars", avg_chosen_len)
    log.info("  Avg rejected len: %d chars", avg_rejected_len)
    log.info("=" * 55)
    log.info("✅ DPO dataset saved.")
    log.info("   Next step: python notebooks/flagguard_dpo_training.py --data %s", output_path)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export preference pairs for DPO fine-tuning.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--output", default="data/preference_data.jsonl")
    parser.add_argument("--synthetic", action="store_true",
                        help="Generate synthetic preference pairs (bootstrap mode)")
    parser.add_argument("--synthetic-count", type=int, default=500,
                        help="Number of synthetic pairs to generate")
    parser.add_argument("--synthetic-seed", type=int, default=42)
    parser.add_argument("--append-real", action="store_true",
                        help="When used with --synthetic: also export real DB feedback and combine")
    args = parser.parse_args()

    all_pairs: list[PreferencePair] = []

    if args.synthetic:
        log.info("Generating %d synthetic preference pairs…", args.synthetic_count)
        all_pairs.extend(generate_synthetic_pairs(args.synthetic_count, args.synthetic_seed))

    if args.append_real or not args.synthetic:
        log.info("Exporting real preference pairs from DB…")
        real_pairs = export_from_database(args.output)
        if not real_pairs and not args.synthetic:
            log.warning("No real feedback found. Run with --synthetic to generate bootstrap data.")
            log.info("  Tip: Use --synthetic --append-real to merge both sources.")
        all_pairs.extend(real_pairs)

    if not all_pairs:
        log.error("No preference pairs generated or exported. Aborting.")
        sys.exit(1)

    all_pairs = _deduplicate(all_pairs)
    random.shuffle(all_pairs)
    save_pairs(all_pairs, args.output)


if __name__ == "__main__":
    main()
