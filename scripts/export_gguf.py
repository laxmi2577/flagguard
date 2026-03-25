"""Ollama Modelfile Builder & Exporter (Phase 3 — Step 3.5).

This script generates an Ollama Modelfile and optionally calls llama.cpp
scripts to merge LoRA adapters and convert to 4-bit GGUF format for local deployment.

Usage:
    python scripts/export_gguf.py --model models/flagguard-dpo-lora
    ollama create flagguard-coder -f models/Modelfile
"""

import argparse
import os

def create_modelfile(output_path: str = "models/Modelfile", gguf_path: str = "flagguard-coder-Q4_K_M.gguf"):
    """Create the Ollama Modelfile."""
    modelfile_content = f"""FROM ./{gguf_path}

# Set context window and sampling parameters
PARAMETER num_ctx 4096
PARAMETER temperature 0.3
PARAMETER top_p 0.9

# ChatML format template
TEMPLATE \"\"\"<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{{{ .System }}}}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{{{ .Prompt }}}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

\"\"\"

# Base system prompt
SYSTEM \"\"\"You are FlagGuard-Coder, an expert AI assistant specializing in feature flag conflict resolution, code remediation, and risk assessment. You analyze code using formal verification (Z3 SAT solver), knowledge graphs, and SHAP-based risk prediction. Always be precise, cite specific functions/files, and provide actionable fixes in unified diff format when applicable.\"\"\"
"""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(modelfile_content)
    
    print(f"✅ Created Ollama Modelfile at {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export GGUF and generate Modelfile")
    parser.add_argument("--lora-dir", type=str, default="models/flagguard-dpo-lora")
    parser.add_argument("--output-modelfile", type=str, default="models/Modelfile")
    parser.add_argument("--gguf-name", type=str, default="flagguard-coder-Q4_K_M.gguf")
    
    args = parser.parse_args()
    
    print("Step 1: Generating Ollama Modelfile...")
    create_modelfile(args.output_modelfile, args.gguf_name)
    
    print("\nNext Steps for Deployment:")
    print("1. Merge LoRA adapters using unsloth/llama.cpp (typically run via notebook on Colab):")
    print("   model.save_pretrained_gguf('models', tokenizer, quantization_method='q4_k_m')")
    print("2. Create the Ollama model locally:")
    print("   ollama create flagguard-coder -f models/Modelfile")
    print("3. FlagGuard will automatically use 'flagguard-coder' when available.")

if __name__ == "__main__":
    main()
