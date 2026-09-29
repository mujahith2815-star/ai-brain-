import sys
sys.path.insert(0, ".")
import tempfile
from pathlib import Path

print("A. About to import RollbackManager...", flush=True)
from core.rollback_manager import RollbackManager
print("B. Imported RollbackManager!", flush=True)
from core.fix_generator import GeneratedFix
print("C. Imported GeneratedFix!", flush=True)

tmp = Path(tempfile.mkdtemp())
backups_dir = tmp / "checkpoints" / "backups"
metrics_file = tmp / "checkpoints" / "immunity_metrics.json"

print("1. Initializing RollbackManager...", flush=True)
manager = RollbackManager(backup_dir=backups_dir, metrics_file=metrics_file)
print("1b. Initialized RollbackManager!", flush=True)

print("2. Creating target file...", flush=True)
target_file = tmp / "service_worker.py"
original_content = "# Version 1.0 Live Code\ndef work():\n    return 'original'\n"
target_file.write_text(original_content, encoding="utf-8")
print("2b. Created target file!", flush=True)

print("3. Backing up file...", flush=True)
bak_path = manager.backup_file(target_file)
print(f"3b. Backup created: {bak_path}", flush=True)

print("4. Deploying fix...", flush=True)
hotfix = GeneratedFix(
    target_file=str(target_file),
    target_line=2,
    error_type="NameError",
    error_msg="fixed worker",
    fix_type="HOTFIX",
    repaired_code="# Version 1.1 Hotfixed Code\ndef work():\n    return 'hotfixed'\n",
    original_code=original_content,
    confidence=0.92,
    escalate_to_user=False,
    status="READY_FOR_SANDBOX",
    explanation="Patched worker function",
)
dep_res = manager.deploy_fix(hotfix, restart_service_if_needed=False)
print(f"4b. Deployment result: {dep_res.success}", flush=True)

print("5. Triggering rollback...", flush=True)
rollback_ok = manager.trigger_rollback(target_file, reason="Crash in work() function")
print(f"5b. Rollback result: {rollback_ok}", flush=True)
print("ALL DONE!", flush=True)
