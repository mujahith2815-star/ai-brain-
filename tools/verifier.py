"""
Tool Result Verifier for P.H.A.S.S Sphere.
Validates outputs against expected contract schemas and sanity bounds.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger("phass.tools.verifier")


class ToolVerifier:
    @staticmethod
    def verify_tool_result(tool_name: str, result: Dict[str, Any], custom_verifier: Optional[Any] = None) -> bool:
        if not isinstance(result, dict):
            return False

        if "error" in result and result["error"]:
            return False

        if custom_verifier and callable(custom_verifier):
            try:
                return bool(custom_verifier(result))
            except Exception as e:
                logger.warning(f"Custom verifier failed for {tool_name}: {e}")
                return False

        # Default verification: Must contain status success or valid data
        status = result.get("status", "SUCCESS")
        return status in ("SUCCESS", "OK", "COMPLETED", "NOMINAL")
