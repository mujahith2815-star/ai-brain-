import pytest
from tools.security_master import (
    encryption,
    password_vault,
    ssh_manager,
    firewall_manager,
    audit_logger,
    threat_detection,
    confirmation_gate,
)


def test_encryption_and_decryption():
    secret = "TopSecretAPIKey_987654"
    enc = encryption("encrypt", secret, algorithm="AES-256")
    assert enc["status"] == "SUCCESS"
    assert "ciphertext" in enc

    dec = encryption("decrypt", enc["ciphertext"])
    assert dec["status"] == "SUCCESS"
    assert dec["plaintext"] == secret


def test_password_vault():
    res = password_vault("store", "aws_console", "MyMasterPassword#1")
    assert res["status"] == "SUCCESS"

    ret = password_vault("get", "aws_console")
    assert ret["status"] == "SUCCESS"
    assert ret["password"] == "MyMasterPassword#1"

    lst = password_vault("list", "")
    assert lst["status"] == "SUCCESS"
    assert "aws_console" in lst["services"]


def test_ssh_and_firewall_management():
    ssh = ssh_manager("generate_key")
    assert ssh["status"] == "SUCCESS"

    fw = firewall_manager("status")
    assert fw["status"] == "SUCCESS"


def test_threat_detection():
    threat = threat_detection("shell", {"command": "sudo rm -rf /"})
    assert threat["status"] == "SUCCESS"
    assert threat["is_threat"] is True
    assert threat["threat_level"] == "HIGH"

    safe = threat_detection("shell", {"command": "git status"})
    assert safe["is_threat"] is False
    assert safe["threat_level"] == "NONE"


def test_confirmation_gate():
    gate = confirmation_gate("delete_database", {"db": "production"})
    assert gate["status"] == "PENDING_CONFIRMATION"
    token = gate["confirmation_token"]
    assert token.startswith("TOKEN-")

    confirmed = confirmation_gate("delete_database", {"db": "production"}, token)
    assert confirmed["status"] == "CONFIRMED"
    assert confirmed["approved"] is True

    # Bad token rejection
    bad_token = confirmation_gate("delete_database", {"db": "production"}, "BAD-TOKEN-XYZ")
    assert bad_token["status"] == "REJECTED"
    assert bad_token["approved"] is False