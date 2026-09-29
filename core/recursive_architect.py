"""
Recursive Architect Coordinator (v14.0) for P.H.A.S.S.
Central orchestrator uniting:
1. Code Analyzer (static metrics & scoring)
2. Architecture Planner (LLM / heuristic planning with 70% confidence safety valve)
3. Code Generator (diff engine & sandbox isolation)
4. Evolution Validator (syntax, dependencies, pytest suites, 100-run benchmark)
5. Evolution Deployer (backup, hot deploy, module reload, 60s rollback watchdog, git commit)
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from core.code_analyzer import CodeAnalyzer, RefactorReport, code_analyzer
from core.architect_planner import ArchitectPlanner, ArchitecturePlan, architect_planner
from core.code_generator import CodeGenerator, GeneratedPatch, code_generator
from core.evolution_validator import EvolutionValidator, ValidationReport, evolution_validator
from core.evolution_deployer import EvolutionDeployer, EvolutionRecord, evolution_deployer

logger = logging.getLogger("phass.core.recursive_architect")


class RecursiveArchitect:
    """
    Master coordinator for autonomous codebase self-rewriting and evolution.
    """

    _instance: Optional[RecursiveArchitect] = None

    def __init__(
        self,
        analyzer: Optional[CodeAnalyzer] = None,
        planner: Optional[ArchitectPlanner] = None,
        generator: Optional[CodeGenerator] = None,
        validator: Optional[EvolutionValidator] = None,
        deployer: Optional[EvolutionDeployer] = None,
    ):
        self.analyzer = analyzer or code_analyzer
        self.planner = planner or architect_planner
        self.generator = generator or code_generator
        self.validator = validator or evolution_validator
        self.deployer = deployer or evolution_deployer

    @classmethod
    def get_instance(cls) -> RecursiveArchitect:
        if cls._instance is None:
            cls._instance = RecursiveArchitect()
        return cls._instance

    def analyze_codebase(self, scan_dirs: Optional[List[str]] = None) -> RefactorReport:
        """Runs static analysis across codebase and returns ranked RefactorReport."""
        logger.info("Initiating Recursive Architect static codebase scan...")
        return self.analyzer.scan_codebase(scan_dirs=scan_dirs)

    def upgrade_worst_module(
        self,
        scan_dirs: Optional[List[str]] = None,
        target_file_override: Optional[Union[str, Path]] = None,
        run_tests: bool = True,
        run_benchmark: bool = True,
    ) -> EvolutionRecord:
        """
        Executes complete autonomous self-rewriting pipeline:
        1. Identifies the worst-ranked module (or uses override).
        2. Synthesizes an ArchitecturePlan.
        3. Enforces 70% confidence safety valve.
        4. Generates patch diff and stages in sandbox.
        5. Validates (syntax, dependencies, unit tests, 100-run performance benchmark).
        6. Deploys hotfix, reloads module, arms 60s rollback watchdog, and auto-commits to Git.
        """
        logger.info("Executing Recursive Architect v14.0 self-rewriting pipeline...")

        # 1. Identify Target Module
        if target_file_override:
            target_metric = target_file_override
        else:
            report = self.analyze_codebase(scan_dirs=scan_dirs)
            if not report.ranked_files:
                return EvolutionRecord(
                    evolution_id="EVO-ABORTED",
                    target_file="none",
                    target_function="none",
                    status="FAILED",
                    speed_improvement_pct=0.0,
                    backup_path="",
                    patch_path="",
                    git_commit="",
                    message="No modules found to analyze or refactor.",
                )
            target_metric = report.ranked_files[0]

        # 2. Plan Refactoring
        plan = self.planner.plan_refactoring(target_metric)

        # 3. Safety Valve Gating
        if plan.escalate_to_user or plan.confidence < 0.70 or plan.status != "READY_FOR_GENERATION":
            logger.warning(f"Evolution aborted: Plan confidence is {plan.confidence*100:.1f}% (< 70%). Escalating to user.")
            return EvolutionRecord(
                evolution_id="EVO-SAFETY-HOLD",
                target_file=plan.target_file,
                target_function=plan.target_function,
                status="FAILED",
                speed_improvement_pct=0.0,
                backup_path="",
                patch_path="",
                git_commit="",
                message=f"Plan confidence is {plan.confidence*100:.1f}% (below 70% safety threshold). Escalated for user review.",
            )

        # 4. Generate Diff Patch & Sandbox File
        patch = self.generator.generate_patch(plan)

        # 5. Evolution Validation (Syntax, Deps, Tests, Benchmark)
        validation = self.validator.validate_patch(patch, run_tests=run_tests, run_benchmark=run_benchmark)
        if not validation.passed:
            logger.error(f"Evolution validation failed: {validation.details}")
            return EvolutionRecord(
                evolution_id="EVO-REJECTED",
                target_file=plan.target_file,
                target_function=plan.target_function,
                status="FAILED",
                speed_improvement_pct=validation.speed_improvement_pct,
                backup_path="",
                patch_path=patch.patch_path,
                git_commit="",
                message=f"Validation failed: {validation.details}",
            )

        # 6. Deploy Evolution, Reload Service, Commit to Git, Arm Watchdog
        record = self.deployer.deploy_evolution(patch, validation)
        logger.info(f"Evolution complete: {record.message}")
        return record

    def get_evolution_history(self) -> List[Dict[str, Any]]:
        """Returns history of all architectural evolutions."""
        return self.deployer.get_evolution_history()


recursive_architect = RecursiveArchitect.get_instance()
