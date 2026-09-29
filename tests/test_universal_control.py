"""
Unit tests for Orvix Universal System Controllers (Hardware, Network, Processes, Files, Media, Clipboard).
"""

import os
import tempfile
import pytest
from tools.hardware_controller import (
    get_cpu_info,
    get_ram_info,
    get_disk_info,
    get_battery_status,
    get_display_info,
    get_hardware_summary,
)
from tools.network_controller import (
    get_ip_addresses,
    ping_host,
    test_port as check_socket_port,
    get_active_connections,
)
from tools.process_controller import (
    list_processes,
    find_process,
)
from tools.file_controller import (
    get_file_info,
    calculate_hash,
    compress_files,
    extract_archive,
    find_duplicates,
)
from tools.clipboard_tool import (
    get_clipboard_text,
    set_clipboard_text,
)
from tools.notification_tool import (
    show_notification,
)


def test_get_cpu_info():
    """Verify CPU inspection metrics."""
    res = get_cpu_info()
    assert res["status"] == "SUCCESS"
    assert res["logical_cores"] > 0
    assert "processor_model" in res


def test_get_ram_info():
    """Verify RAM and swap inspection."""
    res = get_ram_info()
    assert res["status"] == "SUCCESS"
    assert res["total_gb"] > 0.0
    assert res["available_gb"] > 0.0


def test_get_disk_info():
    """Verify disk partitions and usage inspection."""
    res = get_disk_info()
    assert res["status"] == "SUCCESS"
    assert res["disk_count"] > 0
    assert len(res["disks"]) > 0


def test_get_battery_status():
    """Verify battery check handles both desktop and laptops gracefully."""
    res = get_battery_status()
    assert res["status"] == "SUCCESS"
    assert "has_battery" in res


def test_get_hardware_summary():
    """Verify consolidated hardware summary output."""
    summary = get_hardware_summary()
    assert summary["status"] == "SUCCESS"
    assert "cpu" in summary
    assert "ram" in summary
    assert "disks" in summary


def test_get_ip_addresses():
    """Verify local network interface IP retrieval."""
    res = get_ip_addresses()
    assert res["status"] == "SUCCESS"
    assert "ip_addresses" in res
    assert len(res["ip_addresses"]) > 0


def test_ping_host():
    """Verify ICMP ping to loopback interface."""
    res = ping_host("127.0.0.1", count=1)
    assert res["status"] in ("SUCCESS", "FAILED")  # In case firewall blocks ICMP
    assert "connected" in res


def test_test_port():
    """Verify socket port testing."""
    res = check_socket_port("127.0.0.1", 65534, timeout=0.5)
    assert res["status"] == "SUCCESS"
    assert "is_open" in res


def test_list_and_find_processes():
    """Verify process enumeration and lookup."""
    res = list_processes(sort_by="cpu", limit=10)
    assert res["status"] == "SUCCESS"
    assert len(res["processes"]) > 0

    curr_pid = os.getpid()
    find_res = find_process(curr_pid)
    assert find_res["status"] == "SUCCESS"
    assert find_res["total_found"] >= 1


def test_file_info_and_hash():
    """Verify file metadata and cryptographic hash calculation."""
    info = get_file_info(__file__)
    assert info["status"] == "SUCCESS"
    assert info["is_file"]
    assert info["size_bytes"] > 0

    h_res = calculate_hash(__file__, algorithm="sha256")
    assert h_res["status"] == "SUCCESS"
    assert len(h_res["hash"]) == 64


def test_compress_and_extract_archive():
    """Verify round-trip archive creation and extraction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.txt")
        with open(test_file, "w") as f:
            f.write("Hello Orvix Archive Compression Test")

        zip_target = os.path.join(tmpdir, "test.zip")
        comp_res = compress_files([test_file], zip_target, format="zip")
        assert comp_res["status"] == "SUCCESS"
        assert os.path.exists(comp_res["archive_path"])

        ext_dir = os.path.join(tmpdir, "extracted")
        ext_res = extract_archive(comp_res["archive_path"], ext_dir)
        assert ext_res["status"] == "SUCCESS"
        assert os.path.exists(os.path.join(ext_dir, "sample.txt"))


def test_clipboard_text():
    """Verify clipboard writing and reading."""
    test_str = "Orvix_Sphere_Clipboard_Test_Val"
    set_res = set_clipboard_text(test_str)
    assert set_res["status"] == "SUCCESS"

    get_res = get_clipboard_text()
    assert get_res["status"] == "SUCCESS"
    assert test_str in get_res["text"]


def test_show_notification():
    """Verify notification dispatch."""
    res = show_notification("Orvix Sphere", "Universal Control Online", duration_sec=1)
    assert res["status"] == "SUCCESS"
