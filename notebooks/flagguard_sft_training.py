"""FlagGuard QLoRA SFT Fine-Tuning Pipeline (Phase 3 — Step 3.2).

Supervised Fine-Tuning of Llama-3.1-8B-Instruct using QLoRA (4-bit)
on the FlagGuard synthetic dataset. Designed to run on Google Colab
with a T4/A100 GPU.

Pipeline:
    1. Install dependencies (Unsloth, PEFT, TRL, bitsandbytes)
    2. Load base model with 4-bit quantization
    3. Apply LoRA adapters (r=16, alpha=32)
    4. Load SFT dataset from JSONL
    5. Train with SFTTrainer (TRL)
    6. Evaluate BLEU/ROUGE on test set
    7. Save LoRA adapters for merging

Usage (Google Colab):
    !python notebooks/flagguard_sft_training.py --data data/sft_dataset --epochs 3

Usage (Local with GPU):
    python notebooks/flagguard_sft_training.py --data data/sft_dataset --epochs 3

Skills demonstrated: QLoRA, PEFT, LoRA, HuggingFace Transformers, TRL, SFT, 4-bit Quantization.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CELL 1: Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Model configuration
BASE_MODEL = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
FALLBACK_MODEL = "unsloth/Llama-3.2-1B-Instruct-bnb-4bit"  # For low-VRAM GPUs

# LoRA configuration
LORA_CONFIG = {
    "r": 16,                    # LoRA rank
    "lora_alpha": 32,          # Scaling factor
    "lora_dropout": 0.05,       # Dropout for regularization
    "target_modules": [          # Modules to apply LoRA
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

# Training configuration
TRAINING_CONFIG = {
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,
    "warmup_steps": 50,
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "fp16": True,
    "logging_steps": 10,
    "save_strategy": "epoch",
    "evaluation_strategy": "epoch",
    "optim": "adamw_8bit",
    "weight_decay": 0.01,
    "lr_scheduler_type": "cosine",
    "seed": 42,
    "output_dir": "models/flagguard-sft-lora",
    "report_to": "none",
}


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 2: Install Dependencies (for Colab)
# ═══════════════════════════════════════════════════════════════════════════════

def install_dependencies():
    """Install required packages (for Google Colab environment)."""
    try:
        import unsloth  # noqa: F401
        print("✅ Unsloth already installed.")
    except ImportError:
        print("Installing Unsloth + dependencies...")
        os.system(
            'pip install -q "unsloth[colab-new]" '
            '"trl>=0.7.0" "peft>=0.7.0" "transformers>=4.36.0" '
            '"bitsandbytes>=0.41.0" "accelerate>=0.25.0" '
            '"datasets>=2.16.0" "rouge-score" "nltk"'
        )
        print("✅ Dependencies installed.")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 3: Load Model with QLoRA
# ═══════════════════════════════════════════════════════════════════════════════

def load_model_and_tokenizer(model_name: str = BASE_MODEL):
    """Load the base model with 4-bit quantization and apply LoRA.

    Args:
        model_name: HuggingFace model identifier.

    Returns:
        Tuple of (model, tokenizer) with LoRA applied.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: Unsloth not installed. Run install_dependencies() first.")
        sys.exit(1)

    print(f"Loading model: {model_name}")

    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=2048,
            dtype=None,  # Auto-detect (float16 for T4, bfloat16 for A100)
            load_in_4bit=True,
        )
    except Exception as e:
        print(f"Failed to load {model_name}: {e}")
        print(f"Falling back to smaller model: {FALLBACK_MODEL}")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=FALLBACK_MODEL,
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
        )

    # Apply LoRA adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_CONFIG["r"],
        lora_alpha=LORA_CONFIG["lora_alpha"],
        lora_dropout=LORA_CONFIG["lora_dropout"],
        target_modules=LORA_CONFIG["target_modules"],
        bias=LORA_CONFIG["bias"],
    )

    # Print trainable parameter stats
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    return model, tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 4: Load and Prepare Dataset
# ═══════════════════════════════════════════════════════════════════════════════

