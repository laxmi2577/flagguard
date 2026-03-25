"""FlagGuard DPO Alignment Training (Phase 3 — Step 3.4).

Direct Preference Optimization (DPO) to align the SFT-trained model with
human preferences collected from the FlagGuard UI feedback system.

Why DPO over PPO?
    DPO eliminates the need for a separate reward model (and its VRAM cost).
    Instead, the Bradley-Terry preference model is baked into the loss function
    itself. For a small-scale RLHF project like FlagGuard, DPO is the
    practical choice: simpler, cheaper, and equally effective.

Architecture:
    - Reference policy:  Loaded from the SFT checkpoint (frozen)
    - Trained policy:    New LoRA adapters applied on top of the same base model
    - Both loaded with NF4 4-bit quantization to fit within Colab T4 (15GB)
    - DPO beta=0.1 (controls deviation from reference — lower = tighter alignment)
    - Label smoothing=0.0 for standard DPO (set ~0.1 to soften extreme responses)

Pipeline:
    1. Load SFT model as base (frozen reference)
    2. Apply fresh LoRA adapters (the trained policy)
    3. Load preference dataset (prompt / chosen / rejected)
    4. Train with trl.DPOTrainer using cosine LR + adamw_8bit
    5. Evaluate win rate (chosen logprob > rejected logprob) on held-out slice
    6. Save DPO-aligned LoRA adapters

Usage:
    # Step 1: Generate preference data (if needed)
    python scripts/export_preferences.py --synthetic --synthetic-count 500

    # Step 2: Run DPO training
    python notebooks/flagguard_dpo_training.py --model models/flagguard-sft-lora

    # Step 3: Export to Ollama
    python scripts/export_gguf.py --lora-dir models/flagguard-dpo-lora
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("flagguard.dpo")


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class DPOModelConfig:
    """Model loading settings for DPO (same as SFT but more conservative)."""
    sft_model_path: str = "models/flagguard-sft-lora"
    base_model_fallback: str = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
    max_seq_length: int = 2048
    load_in_4bit: bool = True


@dataclass
class DPOLoraConfig:
    """LoRA config applied to the trained policy (reference policy is frozen)."""
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])
    use_gradient_checkpointing: str = "unsloth"


@dataclass
class DPOTrainConfig:
    """DPOTrainer + TrainingArguments settings."""
    output_dir: str = "models/flagguard-dpo-lora"
    num_train_epochs: int = 2
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8       # effective batch = 8
    warmup_ratio: float = 0.1
    learning_rate: float = 5e-6               # DPO needs much lower LR than SFT
    fp16: bool = True
    bf16: bool = False
    logging_steps: int = 5
    save_strategy: str = "epoch"
    eval_strategy: str = "no"                 # eval via win_rate below
    optim: str = "adamw_8bit"
    weight_decay: float = 0.01
    lr_scheduler_type: str = "cosine"
    seed: int = 42
    report_to: str = "none"
    # DPO-specific
    beta: float = 0.1
    max_length: int = 2048
    max_prompt_length: int = 1024
    label_smoothing: float = 0.0


# ── Install ────────────────────────────────────────────────────────────────────

def install_dependencies() -> None:
    """Install DPO-specific dependencies (idempotent)."""
    deps = {
        "unsloth": 'pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"',
        "trl": 'pip install -q "trl>=0.9.0"',
        "peft": 'pip install -q "peft>=0.10.0"',
        "transformers": 'pip install -q "transformers>=4.40.0"',
    }
    for pkg, cmd in deps.items():
        try:
            __import__(pkg)
        except ImportError:
            log.info("Installing %s…", pkg)
            if os.system(cmd) != 0:
                log.error("Failed to install %s", pkg)
                sys.exit(1)
    log.info("✅ All DPO dependencies available.")


# ── Model Loading ─────────────────────────────────────────────────────────────

def load_policy_model(
    model_cfg: DPOModelConfig,
    lora_cfg: DPOLoraConfig,
):
    """Load the base/SFT model and apply fresh LoRA adapters for the trained policy.

    The DPOTrainer (with ref_model=None) internally clones the initial adapter
    weights as the reference policy before training begins — so we only need
    to load the model once.

    Returns:
        Tuple[model, tokenizer]
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        log.error("Unsloth not installed. Run with --install flag.")
        sys.exit(1)

    model_name = model_cfg.sft_model_path
    if not Path(model_name).exists():
        log.warning(
            "SFT model not found at %s. Falling back to base model: %s",
            model_name, model_cfg.base_model_fallback,
        )
        model_name = model_cfg.base_model_fallback

    log.info("Loading model: %s", model_name)
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=model_cfg.max_seq_length,
            dtype=None,
            load_in_4bit=model_cfg.load_in_4bit,
        )
    except Exception as exc:
        log.error("Model loading failed: %s", exc)
        sys.exit(1)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"  # DPO prefers left-padding for generation

    # Apply fresh LoRA adapters (these are the TRAINED policy weights)
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg.r,
        lora_alpha=lora_cfg.lora_alpha,
        lora_dropout=lora_cfg.lora_dropout,
        target_modules=lora_cfg.target_modules,
        bias="none",
        use_gradient_checkpointing=lora_cfg.use_gradient_checkpointing,
        random_state=42,
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log.info("LoRA adapters applied: %s / %s trainable (%.2f%%)",
             f"{trainable:,}", f"{total:,}", 100 * trainable / total)

    return model, tokenizer


