"""
PyInstaller Single-File Executable Packaging Script for Orvix Sphere.
Produces dist/orvix_sphere.exe with all templates, static assets, and configurations bundled.
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ensure_icon(assets_dir: Path) -> Path:
    """Ensure assets/orvix.ico exists, generating a fallback if needed."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    ico_path = assets_dir / "orvix.ico"
    if not ico_path.exists():
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (256, 256), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 248, 248], fill=(14, 20, 40, 255), outline=(0, 212, 255, 255), width=6)
            draw.ellipse([64, 64, 192, 192], fill=(0, 212, 255, 220), outline=(255, 255, 255, 255), width=3)
            img.save(str(ico_path), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print(f"[*] Created icon at: {ico_path}")
        except Exception as e:
            print(f"[!] Warning: Could not generate icon: {e}")
    return ico_path


def build_executable():
    start_time = time.time()
    print("=================================================================")
    print("         ORVIX SPHERE STANDALONE EXECUTABLE PACKAGER             ")
    print("=================================================================")

    base_dir = Path(__file__).parent.resolve()
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    assets_dir = base_dir / "assets"
    ico_path = ensure_icon(assets_dir)

    sep = ";" if os.name == "nt" else ":"

    # Data files to bundle inside the .exe
    data_args = [
        f"--add-data=web/templates{sep}web/templates",
        f"--add-data=web/static{sep}web/static",
        f"--add-data=config{sep}config",
        f"--add-data=proactive/triggers.json{sep}proactive",
        f"--add-data=mcp/servers{sep}mcp/servers",
        f"--add-data=knowledge/agent_memory.db{sep}knowledge",
    ]

    # Required hidden imports for dynamic imports
    hidden_imports = [
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=apscheduler",
        "--hidden-import=apscheduler.triggers.cron",
        "--hidden-import=apscheduler.triggers.interval",
        "--hidden-import=watchdog",
        "--hidden-import=watchdog.observers",
        "--hidden-import=sentence_transformers",
        "--hidden-import=transformers",
        "--hidden-import=torch",
        "--hidden-import=fastapi",
        "--hidden-import=jinja2",
        "--hidden-import=rich",
        "--hidden-import=psutil",
        "--hidden-import=sqlite3",
        "--hidden-import=mcp",
    ]

    # Packages needing full metadata and data collections
    collect_args = [
        "--collect-all=sentence_transformers",
        "--collect-all=tiktoken",
        "--collect-all=tokenizers",
    ]

    # Excluded heavy/irrelevant packages to optimize build size
    exclude_args = [
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide2",
        "--exclude-module=IPython",
        "--exclude-module=pytest",
        "--exclude-module=tests",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=orvix_sphere",
        "--onefile",
        "--console",
        f"--icon={ico_path}",
        "--noconfirm",
        
    ] + data_args + hidden_imports + collect_args + exclude_args + ["run_model_chat.py"]

    print("[*] Executing PyInstaller command (this may take several minutes)...")
    res = subprocess.run(cmd, cwd=str(base_dir))

    if res.returncode != 0:
        print(f"\n[!] Build failed with exit code: {res.returncode}")
        return False

    exe_name = "orvix_sphere.exe" if os.name == "nt" else "orvix_sphere"
    exe_path = dist_dir / exe_name

    if not exe_path.exists():
        print(f"\n[!] Error: Expected binary not found at {exe_path}")
        return False

    exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
    duration = time.time() - start_time
    print(f"\n[OK] Build Successful in {duration:.1f}s!")
    print(f"[OK] Executable: {exe_path} ({exe_size_mb:.2f} MB)")

    # Post-build distribution staging
    print("\n[*] Staging companion distribution files into dist/...")
    
    # 1. Knowledge database
    dist_knowledge = dist_dir / "knowledge"
    dist_knowledge.mkdir(parents=True, exist_ok=True)
    db_src = base_dir / "knowledge" / "agent_memory.db"
    if db_src.exists():
        shutil.copy2(db_src, dist_knowledge / "agent_memory.db")
        print("  [+] Copied knowledge/agent_memory.db -> dist/knowledge/")

    # 2. Environment config
    env_src = base_dir / ".env.example"
    if env_src.exists():
        shutil.copy2(env_src, dist_dir / ".env")
        print("  [+] Copied .env.example -> dist/.env")

    # 3. Documentation & License
    for doc in ["README.md", "LICENSE"]:
        doc_src = base_dir / doc
        if doc_src.exists():
            shutil.copy2(doc_src, dist_dir / doc)
            print(f"  [+] Copied {doc} -> dist/{doc}")

    # 4. Local Model (Optional portable bundling)
    models_src = base_dir / "models" / "llama"
    dist_models = dist_dir / "models" / "llama"
    if models_src.exists() and not dist_models.exists():
        print(f"  [*] Copying local model weights ({models_src}) -> dist/models/llama/...")
        try:
            shutil.copytree(models_src, dist_models)
            print("  [+] Local model successfully bundled for portable distribution.")
        except Exception as e:
            print(f"  [!] Note on model copy: {e}")
    elif dist_models.exists():
        print("  [+] dist/models/llama already present.")

    print("\n=================================================================")
    print("           ORVIX SPHERE STANDALONE PACKAGING COMPLETE            ")
    print("=================================================================")
    return True


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
