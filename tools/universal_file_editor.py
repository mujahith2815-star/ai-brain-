"""
Universal All-Format File Viewer, Hex Dumper & Surgical Code Editor for P.H.A.S.S Sphere v5.0.
Provides unified viewing, editing, regex patching, CSV formatting, and binary inspection
across any file type in the host filesystem.
"""

from __future__ import annotations
import csv
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.tools.universal_file_editor")


@dataclass
class FileViewResult:
    file_path: str
    file_name: str
    file_extension: str
    mime_type: str
    file_size_bytes: int
    total_lines: int
    start_line: int
    end_line: int
    content: str
    sha256_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "total_lines": self.total_lines,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "sha256_hash": self.sha256_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class FileEditResult:
    file_path: str
    operation: str # "REPLACE_SUBSTRING", "REGEX_REPLACE", "WRITE_OVERWRITE", "APPEND_CONTENT"
    success: bool
    changes_made_count: int
    backup_file_path: Optional[str]
    message: str
    execution_time_sec: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "operation": self.operation,
            "success": self.success,
            "changes_made_count": self.changes_made_count,
            "backup_file_path": self.backup_file_path,
            "message": self.message,
            "execution_time_sec": round(self.execution_time_sec, 4),
            "timestamp": self.timestamp,
        }


class UniversalFileEditorSuite:
    def _compute_sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "0" * 64

    def view_file_content(
        self,
        file_path_str: str,
        start_line: int = 1,
        end_line: int = 60,
    ) -> FileViewResult:
        """
        Views lines of any source code, markdown, or text file with syntax line indexing.
        """
        p = Path(file_path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        mime, _ = mimetypes.guess_type(str(p))
        sha = self._compute_sha256(p)
        size = p.stat().st_size

        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
        except Exception:
            with open(p, "r", encoding="latin1", errors="ignore") as f:
                all_lines = f.readlines()

        total = len(all_lines)
        s = max(1, start_line)
        e = min(total, end_line) if total > 0 else 0

        sliced = all_lines[s - 1 : e] if total > 0 else []
        numbered_lines = [f"{s + i:4d} | {line.rstrip(chr(10))}" for i, line in enumerate(sliced)]
        content_str = "\n".join(numbered_lines)

        return FileViewResult(
            file_path=str(p),
            file_name=p.name,
            file_extension=p.suffix.lower() or ".txt",
            mime_type=mime or "text/plain",
            file_size_bytes=size,
            total_lines=total,
            start_line=s,
            end_line=e,
            content=content_str,
            sha256_hash=sha,
        )

    def generate_hex_dump(self, file_path_str: str, max_bytes: int = 256) -> str:
        """
        Generates a traditional hexadecimal dump for binary, image, or raw byte inspection.
        """
        p = Path(file_path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        with open(p, "rb") as f:
            data = f.read(max_bytes)

        lines = [f"=== HEX DUMP: {p.name} ({len(data)} / {p.stat().st_size} Bytes) ==="]
        for offset in range(0, len(data), 16):
            chunk = data[offset : offset + 16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(f"{offset:08X} | {hex_str:<48} | {ascii_str}")

        return "\n".join(lines)

    def view_csv_table_preview(self, file_path_str: str, max_rows: int = 15) -> str:
        """
        Parses and formats a CSV / TSV spreadsheet into a visual ASCII grid.
        """
        p = Path(file_path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        delimiter = "\t" if p.suffix.lower() == ".tsv" else ","
        rows = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)

        if not rows:
            return f"Empty CSV file: {p.name}"

        # Column width formatting
        col_widths = [max(len(str(r[c])) if c < len(r) else 0 for r in rows) for c in range(len(rows[0]))]
        col_widths = [max(4, min(30, w)) for w in col_widths]

        table_lines = [f"=== CSV TABLE PREVIEW: {p.name} (Showing top {len(rows)} rows) ==="]
        header = " | ".join(f"{str(rows[0][c]):<{col_widths[c]}}" for c in range(len(rows[0])))
        sep = "-+-".join("-" * w for w in col_widths)
        table_lines.append(header)
        table_lines.append(sep)

        for r in rows[1:]:
            line = " | ".join(f"{str(r[c]) if c < len(r) else '':<{col_widths[c]}}" for c in range(len(col_widths)))
            table_lines.append(line)

        return "\n".join(table_lines)

    def edit_file_replace(
        self,
        file_path_str: str,
        target_content: str,
        replacement_content: str,
        create_backup: bool = True,
    ) -> FileEditResult:
        """
        Surgically replaces targeted code blocks or strings within any file.
        """
        start_t = time.time()
        p = Path(file_path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        raw_text = p.read_text(encoding="utf-8", errors="ignore")
        if target_content not in raw_text:
            return FileEditResult(
                file_path=str(p),
                operation="REPLACE_SUBSTRING",
                success=False,
                changes_made_count=0,
                backup_file_path=None,
                message=f"Target content string not found inside '{p.name}'.",
                execution_time_sec=time.time() - start_t,
            )

        # Create backup
        backup_path = None
        if create_backup:
            backup_path = str(p) + ".bak"
            shutil.copy(str(p), backup_path)

        occurrences = raw_text.count(target_content)
        new_text = raw_text.replace(target_content, replacement_content)
        p.write_text(new_text, encoding="utf-8")

        dur = time.time() - start_t
        return FileEditResult(
            file_path=str(p),
            operation="REPLACE_SUBSTRING",
            success=True,
            changes_made_count=occurrences,
            backup_file_path=backup_path,
            message=f"Successfully replaced {occurrences} occurrence(s) in '{p.name}'.",
            execution_time_sec=dur,
        )

    def write_full_file(
        self,
        file_path_str: str,
        content: str,
        overwrite: bool = True,
    ) -> FileEditResult:
        """
        Creates or overwrites any file with the specified content.
        """
        start_t = time.time()
        p = Path(file_path_str).resolve()
        if p.exists() and not overwrite:
            return FileEditResult(
                file_path=str(p),
                operation="WRITE_OVERWRITE",
                success=False,
                changes_made_count=0,
                backup_file_path=None,
                message="File exists and overwrite is set to False.",
                execution_time_sec=time.time() - start_t,
            )

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

        return FileEditResult(
            file_path=str(p),
            operation="WRITE_OVERWRITE",
            success=True,
            changes_made_count=1,
            backup_file_path=None,
            message=f"File successfully written ({len(content)} characters) to '{p.name}'.",
            execution_time_sec=time.time() - start_t,
        )


universal_file_editor = UniversalFileEditorSuite()
