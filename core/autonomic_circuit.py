"""
Autonomic Error Recovery Circuit Coordinator for P.H.A.S.S.
Provides closed-loop detection, diagnosis, fix synthesis, sandbox validation,
hot deployment, service rebooting, and 60-second crash rollback protection.
"""

from __future__ import annotations
import logging
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from core.error_analyzer import AnalyzedError, error_analyzer
from core.fix_generator import GeneratedFix, fix_generator
from core.fix_validator import ValidationResult, sandbox_validator
from core.rollback_manager import DeploymentResult, rollback_manager

logger = logging.getLogger("phass.core.autonomic_circuit")


@dataclass
class HealResult:
    success: bool
    target_file: Optional[str] = None
    analyzed_error: Optional[AnalyzedError] = None
    generated_fix: Optional[GeneratedFix] = None
    validation_result: Optional[ValidationResult] = None
    deployment_result: Optional[DeploymentResult] = None
    rolled_back: bool = False
    escalated_to_user: bool = False
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "target_file": self.target_file,
            "analyzed_error": self.analyzed_error.to_dict() if self.analyzed_error else None,
            "generated_fix": self.generated_fix.to_dict() if self.generated_fix else None,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
            "deployment_result": self.deployment_result.to_dict() if self.deployment_result else None,
            "rolled_back": self.rolled_back,
            "escalated_to_user": self.escalated_to_user,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class AutonomicCircuit:
    """
    Central coordinator of the P.H.A.S.S Autonomic Error Recovery Circuit.
    Executes:
    1. Error Capture & Classification (ErrorAnalyzer)
    2. Proactive Alerting (ProactiveMonitor)
    3. Patch Synthesis & Safety Valve (FixGenerator)
    4. Isolated Sandbox Testing (SandboxValidator)
    5. Hot Deployment & Service Restart (RollbackManager)
    6. Post-Deployment Guard Window & Rollback (RollbackManager)
    """

    _instance: Optional[AutonomicCircuit] = None

    def __init__(self):
        self.error_analyzer = error_analyzer
        self.fix_generator = fix_generator
        self.sandbox_validator = sandbox_validator
        self.rollback_manager = rollback_manager

    @classmethod
    def get_instance(cls) -> AutonomicCircuit:
        if cls._instance is None:
            cls._instance = AutonomicCircuit()
        return cls._instance

    def heal_runtime_error(
        self,
        error_or_text: Union[Exception, str],
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        code_context: Optional[str] = None,
        traceback_str: Optional[str] = None,
        run_tests: bool = True,
        canary_fn: Optional[Callable[[], Any]] = None,
    ) -> HealResult:
        """
        Closed-loop recovery pipeline:
        Diagnoses, synthesizes, validates in sandbox, and deploys hotfix with rollback protection.
        """
        logger.info(f"Initiating autonomic error recovery circuit for: {error_or_text}")

        # 1. Error Analysis & Similarity Matching
        if isinstance(error_or_text, Exception):
            err_type = type(error_or_text).__name__
            err_msg = str(error_or_text)
            tb = traceback_str or traceback.format_exc()
            analyzed = self.error_analyzer.analyze_error(
                error_type=err_type,
                error_msg=err_msg,
                file_path=file_path,
                line_number=line_number,
                code_context=code_context,
                traceback_str=tb,
            )
        else:
            analyzed = self.error_analyzer.analyze_log_entry(
                error_text=str(error_or_text),
                file_path=file_path,
                line_number=line_number,
                code_context=code_context,
                traceback_str=traceback_str,
            )

        target_file = analyzed.file_path or file_path
        if not target_file:
            msg = "Autonomous recovery aborted: Target file path could not be identified."
            logger.error(msg)
            return HealResult(
                success=False,
                analyzed_error=analyzed,
                message=msg,
            )

        module_name = Path(target_file).name

        # 2. Proactive Alerting
        try:
            from core.proactive_monitor import proactive_monitor
            proactive_monitor.alert_autonomic_fix(module_name)
        except Exception as e:
            logger.debug(f"Proactive alert notice: {e}")

        # 3. Fix Synthesis & Safety Valve Check
        fix = self.fix_generator.generate_fix(analyzed)

        if fix.escalate_to_user or fix.confidence < 0.70 or fix.status != "READY_FOR_SANDBOX":
            self.rollback_manager.record_pending_review(fix)
            msg = (
                f"Fix confidence is {fix.confidence*100:.1f}% (below 70.0% threshold). "
                f"Escalating to user review without modifying disk."
            )
            logger.warning(f"[Autonomic Circuit Safety Valve] {msg}")
            return HealResult(
                success=False,
                target_file=target_file,
                analyzed_error=analyzed,
                generated_fix=fix,
                escalated_to_user=True,
                message=msg,
            )

        # 4. Sandbox Isolation & Validation (AST + py_compile + pytest)
        val_res = self.sandbox_validator.validate_fix(fix, run_tests=run_tests)
        if not val_res.passed:
            record = {
                "action": "SANDBOX_VALIDATION_FAILED",
                "target_file": target_file,
                "error": val_res.error_message,
            }
            self.rollback_manager.increment_metric("pending_review", 1, record)
            msg = f"Candidate patch failed sandbox validation: {val_res.error_message}. Live files untouched."
            logger.error(f"[Autonomic Circuit Sandbox] {msg}")
            return HealResult(
                success=False,
                target_file=target_file,
                analyzed_error=analyzed,
                generated_fix=fix,
                validation_result=val_res,
                message=msg,
            )

        # 5. Hot Deployment & Module/Service Reload
        dep_res = self.rollback_manager.deploy_fix(fix, validation_result=val_res)
        if not dep_res.success:
            msg = f"Deployment failed: {dep_res.message}"
            logger.error(f"[Autonomic Circuit Deploy] {msg}")
            return HealResult(
                success=False,
                target_file=target_file,
                analyzed_error=analyzed,
                generated_fix=fix,
                validation_result=val_res,
                deployment_result=dep_res,
                message=msg,
            )

        # 6. Post-Deployment Canary Verification (if callable provided)
        if canary_fn:
            try:
                canary_fn()
                logger.info(f"Canary check succeeded for {target_file}.")
            except Exception as canary_err:
                logger.error(f"Canary check failed after deployment ({canary_err}). Triggering rollback!")
                rolled_back = self.rollback_manager.trigger_rollback(target_file, reason=str(canary_err))
                return HealResult(
                    success=False,
                    target_file=target_file,
                    analyzed_error=analyzed,
                    generated_fix=fix,
                    validation_result=val_res,
                    deployment_result=dep_res,
                    rolled_back=rolled_back,
                    message=f"Post-deploy canary check failed ({canary_err}). Rolled back to backup.",
                )

        msg = (
            f"Autonomous self-healing completed for {module_name}: "
            f"Fix deployed with backup {Path(dep_res.backup_path).name if dep_res.backup_path else 'created'}."
        )
        logger.info(f"[Autonomic Circuit Success] {msg}")
        return HealResult(
            success=True,
            target_file=target_file,
            analyzed_error=analyzed,
            generated_fix=fix,
            validation_result=val_res,
            deployment_result=dep_res,
            message=msg,
        )

    def get_circuit_status(self) -> Dict[str, Any]:
        """Returns live status of the recovery circuit, including metrics and active deployments."""
        metrics = self.rollback_manager.get_metrics()
        return {
            "status": "ARMED",
            "active_deployments": len(self.rollback_manager.active_deployments),
            "errors_fixed_today": metrics.get("errors_fixed_today", 0),
            "pending_review": metrics.get("pending_review", 0),
            "rollbacks": metrics.get("rollbacks", 0),
            "recent_actions": metrics.get("history", [])[-5:],
        }


autonomic_circuit = AutonomicCircuit.get_instance()