# ── Dataset Loading ────────────────────────────────────────────────────────────

def _load_jsonl(path: str | Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.warning("Line %d: malformed JSON — %s", lineno, exc)
    return records


def load_preference_dataset(data_path: str, tokenizer, cfg: DPOTrainConfig):
    """Load and tokenize the preference dataset for DPOTrainer.

    The DPO format is:
        prompt:   The user input (as a formatted chat string)
        chosen:   The preferred (high-quality) completion
        rejected: The rejected (low-quality) completion

    We format the prompt using the tokenizer's apply_chat_template to match
    the training format, then pass raw strings to DPOTrainer (which does
    its own tokenization internally).

    Returns:
        Tuple[train_dataset, eval_dataset | None]
    """
    try:
        from datasets import Dataset
    except ImportError:
        log.error("`datasets` package not installed.")
        sys.exit(1)

    path = Path(data_path)
    if not path.exists():
        log.error(
            "%s not found.\n"
            "Generate it first:\n"
            "  python scripts/export_preferences.py --synthetic --synthetic-count 500",
            data_path,
        )
        sys.exit(1)

    raw = _load_jsonl(path)
    log.info("Loaded %d preference pairs from %s", len(raw), data_path)

    formatted = []
    invalid_count = 0
    for item in raw:
        prompt = item.get("prompt", "")
        chosen = item.get("chosen", "")
        rejected = item.get("rejected", "")

        if not prompt or not chosen or not rejected:
            invalid_count += 1
            continue
        if chosen.strip() == rejected.strip():
            invalid_count += 1
            continue  # identical responses are useless for DPO

        # Format the prompt using Llama-3 chat template
        try:
            prompt_formatted = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": (
                        "You are FlagGuard-Coder, an expert AI assistant "
                        "specializing in feature flag conflict resolution."
                    )},
                    {"role": "user", "content": prompt},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            prompt_formatted = (
                "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                "You are FlagGuard-Coder.<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n"
            )

        formatted.append({
            "prompt": prompt_formatted,
            "chosen": f"{chosen}<|eot_id|>",
            "rejected": f"{rejected}<|eot_id|>",
        })

    if invalid_count:
        log.warning("Skipped %d invalid/duplicate preference pairs.", invalid_count)

    if not formatted:
        log.error("No valid preference pairs after filtering. Check your dataset.")
        sys.exit(1)

    # 90/10 train/eval split
    split_idx = max(1, int(len(formatted) * 0.9))
    train_data = formatted[:split_idx]
    eval_data = formatted[split_idx:]

    train_ds = Dataset.from_list(train_data)
    eval_ds = Dataset.from_list(eval_data) if eval_data else None

    log.info("DPO dataset → train=%d  eval=%d", len(train_ds), len(eval_ds) if eval_ds else 0)
    return train_ds, eval_ds


# ── DPO Training ──────────────────────────────────────────────────────────────

