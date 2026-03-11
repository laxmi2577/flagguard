"""Feature Engineering Script for FlagGuard Risk Prediction (Phase 2 — Step 2.1).

Mines `.git` history to extract per-commit tabular features for training
an XGBoost classifier that predicts whether a PR will introduce
feature flag conflicts.

Features Extracted:
    - files_modified        : Number of files changed in the commit
    - lines_added           : Total lines added
    - lines_deleted         : Total lines deleted
    - flag_mentions_count   : Count of flag-related function calls in the diff
    - py_files_modified     : Number of .py files changed
    - js_files_modified     : Number of .js/.ts files changed
    - config_files_modified : Number of .json/.yaml config files changed
    - commit_hour           : Hour of day (0-23) — proxy for rushed commits
    - is_merge_commit       : Whether the commit is a merge
    - message_length        : Length of commit message (short = risky)
    - has_test_changes      : Whether tests were modified
    - author_commit_count   : Author's total commit count (experience proxy)

Label:
    - had_conflict          : 1 if the diff contains flag keywords in risky
                              patterns (simulated), 0 otherwise.

Usage:
    python scripts/generate_training_data.py --repo . --output data/training_data.csv

Skills demonstrated: Feature Engineering, Git Mining, Data Pipelines, pandas, GitPython.
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Flag-related patterns that indicate risk
FLAG_PATTERNS = [
    r"is_enabled\s*\(",
    r"is_feature_enabled\s*\(",
    r"feature_enabled\s*\(",
    r"variation\s*\(",
    r"get_flag\s*\(",
    r"has_feature\s*\(",
    r"check_feature\s*\(",
    r"isEnabled\s*\(",
    r"isFeatureEnabled\s*\(",
    r"featureEnabled\s*\(",
]

# Risky patterns that correlate with conflicts
CONFLICT_RISK_PATTERNS = [
    r"conflicts?\s*[:=]",
    r"mutual.*exclusi",
    r"depends_on\s*[:=]",
    r"dependencies\s*[:=]",
    r"if.*is_enabled.*and.*is_enabled",  # Nested flag checks
    r"not\s+is_enabled",  # Negated flag checks
]

FEATURE_COLUMNS = [
    "commit_hash",
    "files_modified",
    "lines_added",
    "lines_deleted",
    "flag_mentions_count",
    "py_files_modified",
    "js_files_modified",
    "config_files_modified",
    "commit_hour",
    "is_merge_commit",
    "message_length",
    "has_test_changes",
    "author_commit_count",
    "days_since_last_commit",
    "diff_size_ratio",
    "had_conflict",  # Label
]


def extract_features_from_repo(repo_path: str, max_commits: int = 500) -> list[dict]:
    """Extract per-commit features from a git repository.

    Args:
        repo_path: Path to the git repository root.
        max_commits: Maximum number of commits to process.

    Returns:
        List of feature dictionaries, one per commit.
    """
    try:
        from git import Repo
    except ImportError:
        print("ERROR: GitPython not installed. Run: pip install gitpython")
        sys.exit(1)

    repo = Repo(repo_path)
    if repo.bare:
        print("ERROR: Repository is bare, cannot extract features.")
        sys.exit(1)

    commits = list(repo.iter_commits("HEAD", max_count=max_commits))
    print(f"Processing {len(commits)} commits from {repo_path}...")

    # Build author commit count lookup
    author_counts: dict[str, int] = {}
    for c in commits:
        author = c.author.email if c.author else "unknown"
        author_counts[author] = author_counts.get(author, 0) + 1

    features_list: list[dict] = []
    prev_commit_time = None

    for i, commit in enumerate(commits):
        try:
            features = _extract_single_commit(
                commit, author_counts, prev_commit_time
            )
            features_list.append(features)
            prev_commit_time = commit.committed_datetime

            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(commits)} commits...")
        except Exception as e:
            print(f"  Warning: Skipped commit {commit.hexsha[:7]}: {e}")
            continue

    print(f"Extracted features from {len(features_list)} commits.")
    return features_list


def _extract_single_commit(commit, author_counts, prev_time) -> dict:
    """Extract features from a single git commit."""
    # Get diff stats
    if commit.parents:
        diff = commit.diff(commit.parents[0], create_patch=True)
        stats = commit.stats
    else:
        # Initial commit — compare against empty tree
        diff = commit.diff(None, create_patch=True)
        stats = commit.stats

    # Basic stats
    files_modified = stats.total.get("files", 0)
    lines_added = stats.total.get("insertions", 0)
    lines_deleted = stats.total.get("deletions", 0)

    # File type breakdown
    py_files = 0
    js_files = 0
    config_files = 0
    has_test_changes = False

    for file_path in stats.files:
        if file_path.endswith(".py"):
            py_files += 1
        elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            js_files += 1
        elif file_path.endswith((".json", ".yaml", ".yml")):
            config_files += 1
        if "test" in file_path.lower() or "spec" in file_path.lower():
            has_test_changes = True

    # Count flag mentions in the diff
    flag_mentions = 0
    conflict_risk_score = 0
    for d in diff:
        try:
            diff_text = d.diff.decode("utf-8", errors="ignore") if d.diff else ""
        except Exception:
            diff_text = ""

        for pattern in FLAG_PATTERNS:
            flag_mentions += len(re.findall(pattern, diff_text))
        for pattern in CONFLICT_RISK_PATTERNS:
            conflict_risk_score += len(re.findall(pattern, diff_text, re.IGNORECASE))

    # Temporal features
    commit_time = commit.committed_datetime
    commit_hour = commit_time.hour
    is_merge = len(commit.parents) > 1
    message_length = len(commit.message.strip())

    # Author experience
    author_email = commit.author.email if commit.author else "unknown"
    author_commit_count = author_counts.get(author_email, 1)

    # Days since last commit
    days_since = 0.0
    if prev_time:
        delta = abs((commit_time - prev_time).total_seconds())
        days_since = delta / 86400.0

    # Diff size ratio (delete/add ratio — high deletion = risky refactoring)
    total_changes = lines_added + lines_deleted
    diff_size_ratio = (lines_deleted / max(lines_added, 1)) if total_changes > 0 else 0.0

    # Label: Heuristic — commit is "risky" if it has flag mentions in
    # conflict-prone patterns, or modifies both config + code with flag refs
    had_conflict = int(
        conflict_risk_score >= 2
        or (flag_mentions >= 3 and config_files >= 1)
        or (flag_mentions >= 2 and lines_deleted > lines_added * 2)
        or (flag_mentions >= 1 and is_merge and config_files >= 1)
    )

    return {
        "commit_hash": commit.hexsha[:8],
        "files_modified": files_modified,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "flag_mentions_count": flag_mentions,
        "py_files_modified": py_files,
        "js_files_modified": js_files,
        "config_files_modified": config_files,
        "commit_hour": commit_hour,
        "is_merge_commit": int(is_merge),
        "message_length": message_length,
        "has_test_changes": int(has_test_changes),
        "author_commit_count": author_commit_count,
        "days_since_last_commit": round(days_since, 2),
        "diff_size_ratio": round(diff_size_ratio, 2),
        "had_conflict": had_conflict,
    }


def generate_synthetic_augmentation(
    real_data: list[dict], target_size: int = 300
) -> list[dict]:
    """Augment real git data with synthetic samples to reach training size.

    Since most repos don't have enough commits with conflicts, this
    generates realistic synthetic samples to balance the dataset.

    Args:
        real_data: List of real commit feature dicts.
        target_size: Target total dataset size.

    Returns:
        Augmented list combining real + synthetic data.
    """
    import random

    augmented = list(real_data)
    needed = max(0, target_size - len(augmented))

    if needed == 0:
        return augmented

    print(f"Augmenting with {needed} synthetic samples to reach {target_size}...")

    for i in range(needed):
        # Decide if this synthetic commit is "risky" (30% chance)
        is_risky = random.random() < 0.30

        if is_risky:
            sample = {
                "commit_hash": f"syn_{i:04d}",
                "files_modified": random.randint(5, 25),
                "lines_added": random.randint(50, 500),
                "lines_deleted": random.randint(30, 400),
                "flag_mentions_count": random.randint(2, 8),
                "py_files_modified": random.randint(2, 10),
                "js_files_modified": random.randint(0, 5),
                "config_files_modified": random.randint(1, 4),
                "commit_hour": random.choice([0, 1, 2, 3, 22, 23]),  # Late night
                "is_merge_commit": random.choice([0, 0, 1]),
                "message_length": random.randint(5, 30),  # Short messages
                "has_test_changes": random.choice([0, 0, 0, 1]),  # Usually no tests
                "author_commit_count": random.randint(1, 15),  # Junior dev
                "days_since_last_commit": round(random.uniform(0.01, 0.5), 2),
                "diff_size_ratio": round(random.uniform(1.5, 5.0), 2),
                "had_conflict": 1,
            }
        else:
            sample = {
                "commit_hash": f"syn_{i:04d}",
                "files_modified": random.randint(1, 8),
                "lines_added": random.randint(5, 200),
                "lines_deleted": random.randint(2, 100),
                "flag_mentions_count": random.randint(0, 2),
                "py_files_modified": random.randint(0, 4),
                "js_files_modified": random.randint(0, 3),
                "config_files_modified": random.randint(0, 1),
                "commit_hour": random.randint(9, 18),  # Working hours
                "is_merge_commit": random.choice([0, 0, 0, 1]),
                "message_length": random.randint(20, 120),  # Descriptive
                "has_test_changes": random.choice([0, 1, 1]),  # Usually has tests
                "author_commit_count": random.randint(10, 200),  # Experienced
                "days_since_last_commit": round(random.uniform(0.1, 5.0), 2),
                "diff_size_ratio": round(random.uniform(0.1, 1.5), 2),
                "had_conflict": 0,
            }

        augmented.append(sample)

    # Shuffle to mix real and synthetic
    random.shuffle(augmented)
    return augmented


def save_to_csv(data: list[dict], output_path: str):
    """Save feature data to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(data)

    # Print stats
    total = len(data)
    conflicts = sum(1 for d in data if d["had_conflict"] == 1)
    print(f"\nDataset saved to: {output_path}")
    print(f"Total samples: {total}")
    print(f"Positive (had_conflict=1): {conflicts} ({conflicts/total*100:.1f}%)")
    print(f"Negative (had_conflict=0): {total - conflicts} ({(total-conflicts)/total*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate training data for FlagGuard risk prediction model."
    )
    parser.add_argument(
        "--repo", type=str, default=".",
        help="Path to the git repository (default: current directory)"
    )
    parser.add_argument(
        "--output", type=str, default="data/training_data.csv",
        help="Output CSV path (default: data/training_data.csv)"
    )
    parser.add_argument(
        "--max-commits", type=int, default=500,
        help="Maximum number of commits to mine (default: 500)"
    )
    parser.add_argument(
        "--augment-to", type=int, default=300,
        help="Augment dataset to this many samples (default: 300)"
    )

    args = parser.parse_args()

    # Step 1: Extract real features from git history
    real_features = extract_features_from_repo(args.repo, args.max_commits)

    # Step 2: Augment with synthetic data if needed
    augmented = generate_synthetic_augmentation(real_features, args.augment_to)

    # Step 3: Save to CSV
    save_to_csv(augmented, args.output)


if __name__ == "__main__":
    main()
