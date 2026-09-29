"""
Legacy compatibility alias for phass_cli.py (P.H.A.S.S CLI).
"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).parent / "phass_cli.py"
    runpy.run_path(str(target), run_name="__main__")
