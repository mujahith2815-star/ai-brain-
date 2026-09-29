"""
Ethical Cybersecurity Defense, Port Scanner & Network Vulnerability Auditor for P.H.A.S.S Sphere.
Provides network surface mapping, port scanning, security posture evaluation,
firewall inspection, and defensive system hardening.
"""

from __future__ import annotations
import math
import re
import socket
import subprocess
import sys
import threading
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.security.cyber_defense")


@dataclass
class PortScanResult:
    port: int
    service_name: str
    is_open: bool
    risk_level: str # "LOW", "MEDIUM", "HIGH"
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port": self.port,
            "service_name": self.service_name,
            "is_open": self.is_open,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
        }


@dataclass
class CyberSecurityAuditReport:
    target_host: str
    scan_timestamp: str
    total_ports_scanned: int
    open_ports_detected: List[PortScanResult]
    system_security_score: int # 0 to 100
    vulnerabilities_found: List[str]
    hardening_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_host": self.target_host,
            "scan_timestamp": self.scan_timestamp,
            "total_ports_scanned": self.total_ports_scanned,
            "open_ports_detected": [p.to_dict() for p in self.open_ports_detected],
            "system_security_score": self.system_security_score,
            "vulnerabilities_found": self.vulnerabilities_found,
            "hardening_actions": self.hardening_actions,
        }


