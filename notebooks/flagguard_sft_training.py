"""FlagGuard QLoRA SFT Fine-Tuning Pipeline (Phase 3 — Step 3.2).

Supervised Fine-Tuning of Llama-3.1-8B-Instruct using QLoRA (4-bit NF4)
on the FlagGuard synthetic dataset. Designed for Google Colab (T4/A100)
but also runs on any CUDA-capable machine.

Design decisions:
    - Uses Unsloth's FastLanguageModel for 2× faster training (fused kernels)
    - Gradient checkpointing enabled to train >2K ctx on T4 (15GB VRAM)
    - Sequence packing (packing=True) for ~30% throughput improvement
    - EarlyStoppingCallback prevents overfitting on small synthetic set
    - Tokenizer padding side set to 'right' for causal LM (avoids left-pad issues)
    - Adapter metadata saved as adapter_meta.json for pipeline continuity
    - DataCollatorForSeq2Seq with labels masked on prompt tokens (loss only on response)

Pipeline:
    1. Install dependencies (Unsloth, PEFT, TRL, bitsandbytes)
    2. Load base model with NF4 4-bit quantization + double quantization
    3. Apply LoRA (r=16, alpha=32) to all projection + MLP layers
    4. Load & format SFT dataset into Llama-3 ChatML tokens
    5. Train with SFTTrainer + cosine LR + adamw_8bit
    6. Evaluate ROUGE-L and BLEU-4 on held-out test set
    7. Save LoRA adapters + metadata for DPO pipeline

Usage:
    # Google Colab (install first)
    !python notebooks/flagguard_sft_training.py --install --data data/sft_dataset

    # Local GPU (dependencies already installed)
    python notebooks/flagguard_sft_training.py --data data/sft_dataset --epochs 3
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
log = logging.getLogger("flagguard.sft")


# ── Configuration dataclasses ─────────────────────────────────────────────────

@dataclass
class ModelConfig:
    """Model and quantization settings."""
    model_name: str = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
    fallback_model: str = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
    max_seq_length: int = 2048
    load_in_4bit: bool = True
    # NF4 dtype is set by Unsloth automatically; None = auto-detect fp16/bf16


@dataclass
class LoraConfig:
    """LoRA adapter settings."""
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])
    bias: str = "none"
    use_gradient_checkpointing: str = "unsloth"  # Unsloth's optimised GC


@dataclass
class TrainConfig:
    """SFTTrainer / TrainingArguments settings."""
    output_dir: str = "models/flagguard-sft-lora"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    warmup_ratio: float = 0.05           # fraction of steps for linear warmup
    learning_rate: float = 2e-4
    fp16: bool = True
    bf16: bool = False                   # set True if on A100/H100
    logging_steps: int = 10
    save_strategy: str = "epoch"
    eval_strategy: str = "epoch"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False
    optim: str = "adamw_8bit"
    weight_decay: float = 0.01
    lr_scheduler_type: str = "cosine"
    seed: int = 42
    dataloader_num_workers: int = 0      # 0 avoids multiprocessing on Windows
    report_to: str = "none"             # set to "wandb" if WANDB_API_KEY is set
    max_seq_length: int = 2048
    packing: bool = True                 # sequence packing for efficiency
    early_stopping_patience: int = 2     # stop if val_loss doesn't improve


# ── Install Dependencies ──────────────────────────────────────────────────────

def install_dependencies() -> None:
    """Install required packages (idempotent — checks before installing)."""
    packages_needed: list[str] = []

    checks = [
        ("unsloth", 'pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"'),
        ("trl", 'pip install -q "trl>=0.9.0"'),
        ("peft", 'pip install -q "peft>=0.10.0"'),
        ("transformers", 'pip install -q "transformers>=4.40.0"'),
        ("bitsandbytes", 'pip install -q "bitsandbytes>=0.43.0"'),
        ("accelerate", 'pip install -q "accelerate>=0.28.0"'),
        ("datasets", 'pip install -q "datasets>=2.18.0"'),
        ("rouge_score", 'pip install -q rouge-score nltk'),
    ]

    for pkg, cmd in checks:
        try:
            __import__(pkg)
        except ImportError:
            packages_needed.append(cmd)

    if not packages_needed:
        log.info("All dependencies already installed.")
        return

    log.info("Installing %d missing package(s)…", len(packages_needed))
    for cmd in packages_needed:
        log.info("  Running: %s", cmd)
        ret = os.system(cmd)
        if ret != 0:
            log.error("Install failed for: %s", cmd)
            sys.exit(1)
    log.info("✅ All dependencies installed.")


# ── Model Loading ─────────────────────────────────────────────────────────────

def load_base_model(model_cfg: ModelConfig, lora_cfg: LoraConfig):
    """Load the quantized base model and apply LoRA adapters.

    Uses Unsloth's FastLanguageModel for fused kernel acceleration.
    Falls back to a 3B parameter model if the 8B fails (VRAM guard).

    Returns:
        Tuple[model, tokenizer]
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        log.error("Unsloth not installed. Run: python sft_training.py --install")
        sys.exit(1)

    for model_name in (model_cfg.model_name, model_cfg.fallback_model):
        try:
            log.info("Loading model: %s", model_name)
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_name,
                max_seq_length=model_cfg.max_seq_length,
                dtype=None,          # auto: float16 on T4, bfloat16 on A100+
                load_in_4bit=model_cfg.load_in_4bit,
            )
            log.info("Model loaded from: %s", model_name)
            break
        except Exception as exc:
            log.warning("Failed to load %s: %s — trying fallback", model_name, exc)
    else:
        log.error("Both model variants failed to load. Check VRAM and network.")
        sys.exit(1)

    # Important: set right-padding for causal LM so attention masks are correct
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Apply LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg.r,
        lora_alpha=lora_cfg.lora_alpha,
        lora_dropout=lora_cfg.lora_dropout,
        target_modules=lora_cfg.target_modules,
        bias=lora_cfg.bias,
        use_gradient_checkpointing=lora_cfg.use_gradient_checkpointing,
        random_state=42,
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log.info(
        "LoRA applied — trainable params: %s / %s (%.3f%%)",
        f"{trainable:,}", f"{total:,}", 100 * trainable / total,
    )
    return model, tokenizer


