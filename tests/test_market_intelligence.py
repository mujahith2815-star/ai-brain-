"""
Unit & Integration Tests for Market Intelligence, Omni-Search, and v3.0 Metadata.
"""

import pytest
from knowledge.market_intelligence import market_intelligence
from nlp.conversational_agent import conversational_agent
from core.version import VERSION, VERSION_CODENAME, get_version_banner


# 1. Version Verification
def test_v3_version_metadata():
    assert VERSION in ("3.0.0", "4.0.0", "5.0.0", "6.0.0", "7.0.0", "8.0.0")
    banner = get_version_banner()
    assert "P.H.A.S.S SPHERE" in banner


# 2. Market Intelligence & Laptop Spare Parts Search
def test_market_intelligence_laptop_parts():
    report = market_intelligence.search_market_components("search any spare parts for laptops in market", auto_open_browser=False)
    assert report.query == "search any spare parts for laptops in market"
    assert len(report.categories) >= 4
    assert len(report.recommended_vendors) >= 3
    assert "Displays" in [c.category_name for c in report.categories][0]
    assert "Storage" in [c.category_name for c in report.categories][1]

    txt = market_intelligence.format_market_report_text(report)
    assert "DISPLAYS" in txt
    assert "Amazon" in txt or "eBay" in txt


# 3. Dynamic Intelligence Routing for Market & Omni-Search
def test_conversational_market_and_omni_search():
    # A. Laptop spare parts query (User request)
    res_m = conversational_agent.handle_natural_conversation("search any spare parts for laptops in market")
    assert res_m is not None
    assert res_m["type"] == "MARKET_INTELLIGENCE"
    assert res_m["action_executed"] == "LIVE_MARKET_SEARCH"
    assert "SPARE PARTS" in res_m["speech_text"]

    # B. General search query
    res_s = conversational_agent.handle_natural_conversation("search latest artificial intelligence breakthroughs")
    assert res_s is not None
    assert res_s["type"] == "LIVE_OMNI_SEARCH"
    assert res_s["action_executed"] == "OMNI_WEB_SEARCH"
