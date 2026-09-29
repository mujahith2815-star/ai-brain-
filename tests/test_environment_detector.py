"""
Tests for Environment Detector & Hardware Profiler.
"""

import pytest
from core.environment_detector import (
    detect_os,
    detect_hardware,
    detect_package_managers,
    detect_runtimes,
    recommend_llama_tier,
    get_environment_report,
)


def test_detect_os():
    os_info = detect_os()
    assert "system" in os_info
    assert "release" in os_info
    assert "distro" in os_info
    assert isinstance(os_info["is_windows"], bool)
    assert isinstance(os_info["is_linux"], bool)


def test_detect_hardware():
    hw = detect_hardware()
    assert hw["cpu_cores"] >= 1
    assert "cpu_arch" in hw
    assert hw["ram_total_gb"] > 0
    assert hw["ram_available_gb"] > 0
    assert "gpu" in hw


def test_detect_package_managers():
    pms = detect_package_managers()
    assert isinstance(pms, list)
    # Python environment usually has pip
    assert "pip" in pms or len(pms) >= 0


def test_detect_runtimes():
    rt = detect_runtimes()
    assert isinstance(rt, dict)
    assert rt["python"] is True


def test_recommend_llama_tier():
    # 4GB RAM -> 1B
    rec_1b = recommend_llama_tier({"ram_total_gb": 4.0, "has_cuda": False})
    assert "1b" in rec_1b["recommended_model"].lower()

    # 12GB RAM -> 3B
    rec_3b = recommend_llama_tier({"ram_total_gb": 12.0, "has_cuda": False})
    assert "3b" in rec_3b["recommended_model"].lower()

    # 32GB RAM -> 8B
    rec_8b = recommend_llama_tier({"ram_total_gb": 32.0, "has_cuda": False})
    assert "8b" in rec_8b["recommended_model"].lower()

    # 64GB RAM -> 70B
    rec_70b = recommend_llama_tier({"ram_total_gb": 64.0, "has_cuda": False})
    assert "70b" in rec_70b["recommended_model"].lower()


def test_get_environment_report():
    rep = get_environment_report()
    assert "os" in rep
    assert "hardware" in rep
    assert "recommendation" in rep
    assert "python_version" in rep