def load_sft_dataset(data_dir: str, tokenizer):
    """Load the SFT dataset from JSONL files.

    Args:
        data_dir: Directory containing train.jsonl, val.jsonl, test.jsonl.
        tokenizer: The tokenizer to use for formatting.

    Returns:
        Tuple of (train_dataset, val_dataset, test_data_raw).
    """
    from datasets import Dataset

    def load_jsonl(path):
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    train_path = os.path.join(data_dir, "train.jsonl")
    val_path = os.path.join(data_dir, "val.jsonl")
    test_path = os.path.join(data_dir, "test.jsonl")

    for p in [train_path, val_path]:
        if not Path(p).exists():
            print(f"ERROR: {p} not found. Run: python scripts/generate_sft_dataset.py")
            sys.exit(1)

    train_raw = load_jsonl(train_path)
    val_raw = load_jsonl(val_path)
    test_raw = load_jsonl(test_path) if Path(test_path).exists() else []

    def format_example(item):
        """Convert ChatML messages to a single text string for SFT."""
        msgs = item["messages"]
        formatted = ""
        for msg in msgs:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "user":
                formatted += f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "assistant":
                formatted += f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>"
        return {"text": formatted}

    train_data = [format_example(item) for item in train_raw]
    val_data = [format_example(item) for item in val_raw]

    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)

    print(f"Dataset loaded: {len(train_dataset)} train / {len(val_dataset)} val / {len(test_raw)} test")
    return train_dataset, val_dataset, test_raw


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 5: Train with SFTTrainer
# ═══════════════════════════════════════════════════════════════════════════════

