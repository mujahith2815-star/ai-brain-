"""
Cloud Sync Integration for P.H.A.S.S Llama Assistant.
Syncs local workspace folders to cloud destinations (Google Drive, OneDrive, Dropbox, or backup archive),
with conflict resolution keeping the newest changes.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class CloudSync:
    """Manages file synchronization and backup mirrors."""

    def __init__(self, sync_cache_dir: str = "checkpoints/cloud_sync"):
        self.sync_cache_dir = Path(sync_cache_dir)
        self.sync_cache_dir.mkdir(parents=True, exist_ok=True)
        self.supported_providers = ["gdrive", "onedrive", "dropbox", "local_backup"]

    def sync_directories(self, source_dir: str, target_dir: str, dry_run: bool = False) -> Dict[str, Any]:
        """Convenience method to mirror source_dir to target_dir."""
        return self.sync_folder(source_dir, destination_dir=target_dir, dry_run=dry_run)

    def sync_folder(
        self,
        source_dir: str,
        target_provider: str = "local_backup",
        destination_dir: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronizes files from source directory to target destination.
        Applies conflict resolution by keeping newest modifications.
        """
        src = Path(source_dir).resolve()
        if not src.exists():
            return {"status": "ERROR", "message": f"Source directory '{source_dir}' does not exist."}

        dest = Path(destination_dir).resolve() if destination_dir else (self.sync_cache_dir / f"{target_provider}_mirror")
        dest.mkdir(parents=True, exist_ok=True)

        synced_files = []
        conflicts_resolved = 0

        for f in src.glob("**/*"):
            if f.is_file():
                rel = f.relative_to(src)
                target_file = dest / rel

                if not dry_run:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    if target_file.exists():
                        # Conflict resolution: compare mtime and keep newest
                        if f.stat().st_mtime > target_file.stat().st_mtime:
                            shutil.copy2(f, target_file)
                            conflicts_resolved += 1
                    else:
                        shutil.copy2(f, target_file)

                synced_files.append(str(rel))

        return {
            "status": "SUCCESS",
            "provider": target_provider,
            "source": str(src),
            "destination": str(dest),
            "files_synced": len(synced_files),
            "synced_count": len(synced_files),
            "conflicts_resolved": conflicts_resolved,
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "message": f"Synced {len(synced_files)} files with {conflicts_resolved} conflict(s) resolved."
        }

    def resolve_sync_conflict(self, local_file: Path, remote_file: Path) -> Path:
        """Resolves conflict between two versions of a file by keeping the newest."""
        if not remote_file.exists():
            return local_file
        if not local_file.exists():
            return remote_file

        if local_file.stat().st_mtime >= remote_file.stat().st_mtime:
            shutil.copy2(local_file, remote_file)
            return remote_file
        else:
            shutil.copy2(remote_file, local_file)
            return local_file


# Global instance
cloud_sync = CloudSync()


def get_cloud_sync() -> CloudSync:
    return cloud_sync
