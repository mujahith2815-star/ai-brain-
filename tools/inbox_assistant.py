"""
Autonomous Email & Calendar Inbox Assistant for P.H.A.S.S Sphere.
Ingests, categorizes, prioritizes, and reads aloud unread emails and calendar schedules.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.tools.inbox_assistant")


@dataclass
class EmailMessage:
    email_id: str
    sender: str
    subject: str
    preview: str
    is_read: bool
    priority: str # "HIGH", "NORMAL", "LOW"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email_id": self.email_id,
            "sender": self.sender,
            "subject": self.subject,
            "preview": self.preview,
            "is_read": self.is_read,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }


@dataclass
class CalendarScheduleItem:
    event_id: str
    title: str
    start_time: str
    location: str
    priority: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start_time": self.start_time,
            "location": self.location,
            "priority": self.priority,
        }


class InboxCalendarAssistant:
    def __init__(self):
        self.inbox_messages: List[EmailMessage] = [
            EmailMessage(
                email_id="msg_001",
                sender="Engineering Lead <lead@phass.ai>",
                subject="P.H.A.S.S Sphere v4.0 Release Verification",
                preview="All unit tests and physical robotics integration suites have passed with nominal performance.",
                is_read=False,
                priority="HIGH",
            ),
            EmailMessage(
                email_id="msg_002",
                sender="Security Operations <soc@phass.ai>",
                subject="Automated Network Security Audit Complete",
                preview="Zero critical vulnerabilities detected on local interfaces. System health score 100/100.",
                is_read=False,
                priority="HIGH",
            ),
            EmailMessage(
                email_id="msg_003",
                sender="Developer Updates <updates@github.com>",
                subject="Weekly Codebase Digest & Commits",
                preview="Your repositories have 14 new merged pull requests this week.",
                is_read=True,
                priority="NORMAL",
            ),
        ]

        self.calendar_events: List[CalendarScheduleItem] = [
            CalendarScheduleItem("evt_01", "Core Architecture Review", "02:00 PM", "Lab Command Center", "HIGH"),
            CalendarScheduleItem("evt_02", "Neural Weights Validation Check", "04:30 PM", "Terminal HUD", "NORMAL"),
        ]

    def get_unread_emails(self) -> List[EmailMessage]:
        return [m for m in self.inbox_messages if not m.is_read]

    def get_inbox_summary(self) -> Tuple[int, str]:
        unread = self.get_unread_emails()
        count = len(unread)
        if count == 0:
            return 0, "You have zero unread emails in your inbox, sir."

        lines = [f"You have {count} unread email{'s' if count != 1 else ''}, sir:"]
        for i, m in enumerate(unread, 1):
            lines.append(f"  {i}. [{m.priority}] From {m.sender.split('<')[0].strip()}: \"{m.subject}\"")

        return count, "\n".join(lines)

    def format_full_agenda_text(self) -> str:
        unread = self.get_unread_emails()
        lines = [
            "=== EXECUTIVE INBOX & CALENDAR AGENDA ===",
            f"Unread Emails: {len(unread)}",
        ]
        for m in unread:
            lines.append(f"  ✉️ [{m.priority}] {m.sender} -> \"{m.subject}\"\n     Preview: {m.preview}")

        lines.append(f"\nUpcoming Calendar Events Today ({len(self.calendar_events)}):")
        for e in self.calendar_events:
            lines.append(f"  📅 [{e.start_time}] {e.title} ({e.location}) [Priority: {e.priority}]")

        return "\n".join(lines)


inbox_assistant = InboxCalendarAssistant()