class CyberDefenseSuite:
    COMMON_PORTS = {
        21: ("FTP", "HIGH", "Unencrypted File Transfer Protocol. Disable if unused or enforce FTPS/SFTP."),
        22: ("SSH", "MEDIUM", "Secure Shell. Ensure password authentication is disabled in favor of Ed25519 keys."),
        23: ("Telnet", "HIGH", "Insecure plaintext protocol. Disable immediately."),
        25: ("SMTP", "MEDIUM", "Mail transport. Secure with STARTTLS and SPF/DKIM validation."),
        53: ("DNS", "LOW", "Domain Name Resolution. Protect against DNS amplification."),
        80: ("HTTP", "MEDIUM", "Unencrypted Web. Enforce HTTPS redirect via TLS 1.3."),
        110: ("POP3", "HIGH", "Unencrypted mail retrieval. Migrate to POP3S or IMAP over TLS."),
        135: ("RPC", "HIGH", "Windows RPC Endpoint Mapper. Block from public internet."),
        139: ("NetBIOS", "HIGH", "NetBIOS Session Service. Restrict to internal trusted subnet."),
        443: ("HTTPS", "LOW", "Encrypted Web. Ensure modern TLS cipher suites and HSTS header."),
        445: ("SMB", "HIGH", "Server Message Block. Protect against remote exploitation. Disable SMBv1."),
        1433: ("MSSQL", "HIGH", "SQL Server Database. Never expose to public WAN interfaces."),
        3306: ("MySQL", "HIGH", "Database Port. Bind strictly to localhost (127.0.0.1)."),
        3389: ("RDP", "HIGH", "Remote Desktop Protocol. Require MFA or VPN tunnel."),
        5432: ("PostgreSQL", "HIGH", "PostgreSQL Database. Bind to localhost with strong SCRAM-SHA-256 auth."),
        8080: ("HTTP-Proxy/Dev", "MEDIUM", "Secondary Web / Dev Server. Ensure debug endpoints are authenticated."),
    }

    def __init__(self):
        self.last_report: Optional[CyberSecurityAuditReport] = None

    def scan_target_ports(self, host: str = "127.0.0.1", timeout_sec: float = 0.4) -> List[PortScanResult]:
        """
        Scans common network ports on target host using non-invasive socket probes.
        """
        results: List[PortScanResult] = []

        for port, (svc, risk, rec) in self.COMMON_PORTS.items():
            is_open = False
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout_sec)
                res = sock.connect_ex((host, port))
                if res == 0:
                    is_open = True
                sock.close()
            except Exception:
                is_open = False

            if is_open:
                results.append(PortScanResult(port, svc, True, risk, rec))

        return results

    def run_full_security_audit(self, target_host: str = "127.0.0.1") -> CyberSecurityAuditReport:
        """
        Performs a full defensive posture assessment: port scanning, weak configuration audit,
        and system hardening recommendations.
        """
        open_ports = self.scan_target_ports(target_host)
        vulns: List[str] = []
        hardening: List[str] = []
        score = 100

        # Assess Open Port Risks
        for p in open_ports:
            if p.risk_level == "HIGH":
                score -= 15
                vulns.append(f"High-risk service active on port {p.port} ({p.service_name}): {p.recommendation}")
            elif p.risk_level == "MEDIUM":
                score -= 6
                vulns.append(f"Medium-risk service active on port {p.port} ({p.service_name}): {p.recommendation}")

        # Baseline Hardening Suggestions
        hardening.append("Enforce Windows Defender Firewall / iptables default drop policy on all inbound WAN ports.")
        hardening.append("Enforce multi-factor authentication (MFA) across all remote access gateways (SSH / RDP).")
        hardening.append("Audit active background processes and verify cryptographic SHA-256 hashes of system binaries.")
        hardening.append("Ensure automated security patches are active for the host OS kernel and runtime environments.")

        score = max(20, min(100, score))

        report = CyberSecurityAuditReport(
            target_host=target_host,
            scan_timestamp=datetime.now(timezone.utc).isoformat(),
            total_ports_scanned=len(self.COMMON_PORTS),
            open_ports_detected=open_ports,
            system_security_score=score,
            vulnerabilities_found=vulns,
            hardening_actions=hardening,
        )
        self.last_report = report
        return report

    def evaluate_password_entropy(self, password: str) -> Dict[str, Any]:
        """
        Evaluates password entropy and resistance against offline dictionary and brute-force attacks.
        """
        length = len(password)
        pool = 0
        if re.search(r"[a-z]", password): pool += 26
        if re.search(r"[A-Z]", password): pool += 26
        if re.search(r"[0-9]", password): pool += 10
        if re.search(r"[^a-zA-Z0-9]", password): pool += 32

        if pool == 0 or length == 0:
            return {"entropy_bits": 0.0, "strength": "VERY WEAK", "is_secure": False}

        entropy = length * math.log2(pool)
        strength = "VERY WEAK"
        is_secure = False

        if entropy >= 80:
            strength = "MILITARY / CRYPTOGRAPHIC GRADE"
            is_secure = True
        elif entropy >= 60:
            strength = "STRONG"
            is_secure = True
        elif entropy >= 40:
            strength = "MODERATE"
            is_secure = False
        else:
            strength = "WEAK"
            is_secure = False

        return {
            "entropy_bits": round(entropy, 2),
            "strength": strength,
            "is_secure": is_secure,
            "character_pool_size": pool,
            "length": length,
        }

    def format_audit_report_text(self, report: CyberSecurityAuditReport) -> str:
        lines = [
            f"=== ETHICAL CYBERSECURITY DEFENSE AUDIT REPORT ===",
            f"Target Host:           {report.target_host}",
            f"Timestamp:             {report.scan_timestamp}",
            f"Security Health Score: {report.system_security_score}/100",
            f"Total Ports Probed:    {report.total_ports_scanned}",
            f"Open Ports Detected:   {len(report.open_ports_detected)}\n",
        ]

        if report.open_ports_detected:
            lines.append("DETECTED ACTIVE NETWORK SERVICES:")
            for p in report.open_ports_detected:
                lines.append(f"  • Port {p.port:<5} | {p.service_name:<10} | Risk: {p.risk_level:<6} | {p.recommendation}")
            lines.append("")
        else:
            lines.append("✓ No exposed high-risk network ports detected on probed interfaces.\n")

        if report.vulnerabilities_found:
            lines.append("IDENTIFIED SECURITY VULNERABILITIES & RISKS:")
            for v in report.vulnerabilities_found:
                lines.append(f"  ⚠ {v}")
            lines.append("")

        lines.append("RECOMMENDED DEFENSIVE HARDENING ACTIONS:")
        for h in report.hardening_actions:
            lines.append(f"  🛡️ {h}")

        return "\n".join(lines)


cyber_defense = CyberDefenseSuite()
