"""
Tests for Omni-Interface Gateway (Telegram, Slack, REST API, and Desktop Widget).
"""

import pytest
from core.omni_interface import (
    TelegramGateway,
    SlackGateway,
    DesktopWidget,
    OmniGateway,
    handle_api_request,
)


def test_api_health_endpoint():
    code, data = handle_api_request("GET", "/health")
    assert code == 200
    assert data["status"] == "HEALTHY"


def test_api_status_endpoint():
    code, data = handle_api_request("GET", "/status")
    assert code == 200
    assert data["status"] == "ONLINE"
    assert "registered_tools_count" in data
    assert data["registered_tools_count"] > 0


def test_api_tools_catalog():
    code, data = handle_api_request("GET", "/tools")
    assert code == 200
    assert "tools" in data
    assert data["total_tools"] > 0
    names = [t["name"] for t in data["tools"]]
    assert "smart_home_discover_devices" in names or len(names) > 10


def test_api_chat_endpoint():
    payload = {"message": "Hello, how are you?", "session_id": "test_sess"}
    code, data = handle_api_request("POST", "/chat", payload)
    assert code == 200
    assert "reply" in data
    assert data["session_id"] == "test_sess"


def test_telegram_gateway_simulation():
    tg = TelegramGateway()
    res = tg.send_message("12345678", "System update completed successfully.")
    assert res["status"] == "SUCCESS"
    assert res["chat_id"] == "12345678"
    assert len(tg.message_history) == 1


def test_slack_gateway_simulation():
    slack = SlackGateway()
    res = slack.post_message("#general", "Scheduled backup complete.")
    assert res["status"] == "SUCCESS"
    assert res["channel"] == "#general"
    assert len(slack.message_history) == 1


def test_desktop_widget_headless():
    widget = DesktopWidget()
    res = widget.simulate_query("Check system status")
    assert res["status"] == "SUCCESS"
    assert "reply" in res


def test_omni_broadcast():
    omni = OmniGateway()
    res = omni.send_broadcast("Daily briefing notification")
    assert "telegram" in res
    assert "slack" in res
    assert res["broadcast_text"] == "Daily briefing notification"
