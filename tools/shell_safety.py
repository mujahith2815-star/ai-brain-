"""
Shell Safety Guard for Orvix Universal Control.
Validates commands against destructive patterns, classifies risk levels,
and prevents accidental or malicious catastrophic system actions.
"""

import re
from typing import Any, Dict, List, Tuple

# Patterns that are outright BLOCKED from automated execution
BLOCKED_PATTERNS: List[Tuple[str, str]] = [
    # Linux catastrophic
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+|\s+-rf\s+)\s*(\/|\/\*|~\/|~|\$HOME|\.\.)\b", "Catastrophic recursive deletion of root, home, or parent directory"),
    (r"\brm\s+-(?:r|rf|fr)\s+\/\s*$", "Catastrophic deletion of root directory"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:", "Fork bomb detected"),
    (r"\bmkfs(\.[a-zA-Z0-9]+)?\s+", "Filesystem formatting operation"),
    (r"\bdd\s+.*of=\/dev\/(sd[a-z]|nvme[0-9]n[0-9]|hd[a-z])", "Direct raw disk write with dd"),
    (r">\s*\/dev\/(sd[a-z]|nvme[0-9]n[0-9]|hd[a-z])", "Direct disk redirection overwrite"),
    (r"\bchmod\s+(-R\s+)?777\s+\/\b", "Insecure global permission wipe of root"),

    # Windows catastrophic
    (r"\bformat\s+[a-zA-Z]:", "Disk formatting command"),
    (r"\bClear-Disk\b", "PowerShell disk clearing"),
    (r"\bInitialize-Disk\b", "PowerShell disk initialization"),
    (r"\bRemove-Partition\b", "PowerShell partition removal"),
    (r"\bdiskpart\b", "Low-level disk partitioning tool"),
    (r"\bbcdedit\b", "Boot configuration data modification"),
    (r"\bdel\s+(\/[a-zA-Z]\s+)*[cC]:\\(windows|system32)?", "Deletion of critical Windows system directories"),
    (r"\brmdir\s+(\/[a-zA-Z]\s+)*[cC]:\\", "Removal of system root"),
    (r"\breg\s+delete\s+hk(lm|cr|u)\b", "Destructive registry key removal in HKLM/HKCR"),
]

# Patterns that require explicit human approval (CAUTION / DANGEROUS)
APPROVAL_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(shutdown|reboot|poweroff|halt)\b", "System shutdown or reboot"),
    (r"\b(Stop-Computer|Restart-Computer)\b", "PowerShell system shutdown or reboot"),
    (r"\b(userdel|Remove-LocalUser)\b", "User account deletion"),
    (r"\b(iptables\s+-F|ufw\s+reset)\b", "Flushing or resetting firewall rules"),
    (r"\b(netsh\s+advfirewall\s+reset)\b", "Resetting Windows firewall"),
    (r"\b(killall|pkill|Stop-Process)\s+-?(9|force)?\s*(lsass|csrss|winlogon|smss|svchost|systemd|init)", "Killing critical OS supervisor processes"),
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+)", "Recursive deletion"),
    (r"\bRemove-Item\s+.*-Recurse\b", "PowerShell recursive item deletion"),
]

# Known safe read-only commands
SAFE_PREFIXES = {
    "ls", "dir", "Get-ChildItem", "gci", "pwd", "Get-Location", "cat", "type", "Get-Content", "gc",
    "echo", "Write-Output", "grep", "Select-String", "findstr", "find", "where", "which", "Get-Command",
    "ps", "Get-Process", "gps", "netstat", "Get-NetTCPConnection", "ipconfig", "ifconfig", "ip",
    "ping", "Test-Connection", "curl", "Invoke-WebRequest", "wget", "uptime", "whoami", "hostname",
    "date", "Get-Date", "df", "du", "free", "lscpu", "lsblk", "uname", "head", "tail", "wc", "stat",
    "Get-Service", "gsv", "systemctl status", "git status", "git log", "git diff", "git branch",
}


class ShellSafety:
    """Validator and risk assessor for shell commands."""

    @staticmethod
    def check_command(command: str) -> Dict[str, Any]:
        """
        Analyzes a command string and returns its safety status.
        Status categories:
          - SAFE: Read-only or harmless
          - CAUTION: Mild side effects, allowed with logging
          - DANGEROUS: System-level impact, requires approval
          - BLOCKED: Catastrophic or destructive, denied outright
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return {
                "allowed": True,
                "risk_level": "SAFE",
                "reason": "Empty command",
                "requires_approval": False,
            }

        # 1. Check for outright blocked patterns
        for pattern, reason in BLOCKED_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return {
                    "allowed": False,
                    "risk_level": "BLOCKED",
                    "reason": f"BLOCKED: {reason}",
                    "requires_approval": False,
                }

        # 2. Check for patterns requiring explicit approval
        for pattern, reason in APPROVAL_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return {
                    "allowed": True,
                    "risk_level": "DANGEROUS",
                    "reason": f"High risk: {reason}",
                    "requires_approval": True,
                }

        # 3. Check for safe read-only prefixes
        cmd_head = cmd_clean.split()[0].lower() if cmd_clean.split() else ""
        for safe in SAFE_PREFIXES:
            if cmd_clean.lower().startswith(safe.lower()):
                return {
                    "allowed": True,
                    "risk_level": "SAFE",
                    "reason": "Known safe read/query command",
                    "requires_approval": False,
                }

        # 4. Default classification: CAUTION (standard modification/execution)
        return {
            "allowed": True,
            "risk_level": "CAUTION",
            "reason": "Standard execution command",
            "requires_approval": False,
        }

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """Returns True if the command is allowed and does not require manual approval."""
        res = cls.check_command(command)
        return res["allowed"] and not res["requires_approval"]
