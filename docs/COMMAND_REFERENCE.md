# Orvix Universal Command Reference (v1.1.0)

Welcome to the **Orvix Universal Command & Terminal Mastery Reference Guide**.
Orvix Sphere includes a pre-loaded knowledge base of **350+ terminal commands** spanning Windows PowerShell, Command Prompt (CMD), Linux Bash, and Cross-Shell Universal Patterns, coupled with an autonomous feedback learning loop and semantic VectorStore integration.

---

## 1. Architectural Overview

```
+-----------------------------------------------------------------------------+
|                         Operator / User Input                               |
|          ("/cmd ls", "/term Get-Process", or natural language intent)        |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                         Orvix Cognitive Agent                               |
|              (Llama-3.2-1B-Instruct + Phi-4 Secondary Brain)                |
+-----------------------------------------------------------------------------+
               |                              |                        |
               v                              v                        v
+-----------------------------+ +---------------------------+ +---------------+
|   Command Knowledge Base    | |   Terminal Execution      | | Shell Safety  |
| - windows_commands.json     | | - run_terminal()          | | - BLOCKED     |
| - linux_commands.json       | | - chain_commands()        | | - DANGEROUS   |
| - universal_patterns.json   | | - pipe_command()          | | - CAUTION     |
| - learned_commands.json     | | - find_file()             | | - SAFE        |
+-----------------------------+ +---------------------------+ +---------------+
               |                              |                        |
               +------------------------------+------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|               Persistent SQLite History & Autonomous Feedback Learner        |
| - Table: command_history (command, shell, exit_code, stdout, stderr, ms)    |
| - Background Learner: Analyzes failure/recovery patterns & custom workflows |
| - VectorStore: Semantic vector embeddings via all-MiniLM-L6-v2              |
+-----------------------------------------------------------------------------+
```

---

## 2. Command Taxonomy & Breakdown

| Environment / Shell | Command Count | Primary Engine |
|---|---|---|
| **PowerShell** | 100+ commands | `powershell.exe` / `pwsh` |
| **Command Prompt (CMD)** | 80+ commands | `cmd.exe /c` |
| **Linux Bash** | 150+ commands | `/bin/bash` / Git Bash / WSL |
| **Universal Patterns** | 14 patterns | Pipes, redirection, subshells, loops |
| **Total Pre-loaded** | **353 commands** | Auto-indexed in VectorStore |

### Categories
1. **Filesystem**: `ls`, `dir`, `cd`, `pwd`, `cp`, `mv`, `rm`, `mkdir`, `touch`, `ln`, `df`, `du`, `tree`, `Get-ChildItem`, `New-Item`, `Remove-Item`
2. **Search**: `find`, `grep`, `locate`, `which`, `whereis`, `Select-String`, `findstr`, `Get-Command`
3. **Text Processing**: `cat`, `awk`, `sed`, `cut`, `sort`, `uniq`, `head`, `tail`, `tee`, `diff`, `Get-Content`, `Set-Content`
4. **Process Management**: `ps`, `top`, `htop`, `kill`, `pkill`, `Get-Process`, `Stop-Process`, `Start-Process`, `tasklist`, `taskkill`
5. **Network Diagnostics**: `curl`, `wget`, `ping`, `traceroute`, `ip`, `ifconfig`, `netstat`, `ss`, `dig`, `Test-NetConnection`, `Get-NetIPAddress`
6. **System & Hardware**: `uname`, `hostname`, `uptime`, `whoami`, `id`, `dmesg`, `journalctl`, `systemctl`, `free`, `lscpu`, `Get-CimInstance`
7. **Archive & Compression**: `tar`, `gzip`, `zip`, `unzip`, `7z`, `Compress-Archive`, `Expand-Archive`
8. **Permissions & Security**: `chmod`, `chown`, `chgrp`, `umask`, `icacls`, `takeown`, `Get-Acl`, `Set-Acl`
9. **User Management**: `useradd`, `userdel`, `usermod`, `passwd`, `sudo`, `New-LocalUser`, `Remove-LocalUser`
10. **Package Management**: `apt`, `yum`, `dnf`, `pacman`, `snap`, `winget`, `choco`, `pip`, `npm`
11. **Version Control**: `git status`, `git add`, `git commit`, `git push`, `git pull`, `git diff`, `git log`, `git checkout`, `git branch`
12. **Development & Containers**: `python3`, `node`, `make`, `gcc`, `docker`, `docker-compose`
13. **Registry (Windows)**: `reg query`, `reg add`, `reg export`, `Get-ItemProperty`, `Set-ItemProperty`
14. **Scheduling**: `crontab`, `at`, `schtasks`, `Get-ScheduledTask`, `Register-ScheduledTask`
15. **Media & Hardware**: `ffmpeg`, `ffprobe`, `mount`, `umount`, `diskpart`, `Get-Disk`, `Get-Volume`
16. **Power & Lifecycle**: `shutdown`, `reboot`, `powercfg`, `Stop-Computer`, `Restart-Computer`

---

## 3. Shell Safety Classification

All command execution passes through `ShellSafety` before touching any system subprocess:

| Level | Policy | Examples |
|---|---|---|
| **SAFE** | Allowed immediately | `ls`, `dir`, `Get-ChildItem`, `cat`, `echo`, `uptime`, `ping`, `ps` |
| **CAUTION** | Allowed with execution logging | `mkdir`, `cp`, `git commit`, `npm run`, `python script.py` |
| **MODERATE** | Allowed with logging and error tracking | `mv`, `Set-Content`, `chmod 755`, `pip install` |
| **DANGEROUS** | Requires explicit confirmation / approval | `shutdown`, `reboot`, `killall -9`, `Remove-LocalUser` |
| **BLOCKED** | Denied outright without exception | `rm -rf /`, `format C:`, `Clear-Disk`, fork bomb `:(){ :|:& };:` |

---

## 4. Self-Learning Loop & Analytics

Orvix continuously improves from experience:
1. Every command executed is logged to `knowledge/agent_memory.db` (`command_history` table).
2. Telemetry captured: command string, shell interpreter, working directory, exit code, stdout/stderr snippets, and duration (ms).
3. The background learner (`auto_learner.py`) scans execution history every 5 minutes:
   - Identifies custom command scripts that succeed repeatedly and adds them to `learned_commands.json`.
   - Identifies failure patterns and recommends alternatives.
   - Embeds newly learned tools into `VectorStore` for automatic RAG retrieval.

---

## 5. Interactive Slash Commands

| Command | Description | Example |
|---|---|---|
| `/cmd` | Overview of command knowledge base | `/cmd` |
| `/cmd <name>` | Full documentation, flags, and syntax | `/cmd ls` or `/cmd Get-Process` |
| `/cmd-search <query>` | Search commands by keyword | `/cmd-search process` |
| `/cmd-suggest <intent>` | Suggest commands from natural language | `/cmd-suggest find largest files` |
| `/cmd-explain <cmd>` | Dissect flags, syntax, and safety | `/cmd-explain tar -czvf archive.tar.gz src/` |
| `/cmd-categories` | List all 17 categories with counts | `/cmd-categories` |
| `/cmd-learned` | View auto-learned custom commands | `/cmd-learned` |
| `/cmd-history` | Execution stats and recent command history | `/cmd-history` |
| `/term <cmd>` | Direct safe terminal execution | `/term dir` |
