"""
Terminal Downloader for Local Llama Models in P.H.A.S.S Sphere.
Downloads Llama model weights from Hugging Face locally onto disk without using Ollama software.

Usage in terminal:
    python tools/download_llama.py
    python tools/download_llama.py --model unsloth/Llama-3.2-1B-Instruct --dest models/llama
"""

import argparse
import os
import sys
from pathlib import Path


def download_model(model_id: str, dest_dir: str):
    print("=" * 65)
    print("       P.H.A.S.S SPHERE — LOCAL LLAMA MODEL TERMINAL DOWNLOADER      ")
    print("=" * 65)
    print(f"[*] Target Model: {model_id}")
    print(f"[*] Destination:  {os.path.abspath(dest_dir)}")
    print("[*] Runtime:      Pure Python / Hugging Face (No Ollama Software Required)")
    print("-" * 65)

    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download

        print("\n[*] Starting local download of model weights and tokenizer...")
        local_dir = snapshot_download(
            repo_id=model_id,
            local_dir=str(dest_path),
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
        )
        print(f"\n[+] SUCCESS: Model files downloaded locally to:\n    {local_dir}")
        print("\n[*] You can now use this model in P.H.A.S.S by setting:")
        print(f"    $env:LLAMA_LOCAL_DIR='{dest_path}'")
        print("    python run_model_chat.py\n")
    except Exception as e:
        print(f"\n[!] Error downloading model: {e}")
        print("[!] Tip: Ensure you have an internet connection and sufficient disk space.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download Llama model locally to disk.")
    parser.add_argument(
        "--model",
        type=str,
        default="unsloth/Llama-3.2-1B-Instruct",
        help="Hugging Face repo ID or model name (default: unsloth/Llama-3.2-1B-Instruct)",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default="models/llama",
        help="Local destination folder (default: models/llama)",
    )
    args = parser.parse_args()
    download_model(args.model, args.dest)


if __name__ == "__main__":
    main()
