import pytest
import os
from tools.web_master import (
    browser_automation,
    web_scraper,
    form_filler,
    auto_login,
    youtube_controller,
    download_manager,
    rss_reader,
)


def test_web_scraper_text():
    res = web_scraper("https://example.com", extract_type="text")
    assert res["status"] == "SUCCESS"
    assert "text" in res
    assert len(res["text"]) > 0


def test_browser_automation():
    res = browser_automation("navigate", url="https://example.com")
    assert res["status"] == "SUCCESS"
    assert res["action"] == "navigate"


def test_form_filler():
    res = form_filler("https://example.com/contact", {"name": "Alice", "email": "alice@example.com"})
    assert res["status"] == "SUCCESS"
    assert len(res["fields_filled"]) == 2


def test_auto_login():
    res = auto_login("github.com", "dev_user", "super_secret_pwd")
    assert res["status"] == "SUCCESS"
    assert res["authenticated"] is True
    assert res["username"] == "dev_user"


def test_youtube_controller():
    res = youtube_controller("search", "Deep Learning Tutorial")
    assert res["status"] == "SUCCESS"
    results = res.get("results") or res.get("recommended_results")
    assert results is not None
    assert len(results) > 0


def test_download_manager():
    dl = download_manager("https://example.com", destination_dir="memory_vault", filename="unit_test_dl.txt")
    assert dl["status"] == "SUCCESS"
    assert os.path.exists(dl["saved_to"])


def test_rss_reader():
    res = rss_reader("https://news.ycombinator.com/rss", max_items=2)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) >= 1