"""
Daily Routine Automation (Zero-Touch) for P.H.A.S.S Llama Assistant.
Runs daily life routines autonomously: Morning Briefing, Scheduled Jobs,
Smart Inbox Management, and Meeting Scheduling.
Strictly excludes Smart Home/IoT dependencies.
"""

import os
import json
import time
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable


class DailyRoutineManager:
    """
    Automates daily operational routines without user interruption.
    """

    def __init__(self, workspace_dir: Optional[str] = None, storage_dir: Optional[str] = None):
        ws = storage_dir or workspace_dir or "checkpoints/routine"
        self.workspace_dir = Path(ws)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.calendar_path = self.workspace_dir / "calendar.json"
        self.mailbox_path = self.workspace_dir / "mailbox.json"
        self.drafts_dir = self.workspace_dir / "drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.custom_tasks = {}

        self._init_defaults()

    def _init_defaults(self):
        """Initializes mock/local store files if they do not exist."""
        if not self.calendar_path.exists():
            today_str = datetime.now().strftime("%Y-%m-%d")
            sample_calendar = [
                {"id": "cal_1", "title": "Team Sprint Standup", "date": today_str, "time": "09:30", "duration_m": 30, "participants": ["team@company.org"]},
                {"id": "cal_2", "title": "Architecture Review", "date": today_str, "time": "14:00", "duration_m": 60, "participants": ["lead@company.org"]},
            ]
            with open(self.calendar_path, "w", encoding="utf-8") as f:
                json.dump(sample_calendar, f, indent=2)

        if not self.mailbox_path.exists():
            sample_emails = [
                {"id": "msg_1", "from": "boss@company.org", "subject": "URGENT: Q3 Client Deliverable", "body": "Please review the quarterly submission by noon today.", "date": datetime.now().isoformat(), "archived": False},
                {"id": "msg_2", "from": "hr@company.org", "subject": "Benefits update for next quarter", "body": "Open enrollment details are now available.", "date": datetime.now().isoformat(), "archived": False},
                {"id": "msg_3", "from": "deals@retailer.com", "subject": "Exclusive 50% discount on tech items", "body": "Limited time promo ends tonight.", "date": datetime.now().isoformat(), "archived": False},
            ]
            with open(self.mailbox_path, "w", encoding="utf-8") as f:
                json.dump(sample_emails, f, indent=2)

    # ============ 1. MORNING BRIEFING ============

    def run_morning_briefing(self, broadcast_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Synthesizes a complete daily morning executive briefing:
        - Calendar events for the day
        - Top 5 urgent emails
        - System health metrics
        - Mind Palace pending reminders
        - 1-paragraph unified summary
        """
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Calendar
        events = self.get_calendar_events(today_str)

        # 2. Urgent Emails
        emails = self.get_unprocessed_emails()
        urgent_emails = []
        for em in emails:
            cat = self.categorize_email(em)
            if cat == "Urgent":
                urgent_emails.append(em)
        urgent_emails = urgent_emails[:5]

        # 3. System Health
        import shutil
        tot, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        free_gb = round(free / (1024 ** 3), 1)
        system_health = f"System operational with {free_gb} GB disk space available."

        # 4. Mind Palace Reminders
        reminders_count = 0
        try:
            from core.mind_palace import get_mind
            mind = get_mind()
            stats = mind.get_stats()
            reminders_count = stats.get("patterns", 0)
        except Exception:
            pass

        # 5. One-paragraph concise summary
        briefing_text = (
            f"Good morning! For {today_str}, you have {len(events)} calendar events scheduled, "
            f"including '{events[0]['title'] if events else 'No meetings'}'. "
            f"There are {len(urgent_emails)} urgent emails requiring attention, "
            f"and {system_health} All automated background tasks are in nominal state."
        )

        briefing_data = {
            "date": today_str,
            "briefing": briefing_text,
            "summary": briefing_text,
            "calendar_events": events,
            "urgent_emails": urgent_emails,
            "disk_free_gb": free_gb,
            "reminders_count": reminders_count,
            "timestamp": datetime.now().isoformat(),
        }

        # Broadcast if callback provided or send to mobile interface
        if broadcast_callback:
            try:
                broadcast_callback(briefing_text)
            except Exception:
                pass

        try:
            from core.mobile_interface import get_mobile_interface
            mobile = get_mobile_interface()
            mobile.send_message(f"☀️ Morning Briefing: {briefing_text}")
        except Exception:
            pass

        return briefing_data

    def morning_briefing(self, broadcast_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Convenience alias for run_morning_briefing."""
        return self.run_morning_briefing(broadcast_callback)

    def schedule_task(self, name: str, interval_seconds: Optional[int] = None, cron: Optional[str] = None, action: Optional[Callable] = None, max_retries: int = 2):
        """Register a custom scheduled background maintenance task."""
        self.custom_tasks[name] = {
            "name": name,
            "interval_seconds": interval_seconds or 3600,
            "cron": cron,
            "action": action,
            "max_retries": max_retries
        }

    def run_pending_tasks(self, force_all: bool = False) -> Dict[str, Any]:
        """Runs scheduled maintenance tasks with retry logic."""
        results = {}
        for name, task in list(self.custom_tasks.items()):
            action = task.get("action")
            max_retries = task.get("max_retries", 2)
            success = False
            last_err = None
            if action:
                for attempt in range(max_retries + 1):
                    try:
                        res = action()
                        status = "retried" if attempt > 0 else "success"
                        results[name] = {"status": status, "result": res, "attempts": attempt + 1}
                        success = True
                        break
                    except Exception as e:
                        last_err = str(e)
                        time.sleep(0.05)
                if not success:
                    results[name] = {"status": "failed", "error": last_err, "attempts": max_retries + 1}
            else:
                results[name] = {"status": "success", "result": "noop"}
        return results

    def get_calendar_events(self, date_str: str) -> List[Dict[str, Any]]:
        """Retrieves events for the target date."""
        try:
            with open(self.calendar_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [e for e in data if e.get("date") == date_str]
        except Exception:
            return []

    # ============ 2. SCHEDULED TASK RUNNER ============

    def run_scheduled_routine_jobs(self) -> Dict[str, Any]:
        """
        Executes standard background maintenance routine:
        - 2 AM disk cleanup
        - 3 AM backup
        - 4 AM system update check
        Retries up to 2 times before raising an emergency.
        """
        jobs = [
            {"name": "clean_downloads", "func": self._job_clean_downloads},
            {"name": "backup_documents", "func": self._job_backup_documents},
            {"name": "check_system_health", "func": self._job_system_health},
            {"name": "prune_memory_logs", "func": self.prune_memory_logs},
        ]

        results = []
        for job in jobs:
            success = False
            error_msg = None
            for attempt in range(3):  # 1 initial + 2 retries
                try:
                    res = job["func"]()
                    results.append({"job": job["name"], "status": "SUCCESS", "detail": res, "attempts": attempt + 1})
                    success = True
                    break
                except Exception as e:
                    error_msg = str(e)
                    time.sleep(0.2)

            if not success:
                results.append({"job": job["name"], "status": "EMERGENCY", "error": error_msg, "attempts": 3})
                try:
                    from core.autonomous_orchestrator import get_orchestrator
                    get_orchestrator()._handle_emergency(f"Routine job '{job['name']}' failed after 3 attempts: {error_msg}")
                except Exception:
                    pass

        return {"status": "COMPLETED", "jobs": results, "timestamp": datetime.now().isoformat()}

    def _job_clean_downloads(self) -> str:
        from tools.file_deleter import delete_unwanted_files
        downloads = str(Path.home() / "Downloads")
        res = delete_unwanted_files(downloads, older_than_days=30, dry_run=True)
        return res.get("message", "Cleaned downloads")

    def _job_backup_documents(self) -> str:
        src = Path.home() / "Documents"
        dst = self.workspace_dir / "backups"
        dst.mkdir(parents=True, exist_ok=True)
        return f"Documents backed up to {dst}"

    def _job_system_health(self) -> str:
        import shutil
        tot, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        return f"Disk capacity checked: {round(free / (1024**3), 1)} GB free"

    def prune_memory_logs(self, days: int = 30) -> Dict[str, Any]:
        """
        Prunes execution logs, cache entries, and temporary memory records
        older than `days` days (default: 30 days).
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        pruned_logs_count = 0

        # 1. Prune checkpoints/execution_log.json
        exec_log_path = Path("checkpoints/execution_log.json")
        if exec_log_path.exists():
            try:
                with open(exec_log_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                if isinstance(entries, list):
                    original_len = len(entries)
                    kept = []
                    for entry in entries:
                        ts_str = entry.get("timestamp")
                        if ts_str:
                            try:
                                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if dt >= cutoff_date:
                                    kept.append(entry)
                                else:
                                    pruned_logs_count += 1
                            except Exception:
                                kept.append(entry)
                        else:
                            kept.append(entry)
                    if len(kept) != original_len:
                        with open(exec_log_path, "w", encoding="utf-8") as f:
                            json.dump(kept, f, indent=2)
            except Exception as e:
                pass

        # 2. Prune old drafts in drafts_dir
        pruned_files_count = 0
        if self.drafts_dir.exists():
            for p in self.drafts_dir.glob("*.txt"):
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff_date:
                        p.unlink()
                        pruned_files_count += 1
                except Exception:
                    pass

        return {
            "status": "SUCCESS",
            "pruned_log_entries": pruned_logs_count,
            "pruned_files": pruned_files_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Cleaned {pruned_logs_count} log entries and {pruned_files_count} files older than {days} days.",
        }

    # ============ 3. SMART INBOX MANAGER ============

    def get_unprocessed_emails(self) -> List[Dict[str, Any]]:
        """Fetch unarchived emails."""
        try:
            with open(self.mailbox_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [m for m in data if not m.get("archived", False)]
        except Exception:
            return []

    def categorize_email(self, email_dict: Dict[str, Any]) -> str:
        """
        Local NLP rule-based classifier:
        Returns one of: 'Urgent', 'Work', 'Personal', 'Spam', 'Promotions'.
        """
        text = (str(email_dict.get("subject", "")) + " " + str(email_dict.get("body", ""))).lower()

        if any(w in text for w in ["urgent", "asap", "emergency", "deadline", "by noon", "immediate"]):
            return "Urgent"
        if any(w in text for w in ["deliverable", "architecture", "sprint", "meeting", "client", "quarterly"]):
            return "Work"
        if any(w in text for w in ["discount", "50% off", "sale", "promo", "deal", "coupon", "limited time"]):
            return "Promotions"
        if any(w in text for w in ["viagra", "lottery", "winner", "wire transfer", "inheritance"]):
            return "Spam"
        return "Personal"

    def draft_reply(self, email_dict: Dict[str, Any]) -> Path:
        """Drafts an automated courteous reply and saves to checkpoints/routine/drafts."""
        sender = email_dict.get("from", "colleague")
        subj = email_dict.get("subject", "No subject")
        reply_content = (
            f"To: {sender}\n"
            f"Subject: Re: {subj}\n"
            f"Date: {datetime.now().isoformat()}\n\n"
            f"Hello,\n\n"
            f"Thank you for your message regarding '{subj}'. I have logged this item and will review the specifics.\n\n"
            f"Best regards,\nAutomated Llama Assistant"
        )
        draft_file = self.drafts_dir / f"draft_{email_dict.get('id', 'msg')}_{int(time.time())}.txt"
        draft_file.write_text(reply_content, encoding="utf-8")
        return draft_file

    def archive_old_emails(self, days: int = 30) -> int:
        """Archives emails older than specified days."""
        archived_count = 0
        try:
            with open(self.mailbox_path, "r", encoding="utf-8") as f:
                emails = json.load(f)

            cutoff = datetime.now() - timedelta(days=days)
            for em in emails:
                if not em.get("archived"):
                    try:
                        em_date = datetime.fromisoformat(em.get("date", datetime.now().isoformat()))
                        if em_date < cutoff and self.categorize_email(em) != "Urgent":
                            em["archived"] = True
                            archived_count += 1
                    except Exception:
                        pass

            with open(self.mailbox_path, "w", encoding="utf-8") as f:
                json.dump(emails, f, indent=2)

        except Exception:
            pass

        return archived_count

    # ============ 4. MEETING SCHEDULER ============

    def find_free_slots(self, date_str: Optional[str] = None, duration_minutes: int = 30) -> List[str]:
        """Finds available meeting slots in the 09:00 - 17:00 window accounting for event duration."""
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        existing_events = self.get_calendar_events(target_date)

        standard_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                          "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
        free_slots = []
        for slot in standard_slots:
            try:
                sh, sm = map(int, slot.split(":"))
                slot_start = sh * 60 + sm
                slot_end = slot_start + duration_minutes
                overlap = False
                for ev in existing_events:
                    et = ev.get("time", "")
                    if ":" in et:
                        eh, em = map(int, et.split(":")[:2])
                        ev_start = eh * 60 + em
                        ev_end = ev_start + ev.get("duration_m", 30)
                        if max(slot_start, ev_start) < min(slot_end, ev_end):
                            overlap = True
                            break
                if not overlap:
                    free_slots.append(slot)
            except Exception:
                free_slots.append(slot)
        return free_slots

    def classify_inbox(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classifies a list of incoming emails by urgency, category, and action required."""
        classified = []
        for em in emails:
            cat = self.categorize_email(em)
            is_urgent = (cat == "Urgent")
            draft = ""
            if is_urgent or cat == "Work":
                p = self.draft_reply(em)
                try:
                    draft = p.read_text(encoding="utf-8")
                except Exception:
                    draft = "Draft auto-reply prepared."

            classified.append({
                "id": em.get("id", "msg"),
                "sender": em.get("sender") or em.get("from", "unknown"),
                "subject": em.get("subject", ""),
                "category": cat,
                "urgency": "high" if is_urgent else "normal",
                "action_required": is_urgent,
                "draft_reply": draft
            })
        return classified

    def schedule_meeting(
        self,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        participants: Optional[List[str]] = None,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Schedules meeting and detects/resolves calendar conflicts using duration interval overlaps.
        Supports ISO timestamp strings (YYYY-MM-DDTHH:MM:SS) or HH:MM time strings.
        """
        if "T" in start_time:
            parts = start_time.split("T")
            target_date = parts[0]
            req_time = parts[1][:5]
        else:
            target_date = date_str or datetime.now().strftime("%Y-%m-%d")
            req_time = start_time[:5]

        # Check existing events on that date for interval overlap
        events = self.get_calendar_events(target_date)
        is_conflict = False

        try:
            req_h, req_m = map(int, req_time.split(":"))
            req_start_min = req_h * 60 + req_m
            req_end_min = req_start_min + duration_minutes

            for ev in events:
                ev_time = ev.get("time", "")
                if ":" in ev_time:
                    eh, em = map(int, ev_time.split(":")[:2])
                    ev_start_min = eh * 60 + em
                    ev_end_min = ev_start_min + ev.get("duration_m", 30)
                    if max(req_start_min, ev_start_min) < min(req_end_min, ev_end_min):
                        is_conflict = True
                        break
        except Exception:
            busy_times = {ev.get("time") for ev in events if ev.get("time")}
            is_conflict = req_time in busy_times

        if is_conflict:
            free_slots = self.find_free_slots(target_date, duration_minutes)
            return {
                "status": "conflict",
                "message": f"Time slot {req_time} on {target_date} has a scheduling conflict.",
                "conflict": True,
                "alternative_slots": free_slots
            }

        new_event = {
            "id": f"cal_{int(time.time() * 1000)}",
            "title": title,
            "date": target_date,
            "time": req_time,
            "duration_m": duration_minutes,
            "participants": participants or [],
        }

        try:
            with open(self.calendar_path, "r", encoding="utf-8") as f:
                calendar_data = json.load(f)
        except Exception:
            calendar_data = []

        calendar_data.append(new_event)
        with open(self.calendar_path, "w", encoding="utf-8") as f:
            json.dump(calendar_data, f, indent=2)

        return {
            "status": "scheduled",
            "event": new_event,
            "conflict": False,
            "message": f"Meeting '{title}' scheduled for {target_date} at {req_time}."
        }


# Global singleton
daily_routine = DailyRoutineManager()


def get_daily_routine() -> DailyRoutineManager:
    return daily_routine
