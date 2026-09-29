import os
import glob
import shutil
from datetime import datetime, timedelta

def delete_unwanted_files(
    directory: str,
    pattern: str = None,
    older_than_days: int = None,
    extensions: list = None,
    include_subfolders: bool = True,
    dry_run: bool = True
) -> dict:
    """
    Safely delete unwanted files with multiple filters.
    
    Args:
        directory: The folder to search in.
        pattern: File name pattern (e.g., "temp_*", "*.log").
        older_than_days: Delete files older than this many days.
        extensions: List of extensions to target (e.g., ['.tmp', '.log']).
        include_subfolders: Whether to search recursively.
        dry_run: If True, only show what would be deleted (safe mode).
    
    Returns:
        dict with status, deleted_count, file_list, freed_space.
    """
    result = {
        "status": "SUCCESS",
        "deleted_count": 0,
        "file_list": [],
        "freed_space_mb": 0,
        "errors": []
    }
    
    # Validate directory exists
    if not os.path.isdir(directory):
        result["status"] = "FAILED"
        result["errors"].append(f"Directory does not exist: {directory}")
        return result
    
    # Build search pattern
    search_pattern = pattern or "*"
    if extensions:
        # Build pattern like "*.tmp|*.log" if not already specified
        if not pattern:
            search_pattern = "|".join([f"*{ext}" for ext in extensions])
    
    # Collect files
    files_to_delete = []
    total_size = 0
    
    # Use glob recursively
    if include_subfolders:
        search_path = os.path.join(directory, "**", search_pattern)
    else:
        search_path = os.path.join(directory, search_pattern)
    
    for file_path in glob.glob(search_path, recursive=include_subfolders):
        if not os.path.isfile(file_path):
            continue
            
        # Check extensions (if provided)
        if extensions:
            if not any(file_path.endswith(ext) for ext in extensions):
                continue
                
        # Check age (if provided)
        if older_than_days:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            age_days = (datetime.now() - file_mtime).days
            if age_days < older_than_days:
                continue
        
        # Skip important system files (safety)
        skip_patterns = [
            "C:\\Windows", "C:\\Program Files", 
            "/etc", "/usr", "/bin", "/boot",
            ".git", "node_modules", "__pycache__"
        ]
        if any(skip in file_path for skip in skip_patterns):
            continue
            
        try:
            from core.platform_abstraction import get_platform
            if get_platform().is_system_protected_path(file_path):
                continue
        except Exception:
            pass
            
        # Collect file info
        size = os.path.getsize(file_path)
        total_size += size
        files_to_delete.append({
            "path": file_path,
            "size_mb": size / (1024 * 1024),
            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # If dry_run, just return the list
    if dry_run:
        result["file_list"] = files_to_delete
        result["freed_space_mb"] = round(total_size / (1024 * 1024), 2)
        result["deleted_count"] = len(files_to_delete)
        result["message"] = f"DRY RUN: Would delete {len(files_to_delete)} files ({result['freed_space_mb']:.2f} MB). Set dry_run=False to actually delete."
        return result
    
    # Actually delete files
    deleted_count = 0
    deleted_files = []
    for file_info in files_to_delete:
        try:
            os.remove(file_info["path"])
            deleted_count += 1
            deleted_files.append(file_info["path"])
        except Exception as e:
            result["errors"].append(f"Could not delete {file_info['path']}: {str(e)}")
    
    result["deleted_count"] = deleted_count
    result["file_list"] = deleted_files
    result["freed_space_mb"] = round(total_size / (1024 * 1024), 2)
    result["message"] = f"Deleted {deleted_count} files ({result['freed_space_mb']:.2f} MB freed)."
    
    return result