def train_dpo(
    model,
    tokenizer,
    train_ds,
    eval_ds,
    cfg: DPOTrainConfig,
) -> Any:
    """Train the model using DPOTrainer.

    Key design choice: ref_model=None — TRL handles the frozen reference
    policy internally by snapshotting the adapter weights before training.
    This halves VRAM usage compared to loading two separate models.
    """
    try:
        from trl import DPOTrainer, DPOConfig
    except ImportError:
        try:
            from trl import DPOTrainer
            from transformers import TrainingArguments as DPOConfig  # fallback
        except ImportError:
            log.error("TRL not installed. Run with --install.")
            sys.exit(1)

    report_to = cfg.report_to
    if report_to == "none" and os.environ.get("WANDB_API_KEY"):
        report_to = "wandb"
        log.info("WANDB_API_KEY detected — enabling W&B DPO tracking.")

    try:
        # TRL >= 0.9 uses DPOConfig
        dpo_config = DPOConfig(
            output_dir=cfg.output_dir,
            num_train_epochs=cfg.num_train_epochs,
            per_device_train_batch_size=cfg.per_device_train_batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            warmup_ratio=cfg.warmup_ratio,
            learning_rate=cfg.learning_rate,
            fp16=cfg.fp16,
            bf16=cfg.bf16,
            logging_steps=cfg.logging_steps,
            save_strategy=cfg.save_strategy,
            optim=cfg.optim,
            weight_decay=cfg.weight_decay,
            lr_scheduler_type=cfg.lr_scheduler_type,
            seed=cfg.seed,
            report_to=report_to,
            beta=cfg.beta,
            max_length=cfg.max_length,
            max_prompt_length=cfg.max_prompt_length,
            label_smoothing=cfg.label_smoothing,
            save_total_limit=1,
        )
        trainer = DPOTrainer(
            model=model,
            ref_model=None,    # TRL uses PEFT reference internally
            args=dpo_config,
            train_dataset=train_ds,
            eval_dataset=eval_ds,
            tokenizer=tokenizer,
        )
    except TypeError:
        # Fallback for older TRL API
        from transformers import TrainingArguments
        training_args = TrainingArguments(
            output_dir=cfg.output_dir,
            num_train_epochs=cfg.num_train_epochs,
            per_device_train_batch_size=cfg.per_device_train_batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            warmup_ratio=cfg.warmup_ratio,
            learning_rate=cfg.learning_rate,
            fp16=cfg.fp16,
            logging_steps=cfg.logging_steps,
            save_strategy=cfg.save_strategy,
            optim=cfg.optim,
            weight_decay=cfg.weight_decay,
            lr_scheduler_type=cfg.lr_scheduler_type,
            seed=cfg.seed,
            report_to=report_to,
        )
        trainer = DPOTrainer(
            model=model,
            ref_model=None,
            args=training_args,
            beta=cfg.beta,
            train_dataset=train_ds,
            eval_dataset=eval_ds,
            tokenizer=tokenizer,
            max_length=cfg.max_length,
            max_prompt_length=cfg.max_prompt_length,
        )

    log.info("=" * 60)
    log.info("STARTING DPO ALIGNMENT TRAINING")
    log.info("=" * 60)
    log.info("  Beta         : %.2f  (deviation from reference policy)", cfg.beta)
    log.info("  LR           : %g", cfg.learning_rate)
    log.info("  Eff. batch   : %d × %d = %d",
             cfg.per_device_train_batch_size,
             cfg.gradient_accumulation_steps,
             cfg.per_device_train_batch_size * cfg.gradient_accumulation_steps)
    log.info("  Train pairs  : %d", len(train_ds))
    log.info("  ref_model    : implicit (PEFT snapshot, saves ~50%% VRAM)")

    t0 = time.time()
    result = trainer.train()
    elapsed = time.time() - t0

    log.info("DPO training complete in %.1f min", elapsed / 60)
    log.info("  global_step    : %d", result.global_step)
    log.info("  training_loss  : %.4f", result.training_loss)

    return model, result


# ── Win Rate Evaluation ───────────────────────────────────────────────────────