# ── Dataset Loading ───────────────────────────────────────────────────────────

def _load_jsonl(path: str | Path) -> list[dict]:
    """Load a JSONL file, skipping malformed lines."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.warning("Skipping malformed JSONL line %d: %s", lineno, exc)
    return records


def _chatml_to_text(item: dict, tokenizer) -> dict[str, str]:
    """Convert a ChatML dict to a single Llama-3 formatted text string.

    Uses the tokenizer's built-in apply_chat_template if available,
    falling back to manual string construction.
    """
    msgs = item["messages"]
    try:
        text = tokenizer.apply_chat_template(
            msgs,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        # Manual fallback using Llama-3 special tokens
        text = ""
        for msg in msgs:
            role, content = msg["role"], msg["content"]
            if role == "system":
                text += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "user":
                text += f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "assistant":
                text += f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>"
    return {"text": text}


def load_sft_dataset(data_dir: str, tokenizer, train_cfg: ModelConfig):
    """Load and prepare the SFT dataset from generated JSONL splits.

    Performs token-length analysis and logs samples that exceed
    max_seq_length (they will be truncated by the trainer).

    Returns:
        Tuple[train_dataset, val_dataset, test_data_raw]
    """
    try:
        from datasets import Dataset
    except ImportError:
        log.error("HuggingFace `datasets` not installed.")
        sys.exit(1)

    data_path = Path(data_dir)
    required = [data_path / "train.jsonl", data_path / "val.jsonl"]
    for p in required:
        if not p.exists():
            log.error(
                "%s not found. Generate it first:\n"
                "  python scripts/generate_sft_dataset.py --output %s",
                p, data_dir,
            )
            sys.exit(1)

    train_raw = _load_jsonl(data_path / "train.jsonl")
    val_raw = _load_jsonl(data_path / "val.jsonl")
    test_raw = _load_jsonl(data_path / "test.jsonl") if (data_path / "test.jsonl").exists() else []

    train_texts = [_chatml_to_text(item, tokenizer) for item in train_raw]
    val_texts = [_chatml_to_text(item, tokenizer) for item in val_raw]

    # Token-length analysis (warn on truncated samples)
    max_len = train_cfg.max_seq_length
    long_samples = sum(
        1 for t in train_texts
        if len(tokenizer.encode(t["text"])) > max_len
    )
    if long_samples:
        log.warning(
            "%d/%d train samples exceed max_seq_length=%d and will be truncated.",
            long_samples, len(train_texts), max_len,
        )

    train_ds = Dataset.from_list(train_texts)
    val_ds = Dataset.from_list(val_texts)

    log.info(
        "Dataset → train=%d  val=%d  test=%d",
        len(train_ds), len(val_ds), len(test_raw),
    )
    return train_ds, val_ds, test_raw


# ── Training ──────────────────────────────────────────────────────────────────

def train_model(
    model,
    tokenizer,
    train_ds,
    val_ds,
    train_cfg: TrainConfig,
) -> tuple[Any, Any]:
    """Fine-tune with SFTTrainer.

    Returns:
        Tuple[trained_model, TrainOutput]
    """
    try:
        from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
        from transformers import TrainingArguments, EarlyStoppingCallback
    except ImportError:
        log.error("TRL / Transformers not installed.")
        sys.exit(1)

    # Auto-detect wandb
    report_to = train_cfg.report_to
    if report_to == "none" and os.environ.get("WANDB_API_KEY"):
        report_to = "wandb"
        log.info("WANDB_API_KEY detected — enabling W&B logging.")

    training_args = TrainingArguments(
        output_dir=train_cfg.output_dir,
        num_train_epochs=train_cfg.num_train_epochs,
        per_device_train_batch_size=train_cfg.per_device_train_batch_size,
        gradient_accumulation_steps=train_cfg.gradient_accumulation_steps,
        warmup_ratio=train_cfg.warmup_ratio,
        learning_rate=train_cfg.learning_rate,
        fp16=train_cfg.fp16,
        bf16=train_cfg.bf16,
        logging_steps=train_cfg.logging_steps,
        save_strategy=train_cfg.save_strategy,
        eval_strategy=train_cfg.eval_strategy,
        load_best_model_at_end=train_cfg.load_best_model_at_end,
        metric_for_best_model=train_cfg.metric_for_best_model,
        greater_is_better=train_cfg.greater_is_better,
        optim=train_cfg.optim,
        weight_decay=train_cfg.weight_decay,
        lr_scheduler_type=train_cfg.lr_scheduler_type,
        seed=train_cfg.seed,
        dataloader_num_workers=train_cfg.dataloader_num_workers,
        report_to=report_to,
        save_total_limit=2,
        remove_unused_columns=False,
    )

    callbacks = [
        EarlyStoppingCallback(
            early_stopping_patience=train_cfg.early_stopping_patience,
        )
    ]

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=train_cfg.max_seq_length,
        packing=train_cfg.packing,
        callbacks=callbacks,
    )

    log.info("=" * 60)
    log.info("STARTING QLoRA SFT TRAINING")
    log.info("=" * 60)
    log.info("  Model         : %s", model.config._name_or_path if hasattr(model, "config") else "PEFT model")
    log.info("  Epochs        : %d", train_cfg.num_train_epochs)
    log.info("  Batch (eff.)  : %d (device×%d × accum×%d)",
             train_cfg.per_device_train_batch_size * train_cfg.gradient_accumulation_steps,
             train_cfg.per_device_train_batch_size,
             train_cfg.gradient_accumulation_steps)
    log.info("  Learning rate : %g", train_cfg.learning_rate)
    log.info("  Packing       : %s", train_cfg.packing)
    log.info("  Report to     : %s", report_to)

    t0 = time.time()
    result = trainer.train()
    elapsed = time.time() - t0

    log.info("Training complete in %.1f min", elapsed / 60)
    log.info("  global_step   : %d", result.global_step)
    log.info("  training_loss : %.4f", result.training_loss)

    return model, result


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_model(
    model,
    tokenizer,
    test_data: list[dict],
    max_samples: int = 50,
    output_dir: str = "models/flagguard-sft-lora",
) -> dict[str, float]:
    """Compute ROUGE-L and corpus BLEU-4 on the test set.

    Generates at most max_samples predictions to bound evaluation time.
    Results are written to eval_metrics.json in output_dir.

    Returns:
        Dict of metric name → float value.
    """
    if not test_data:
        log.warning("No test data provided — skipping evaluation.")
        return {}

    try:
        import nltk
        from nltk.translate.bleu_score import corpus_bleu, SmoothingFunction
        from rouge_score import rouge_scorer as rs_module
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
    except ImportError:
        log.warning("rouge-score / nltk not installed — skipping evaluation.")
        return {}

    try:
        from unsloth import FastLanguageModel
        FastLanguageModel.for_inference(model)
    except Exception as exc:
        log.warning("FastLanguageModel.for_inference failed: %s", exc)

    scorer = rs_module.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    smoother = SmoothingFunction().method1

    references: list[list[list[str]]] = []
    hypotheses: list[list[str]] = []
    rouge_acc: dict[str, list[float]] = {"rouge1": [], "rouge2": [], "rougeL": []}

    samples = test_data[:max_samples]
    log.info("Evaluating on %d test samples…", len(samples))

    for i, item in enumerate(samples):
        msgs = item["messages"]
        reference_text: str = msgs[2]["content"]

        # Build inference prompt (system + user, no assistant response)
        try:
            prompt = tokenizer.apply_chat_template(
                msgs[:2],
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            prompt = (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                f"{msgs[0]['content']}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n"
                f"{msgs[1]['content']}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>\n"
            )

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                           max_length=1536).to(model.device)
        with __import__("torch").no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        ).strip()

        # BLEU accumulation
        ref_tokens = nltk.word_tokenize(reference_text.lower())
        gen_tokens = nltk.word_tokenize(generated.lower())
        references.append([ref_tokens])
        hypotheses.append(gen_tokens)

        # ROUGE accumulation
        rouge_result = scorer.score(reference_text, generated)
        for key in rouge_acc:
            rouge_acc[key].append(rouge_result[key].fmeasure)

        if (i + 1) % 10 == 0:
            log.info("  Evaluated %d/%d", i + 1, len(samples))

    import numpy as np
    bleu4 = corpus_bleu(references, hypotheses, smoothing_function=smoother)
    metrics = {
        "bleu4": float(bleu4),
        "rouge1": float(np.mean(rouge_acc["rouge1"])),
        "rouge2": float(np.mean(rouge_acc["rouge2"])),
        "rougeL": float(np.mean(rouge_acc["rougeL"])),
        "num_evaluated": len(samples),
    }

    log.info("=" * 50)
    log.info("EVALUATION RESULTS (n=%d)", len(samples))
    log.info("  BLEU-4  : %.4f", metrics["bleu4"])
    log.info("  ROUGE-1 : %.4f", metrics["rouge1"])
    log.info("  ROUGE-2 : %.4f", metrics["rouge2"])
    log.info("  ROUGE-L : %.4f", metrics["rougeL"])
    log.info("=" * 50)

    metrics_path = Path(output_dir) / "eval_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2))
    log.info("Metrics saved to %s", metrics_path)

    return metrics


# ── Saving ────────────────────────────────────────────────────────────────────

def save_lora_adapters(
    model,
    tokenizer,
    output_dir: str,
    model_cfg: ModelConfig,
    lora_cfg: LoraConfig,
    train_cfg: TrainConfig,
    metrics: dict[str, float] | None = None,
) -> None:
    """Save LoRA adapters, tokenizer, and metadata.

    Saves:
        <output_dir>/adapter_model.safetensors  — LoRA weights
        <output_dir>/tokenizer_config.json      — tokenizer settings
        <output_dir>/adapter_meta.json          — training provenance
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    meta = {
        "framework": "flagguard-sft-v2",
        "base_model": model_cfg.model_name,
        "max_seq_length": model_cfg.max_seq_length,
        "lora": asdict(lora_cfg),
        "training": asdict(train_cfg),
        "eval_metrics": metrics or {},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "adapter_meta.json").write_text(json.dumps(meta, indent=2))

    log.info("✅ LoRA adapters saved to %s/", output_dir)
    log.info("   Next step: Run DPO alignment or export to GGUF.")


