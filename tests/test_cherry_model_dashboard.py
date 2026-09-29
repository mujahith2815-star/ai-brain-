import json
import urllib.request
import pytest
from ui.cherry_model_dashboard import cherry_dashboard_server
from nlp.conversational_agent import conversational_agent

@pytest.fixture(scope="module")
def dashboard_port():
    port = cherry_dashboard_server.start()
    assert port > 0
    yield port
    cherry_dashboard_server.stop()

def test_dashboard_html_endpoint(dashboard_port):
    url = f"http://127.0.0.1:{dashboard_port}/"
    with urllib.request.urlopen(url, timeout=3.0) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "P.H.A.S.S SPHERE" in html
        assert "backdrop-blur-overlay" in html
        assert "tileSplitSideBySide" in html
        assert "#ff003c" in html

def test_dashboard_api_model_status(dashboard_port):
    url = f"http://127.0.0.1:{dashboard_port}/api/model/status"
    with urllib.request.urlopen(url, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("is_ready_for_inference") is True

def test_dashboard_api_model_generate(dashboard_port):
    url = f"http://127.0.0.1:{dashboard_port}/api/model/generate"
    req = urllib.request.Request(
        url,
        data=json.dumps({"prompt": "what is your name"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "response" in data
        assert len(data["response"]) > 0

def test_dashboard_api_telemetry(dashboard_port):
    url = f"http://127.0.0.1:{dashboard_port}/api/system/telemetry"
    with urllib.request.urlopen(url, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "cpu_load_pct" in data

def test_dashboard_api_files_list(dashboard_port):
    url = f"http://127.0.0.1:{dashboard_port}/api/files/list"
    with urllib.request.urlopen(url, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "files" in data
        assert len(data["files"]) > 0

def test_conversational_dashboard_launch_directive():
    res = conversational_agent.handle_natural_conversation("launch model dashboard")
    assert res is not None
    assert res["type"] == "CHERRY_MODEL_DASHBOARD_LAUNCH"
    assert "http://127.0.0.1:" in res["speech_text"]