def train_model(model, tokenizer, train_dataset, val_dataset, config: dict):
    """Fine-tune the model using SFTTrainer from TRL.

    Args:
        model: The PEFT model with LoRA adapters.
        tokenizer: The tokenizer.
        train_dataset: Training dataset.
        val_dataset: Validation dataset.
        config: Training hyperparameters.

    Returns:
        The trained model and training results.
    """
    from trl import SFTTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(**config)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=2048,
        packing=True,  # Pack short sequences for efficiency
    )

    print("\n" + "=" * 60)
    print("STARTING QLoRA SFT TRAINING")
    print("=" * 60)
    print(f"Epochs: {config['num_train_epochs']}")
    print(f"Batch size: {config['per_device_train_batch_size']} × {config['gradient_accumulation_steps']} grad accum")
    print(f"Learning rate: {config['learning_rate']}")
    print(f"LoRA rank: {LORA_CONFIG['r']}, alpha: {LORA_CONFIG['lora_alpha']}")

    results = trainer.train()

    print(f"\n✅ Training complete!")
    print(f"   Total steps: {results.global_step}")
    print(f"   Final loss: {results.training_loss:.4f}")

    return model, results


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 6: Evaluate on Test Set (BLEU/ROUGE)
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_model(model, tokenizer, test_data: list[dict], max_samples: int = 50):
    """Evaluate the fine-tuned model using BLEU and ROUGE metrics.

    Args:
        model: The fine-tuned model.
        tokenizer: The tokenizer.
        test_data: List of raw test examples (ChatML format).
        max_samples: Maximum number of test samples to evaluate.

    Returns:
        Dictionary of evaluation metrics.
    """
    try:
        import nltk
        from rouge_score import rouge_scorer
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
    except ImportError:
        print("⚠️ rouge-score/nltk not installed. Skipping evaluation.")
        return {}

    from unsloth import FastLanguageModel

    FastLanguageModel.for_inference(model)

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    bleu_scores = []
    rouge_scores = {"rouge1": [], "rouge2": [], "rougeL": []}

    samples = test_data[:max_samples]
    print(f"\nEvaluating on {len(samples)} test samples...")

    for i, item in enumerate(samples):
        # Extract reference and prompt
        msgs = item["messages"]
        reference = msgs[2]["content"]  # Assistant response

        # Build prompt (system + user only)
        prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"{msgs[0]['content']}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n"
            f"{msgs[1]['content']}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n"
        )

        # Generate
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.3,
            do_sample=True,
            top_p=0.9,
        )
        generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        # BLEU
        ref_tokens = nltk.word_tokenize(reference.lower())
        gen_tokens = nltk.word_tokenize(generated.lower())
        try:
            bleu = nltk.translate.bleu_score.sentence_bleu([ref_tokens], gen_tokens)
        except Exception:
            bleu = 0.0
        bleu_scores.append(bleu)

        # ROUGE
        rouge_result = scorer.score(reference, generated)
        for key in rouge_scores:
            rouge_scores[key].append(rouge_result[key].fmeasure)

        if (i + 1) % 10 == 0:
            print(f"  Evaluated {i + 1}/{len(samples)}")

    # Aggregate
    import numpy as np
    metrics = {
        "bleu": float(np.mean(bleu_scores)),
        "rouge1": float(np.mean(rouge_scores["rouge1"])),
        "rouge2": float(np.mean(rouge_scores["rouge2"])),
        "rougeL": float(np.mean(rouge_scores["rougeL"])),
    }

    print(f"\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"BLEU:    {metrics['bleu']:.4f}")
    print(f"ROUGE-1: {metrics['rouge1']:.4f}")
    print(f"ROUGE-2: {metrics['rouge2']:.4f}")
    print(f"ROUGE-L: {metrics['rougeL']:.4f}")

    # Save metrics
    metrics_path = os.path.join(TRAINING_CONFIG["output_dir"], "eval_metrics.json")
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nMetrics saved to {metrics_path}")

    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 7: Save LoRA Adapters
# ═══════════════════════════════════════════════════════════════════════════════

def save_lora_adapters(model, tokenizer, output_dir: str = "models/flagguard-sft-lora"):
    """Save the LoRA adapters for later merging.

    Args:
        model: The fine-tuned PEFT model.
        tokenizer: The tokenizer.
        output_dir: Directory to save adapters.
    """
    os.makedirs(output_dir, exist_ok=True)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save training metadata
    meta = {
        "base_model": BASE_MODEL,
        "lora_config": LORA_CONFIG,
        "training_config": {k: str(v) for k, v in TRAINING_CONFIG.items()},
        "version": "1.0.0",
        "description": "FlagGuard SFT LoRA adapters for conflict resolution",
    }
    with open(os.path.join(output_dir, "adapter_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ LoRA adapters saved to {output_dir}/")
    print(f"   Next: Merge + quantize with llama.cpp or run DPO alignment.")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 8: Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="FlagGuard QLoRA SFT Fine-Tuning Pipeline"
    )
    parser.add_argument("--data", type=str, default="data/sft_dataset")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--model", type=str, default=BASE_MODEL)
    parser.add_argument("--output", type=str, default="models/flagguard-sft-lora")
    parser.add_argument("--install", action="store_true", help="Install dependencies first")
    parser.add_argument("--eval-only", action="store_true", help="Only evaluate, don't train")

    args = parser.parse_args()

    if args.install:
        install_dependencies()

    # Update config
    TRAINING_CONFIG["num_train_epochs"] = args.epochs
    TRAINING_CONFIG["output_dir"] = args.output

    # Load model
    model, tokenizer = load_model_and_tokenizer(args.model)

    # Load dataset
    train_dataset, val_dataset, test_raw = load_sft_dataset(args.data, tokenizer)

    if not args.eval_only:
        # Train
        model, results = train_model(model, tokenizer, train_dataset, val_dataset, TRAINING_CONFIG)

        # Save adapters
        save_lora_adapters(model, tokenizer, args.output)

    # Evaluate
    if test_raw:
        evaluate_model(model, tokenizer, test_raw)

    print("\n" + "=" * 60)
    print("SFT PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
