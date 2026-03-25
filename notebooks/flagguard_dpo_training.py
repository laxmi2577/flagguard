"""FlagGuard DPO Alignment Pipeline (Phase 3 — Step 3.4).

Direct Preference Optimization (DPO) training to align the SFT model
with human preferences using the exported preference JSONL data.
Designed to run on Google Colab with a T4/A100 GPU.

Pipeline:
    1. Install dependencies (Unsloth, TRL, etc.)
    2. Load the SFT-trained model with LoRA adapters
    3. Load preference dataset (prompt, chosen, rejected)
    4. Train using trl.DPOTrainer
    5. Save final aligned adapters

Usage (Google Colab):
    !python notebooks/flagguard_dpo_training.py --data data/preference_data.jsonl

Skills demonstrated: DPO, RLHF, Preference Alignment, Unsloth, TRL.
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
BASE_MODEL = "models/flagguard-sft-lora"  # Path to the SFT model

# DPO Training configuration
TRAINING_CONFIG = {
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "warmup_steps": 50,
    "num_train_epochs": 2,
    "learning_rate": 5e-6,  # DPO uses much lower LR than SFT
    "fp16": True,
    "logging_steps": 10,
    "save_strategy": "epoch",
    "evaluation_strategy": "no",
    "optim": "adamw_8bit",
    "weight_decay": 0.01,
    "lr_scheduler_type": "cosine",
    "seed": 42,
    "output_dir": "models/flagguard-dpo-lora",
    "report_to": "none",
}

# DPO-specific config
DPO_CONFIG = {
    "beta": 0.1,  # Temperature parameter for DPO loss
    "max_length": 2048,
    "max_prompt_length": 1024,
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
            '"bitsandbytes>=0.41.0" "accelerate>=0.25.0" "datasets>=2.16.0"'
        )
        print("✅ Dependencies installed.")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 3: Load Model
# ═══════════════════════════════════════════════════════════════════════════════

def load_model_and_tokenizer(model_name: str = BASE_MODEL):
    """Load the SFT model with 4-bit quantization and LoRA.

    Args:
        model_name: Path or HF identifier for the base SFT model.

    Returns:
        Tuple of (model, tokenizer).
    """
    try:
        from unsloth import FastLanguageModel
        from peft import PeftModel
    except ImportError:
        print("ERROR: Unsloth/PEFT not installed. Run install_dependencies() first.")
        sys.exit(1)

    print(f"Loading SFT model: {model_name}")

    if not Path(model_name).exists():
        print(f"WARNING: {model_name} not found locally. Using base Llama-3.1-8B-Instruct.")
        model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"

    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=DPO_CONFIG["max_length"],
            dtype=None,
            load_in_4bit=True,
        )
    except Exception as e:
        print(f"Failed to load model: {e}")
        sys.exit(1)

    # Note: If model_name was a PEFT directory, FastLanguageModel loads it with adapters.
    # Otherwise, we need to apply new LoRA adapters for DPO training.
    # We apply LoRA adapters regardless to ensure they are trainable.
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
    )

    return model, tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 4: Load DPO Dataset
# ═══════════════════════════════════════════════════════════════════════════════

def load_dpo_dataset(data_path: str, tokenizer):
    """Load the preference dataset for DPO format.

    Args:
        data_path: Path to preference_data.jsonl.
        tokenizer: The tokenizer.

    Returns:
        HuggingFace Dataset ready for DPOTrainer.
    """
    from datasets import Dataset

    if not Path(data_path).exists():
        print(f"ERROR: {data_path} not found. Run: python scripts/export_preferences.py")
        sys.exit(1)

    raw_data = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            raw_data.append(json.loads(line))

    # Format for DPO Trainer: prompt, chosen, rejected
    formatted_data = []
    for item in raw_data:
        prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"You are FlagGuard-Coder, an expert AI assistant specializing in feature flag "
            f"conflict resolution.<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n"
            f"{item['prompt']}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n"
        )
        
        # Responses should not contain the prompt, only the completions
        chosen = f"{item['chosen']}<|eot_id|>"
        rejected = f"{item['rejected']}<|eot_id|>"

        formatted_data.append({
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
        })

    dataset = Dataset.from_list(formatted_data)
    print(f"Loaded {len(dataset)} preference pairs for DPO.")
    return dataset


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 5: Train with DPOTrainer
# ═══════════════════════════════════════════════════════════════════════════════

def train_dpo(model, tokenizer, dataset, config: dict):
    """Fine-tune using DPOTrainer.

    Args:
        model: The PEFT model.
        tokenizer: The tokenizer.
        dataset: HuggingFace dataset with prompt/chosen/rejected.
        config: Training arguments.
    """
    from trl import DPOTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(**config)

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # PEFT magically handles the reference model
        args=training_args,
        beta=DPO_CONFIG["beta"],
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_length=DPO_CONFIG["max_length"],
        max_prompt_length=DPO_CONFIG["max_prompt_length"],
    )

    print("\n" + "=" * 60)
    print("STARTING DPO ALIGNMENT TRAINING")
    print("=" * 60)

    results = trainer.train()

    print(f"\n✅ DPO Training complete!")
    print(f"   Final loss: {results.training_loss:.4f}")

    return model


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 6: Save Final Model
# ═══════════════════════════════════════════════════════════════════════════════

def save_aligned_model(model, tokenizer, output_dir: str):
    """Save the final DPO-aligned model adapters."""
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"\n✅ Aligned LoRA adapters saved to {output_dir}/")


# ═══════════════════════════════════════════════════════════════════════════════
# CELL 7: Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FlagGuard DPO Alignment")
    parser.add_argument("--data", type=str, default="data/preference_data.jsonl")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--model", type=str, default=BASE_MODEL)
    parser.add_argument("--output", type=str, default="models/flagguard-dpo-lora")
    parser.add_argument("--install", action="store_true")

    args = parser.parse_args()

    if args.install:
        install_dependencies()

    TRAINING_CONFIG["num_train_epochs"] = args.epochs
    TRAINING_CONFIG["output_dir"] = args.output

    model, tokenizer = load_model_and_tokenizer(args.model)
    dataset = load_dpo_dataset(args.data, tokenizer)
    
    model = train_dpo(model, tokenizer, dataset, TRAINING_CONFIG)
    save_aligned_model(model, tokenizer, args.output)

    print("\n" + "=" * 60)
    print("DPO PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
