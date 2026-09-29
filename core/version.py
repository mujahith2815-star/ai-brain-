"""
P.H.A.S.S SPHERE — System Version & Release Metadata
"""

VERSION = "8.0.0"
VERSION_CODENAME = "Apex Nexus Singularity"
RELEASE_DATE = "2026-08-30"
ARCHITECTURE = "Frontier Neural AI Training (DPO + SFT + EWC + Self-Play), 3D WebGL HUD, Multi-Device Mesh & Cyber Shield"

def get_version_banner() -> str:
    return (
        f"=======================================================\n"
        f"    P.H.A.S.S SPHERE v{VERSION} — {VERSION_CODENAME.upper()}\n"
        f"    {ARCHITECTURE}\n"
        f"======================================================="
    )