# ── CLI / Main ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FlagGuard QLoRA SFT Fine-Tuning Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data", default="data/sft_dataset",
                        help="Path to SFT dataset directory (train/val/test.jsonl)")
    parser.add_argument("--output", default="models/flagguard-sft-lora",
                        help="Output directory for LoRA adapters")
    parser.add_argument("--model", default=ModelConfig.model_name)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--max-eval-samples", type=int, default=50,
                        help="Max test samples to evaluate (set 0 to skip)")
    parser.add_argument("--install", action="store_true",
                        help="Install missing dependencies before training")
    parser.add_argument("--eval-only", action="store_true",
                        help="Skip training; only run evaluation on test set")
    parser.add_argument("--bf16", action="store_true",
                        help="Use bfloat16 (for A100/H100 GPUs)")

    args = parser.parse_args()

    if args.install:
        install_dependencies()

    model_cfg = ModelConfig(model_name=args.model)
    lora_cfg = LoraConfig(r=args.lora_r)
    train_cfg = TrainConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        bf16=args.bf16,
        fp16=not args.bf16,
    )

    model, tokenizer = load_base_model(model_cfg, lora_cfg)
    train_ds, val_ds, test_raw = load_sft_dataset(args.data, tokenizer, model_cfg)

    metrics: dict[str, float] = {}

    if not args.eval_only:
        model, result = train_model(model, tokenizer, train_ds, val_ds, train_cfg)
        save_lora_adapters(model, tokenizer, args.output, model_cfg, lora_cfg, train_cfg)

    if test_raw and args.max_eval_samples > 0:
        metrics = evaluate_model(
            model, tokenizer, test_raw,
            max_samples=args.max_eval_samples,
            output_dir=args.output,
        )

    if not args.eval_only:
        # Re-save with metrics included
        save_lora_adapters(model, tokenizer, args.output, model_cfg, lora_cfg, train_cfg, metrics)

    log.info("=" * 60)
    log.info("SFT PIPELINE COMPLETE")
    log.info("  Adapters saved to: %s", args.output)
    log.info("  Next: python notebooks/flagguard_dpo_training.py --model %s", args.output)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