def compute_win_rate(model, tokenizer, eval_ds, max_samples: int = 50) -> float:
    """Compute DPO win rate: fraction of pairs where chosen logprob > rejected logprob.

    This is the primary DPO alignment metric. A win rate > 0.5 means the model
    has successfully learned to prefer higher-quality responses.

    Returns:
        Win rate as a float in [0.0, 1.0].
    """
    if eval_ds is None or len(eval_ds) == 0:
        log.warning("No eval set available for win rate computation.")
        return float("nan")

    try:
        import torch
    except ImportError:
        log.warning("PyTorch not importable — skipping win rate.")
        return float("nan")

    try:
        from unsloth import FastLanguageModel
        FastLanguageModel.for_inference(model)
    except Exception:
        pass

    wins = 0
    total = min(max_samples, len(eval_ds))
    model.eval()

    samples = eval_ds.select(range(total))
    log.info("Computing win rate on %d eval pairs…", total)

    for item in samples:
        prompt = item["prompt"]
        chosen = item["chosen"]
        rejected = item["rejected"]

        def _logprob(continuation: str) -> float:
            full_text = prompt + continuation
            enc = tokenizer(full_text, return_tensors="pt", truncation=True,
                            max_length=2048).to(model.device)
            prompt_len = len(tokenizer.encode(prompt, add_special_tokens=False))
            with torch.no_grad():
                logits = model(**enc).logits
            log_probs = torch.nn.functional.log_softmax(logits[0], dim=-1)
            labels = enc["input_ids"][0][1:]       # shift right
            label_log_probs = log_probs[:-1]       # align lengths
            token_lps = label_log_probs[range(len(labels)), labels]
            return token_lps[prompt_len:].sum().item()

        lp_chosen = _logprob(chosen)
        lp_rejected = _logprob(rejected)
        if lp_chosen > lp_rejected:
            wins += 1

    win_rate = wins / total
    log.info("Win rate: %.3f (%d/%d pairs prefer chosen)", win_rate, wins, total)
    return win_rate


# ── Save ──────────────────────────────────────────────────────────────────────

def save_aligned_model(
    model,
    tokenizer,
    output_dir: str,
    model_cfg: DPOModelConfig,
    lora_cfg: DPOLoraConfig,
    train_cfg: DPOTrainConfig,
    win_rate: float = float("nan"),
) -> None:
    """Save DPO-aligned LoRA adapters and provenance metadata."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    meta = {
        "framework": "flagguard-dpo-v2",
        "sft_checkpoint": model_cfg.sft_model_path,
        "base_model_fallback": model_cfg.base_model_fallback,
        "lora": asdict(lora_cfg),
        "dpo_config": asdict(train_cfg),
        "eval": {"win_rate": win_rate if not __import__("math").isnan(win_rate) else None},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "adapter_meta.json").write_text(json.dumps(meta, indent=2))

    log.info("✅ DPO-aligned adapters saved to %s/", output_dir)
    log.info("   Next: python scripts/export_gguf.py --lora-dir %s", output_dir)


# ── CLI / Main ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FlagGuard DPO Alignment Training",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data", default="data/preference_data.jsonl")
    parser.add_argument("--model", default=DPOModelConfig.sft_model_path,
                        help="Path to SFT LoRA adapters (output of sft_training.py)")
    parser.add_argument("--output", default="models/flagguard-dpo-lora")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--beta", type=float, default=0.1,
                        help="DPO temperature (lower = tighter alignment with reference)")
    parser.add_argument("--max-eval-samples", type=int, default=50)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--bf16", action="store_true", help="Use bfloat16 (A100+)")

    args = parser.parse_args()

    if args.install:
        install_dependencies()

    model_cfg = DPOModelConfig(sft_model_path=args.model)
    lora_cfg = DPOLoraConfig()
    train_cfg = DPOTrainConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        beta=args.beta,
        bf16=args.bf16,
        fp16=not args.bf16,
    )

    model, tokenizer = load_policy_model(model_cfg, lora_cfg)
    train_ds, eval_ds = load_preference_dataset(args.data, tokenizer, train_cfg)

    model, training_result = train_dpo(model, tokenizer, train_ds, eval_ds, train_cfg)

    win_rate = compute_win_rate(model, tokenizer, eval_ds, max_samples=args.max_eval_samples)

    save_aligned_model(model, tokenizer, args.output, model_cfg, lora_cfg, train_cfg, win_rate)

    log.info("=" * 60)
    log.info("DPO PIPELINE COMPLETE")
    log.info("  Win rate: %.3f", win_rate)
    log.info("  Adapters: %s", args.output)
    log.info("  Next:     python scripts/export_gguf.py --lora-dir %s", args.output)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
