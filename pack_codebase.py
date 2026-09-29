import os
import sys
from pathlib import Path

# Directories to include (ONLY the ones YOU wrote)
INCLUDE_DIRS = [
    "core", "tools", "nlp", "hardware", "security", 
    "clients", "ui", "integrations", "jarvis", "memory", 
    "neural", "vision", "voice", "world", "mesh"
]

# File extensions to include
EXTENSIONS = (".py",)

# Explicitly ignore these patterns
IGNORE_PATTERNS = [
    "__pycache__", ".venv", "dist", "build", 
    "checkpoints", "firmware/build", "sandbox", 
    "data_backups", "memory_vault", "projects", 
    "generated_apps", "overnight_logs", "neural_checkpoints",
    "*.pyc", "*.pyo", "*.so", "*.dll"
]

def should_ignore(path):
    for pattern in IGNORE_PATTERNS:
        if pattern in str(path):
            return True
    return False

def pack_codebase(output_file="P_H_A_S_S_FULL_CODEBASE.txt"):
    base_dir = Path(".")
    all_files = []
    
    for root_dir in INCLUDE_DIRS:
        target = base_dir / root_dir
        if not target.exists():
            print(f"⚠️ Skipping missing directory: {root_dir}")
            continue
        for file in target.rglob("*"):
            if file.is_file() and file.suffix in EXTENSIONS:
                if should_ignore(file):
                    continue
                all_files.append(file)
    
    # Sort files alphabetically
    all_files.sort()
    
    print(f"✅ Found {len(all_files)} source files to pack.")
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("=" * 80 + "\n")
        out.write(" P.H.A.S.S MASTER CODEBASE DUMP\n")
        out.write(f" Total Files: {len(all_files)}\n")
        out.write("=" * 80 + "\n\n")
        
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                out.write(f"\n\n{'#' * 80}\n")
                out.write(f"# FILE: {file_path}\n")
                out.write(f"# LINES: {len(content.splitlines())}\n")
                out.write(f"{'#' * 80}\n\n")
                out.write(content)
                out.write("\n")
            except Exception as e:
                out.write(f"\n\n# ERROR READING {file_path}: {e}\n\n")
    
    print(f"✅ Codebase packed to: {output_file}")
    print(f"📁 Size: {os.path.getsize(output_file) / 1024:.2f} KB")

if __name__ == "__main__":
    pack_codebase()