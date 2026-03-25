"""Export Preference Data for DPO Training (Phase 3 — Step 3.3).

Reads 👍/👎 feedback from the SQLAlchemy database and exports it
as a DPO-compatible JSONL file for Direct Preference Optimization.

Output format (DPO-compatible):
    {"prompt": "...", "chosen": "...", "rejected": "..."}

For each prompt that has both positive and negative feedback,
we pair them as (chosen=positive, rejected=negative).

Usage:
    python scripts/export_preferences.py --output data/preference_data.jsonl
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def export_preferences(output_path: str = "data/preference_data.jsonl") -> int:
    """Export preference pairs from the database.

    Strategy:
        - Group feedback by prompt content
        - For prompts with both positive and negative feedback,
          create DPO pairs (chosen/rejected)
        - For prompts with only one type, create synthetic pairs
          by pairing with a generic "bad" response

    Returns:
        Number of preference pairs exported.
    """
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import LLMFeedback
    except ImportError:
        print("ERROR: FlagGuard not installed. Run: pip install -e .")
        sys.exit(1)

    db = SessionLocal()
    try:
        all_feedback = db.query(LLMFeedback).all()
        print(f"Total feedback records: {len(all_feedback)}")

        if not all_feedback:
            print("No feedback found. Users need to rate LLM outputs in the UI first.")
            return 0

        # Group by prompt
        prompt_groups: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: {"positive": [], "negative": []}
        )
        for fb in all_feedback:
            prompt_groups[fb.prompt][fb.feedback].append(fb.response)

        pairs = []

        for prompt, responses in prompt_groups.items():
            pos = responses["positive"]
            neg = responses["negative"]

            if pos and neg:
                # Best case: real preference pair
                for chosen in pos:
                    for rejected in neg:
                        pairs.append({
                            "prompt": prompt,
                            "chosen": chosen,
                            "rejected": rejected,
                        })
            elif pos and not neg:
                # Only positive: create synthetic rejected
                for chosen in pos:
                    pairs.append({
                        "prompt": prompt,
                        "chosen": chosen,
                        "rejected": (
                            "I'm not sure about this. The conflict might involve "
                            "those flags but I'd need more context to provide a "
                            "definitive answer."
                        ),
                    })
            elif neg and not pos:
                # Only negative: create synthetic chosen
                for rejected in neg:
                    pairs.append({
                        "prompt": prompt,
                        "chosen": (
                            "Based on formal verification using the Z3 SAT solver, "
                            "I can identify the exact nature of this conflict and "
                            "provide a verified fix. Let me analyze the constraints."
                        ),
                        "rejected": rejected,
                    })

        # Save
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        print(f"\n✅ Exported {len(pairs)} preference pairs to {output_path}")
        print(f"   Prompts with both +/- feedback: "
              f"{sum(1 for p in prompt_groups.values() if p['positive'] and p['negative'])}")
        print(f"   Positive-only (synthetic rejected): "
              f"{sum(1 for p in prompt_groups.values() if p['positive'] and not p['negative'])}")
        print(f"   Negative-only (synthetic chosen): "
              f"{sum(1 for p in prompt_groups.values() if p['negative'] and not p['positive'])}")

        return len(pairs)

    finally:
        db.close()


def generate_synthetic_preferences(
    output_path: str = "data/preference_data.jsonl",
    count: int = 200,
) -> int:
    """Generate synthetic preference pairs for initial DPO training.

    Used when there isn't enough real user feedback yet. Generates
    high-quality vs low-quality response pairs.

    Returns:
        Number of synthetic pairs generated.
    """
    import random
    random.seed(42)

    flag_pairs = [
        ("dark_mode", "premium_tier"),
        ("payment_v2", "checkout_redesign"),
        ("auth_sso", "legacy_api"),
        ("beta_dashboard", "analytics_v2"),
        ("notification_v3", "email_templates_v2"),
    ]

    pairs = []
    for i in range(count):
        f1, f2 = random.choice(flag_pairs)

        prompt = (
            f"The Z3 solver detected a conflict between `{f1}` and `{f2}`. "
            f"Both flags are enabled but mutually exclusive. Explain this conflict."
        )

        # High-quality response (chosen)
        chosen = (
            f"## Conflict Analysis\n\n"
            f"**Severity:** HIGH\n"
            f"**Type:** Mutual exclusion violation\n\n"
            f"The flags `{f1}` and `{f2}` are both enabled, but they are declared "
            f"as mutually exclusive in the configuration. The Z3 SAT solver proves "
            f"that no valid state exists where both flags can be true simultaneously.\n\n"
            f"### Impact\n"
            f"Functions that check both flags will enter an undefined behavior state. "
            f"This was verified through formal constraint solving — it's not a heuristic.\n\n"
            f"### Fix\n"
            f"Disable `{f2}` (the legacy path) and keep `{f1}` active."
        )

        # Low-quality response (rejected)
        rejected = random.choice([
            f"The flags {f1} and {f2} might conflict. You should check your configuration.",
            f"I think there's an issue with those flags. Try disabling one of them.",
            f"There appears to be a problem. I recommend reviewing the flag settings.",
            f"These flags seem to have a conflict. Please consult the documentation.",
        ])

        pairs.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"✅ Generated {len(pairs)} synthetic preference pairs → {output_path}")
    return len(pairs)


def main():
    parser = argparse.ArgumentParser(
        description="Export preference data for DPO training."
    )
    parser.add_argument(
        "--output", type=str, default="data/preference_data.jsonl",
    )
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Generate synthetic pairs instead of exporting from DB",
    )
    parser.add_argument(
        "--synthetic-count", type=int, default=200,
    )

    args = parser.parse_args()

    if args.synthetic:
        generate_synthetic_preferences(args.output, args.synthetic_count)
    else:
        count = export_preferences(args.output)
        if count == 0:
            print("\nTip: Use --synthetic to generate initial training data.")


if __name__ == "__main__":
    main()
