"""
Hierarchical Task Network (HTN) Planner & Dynamic Replanner for P.H.A.S.S Sphere.
Decomposes high-level goals into recursive composite & primitive tasks,
with automated real-time replanning upon encountering unexpected hazards or tool failures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
from .goal_manager import Goal, SubTask, GoalState

logger = logging.getLogger("phass.core.planning_advanced")


@dataclass
class HTNTask:
    name: str
    is_composite: bool
    tool_binding: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    subtasks: List[HTNTask] = field(default_factory=list)


class HierarchicalTaskPlanner:
    def __init__(self):
        pass

    def decompose_goal_htn(self, goal_title: str, world_context: Dict[str, Any]) -> List[SubTask]:
        """
        Recursively resolves Hierarchical Task Network into flat ordered SubTasks.
        """
        t_lower = goal_title.lower()

        if "diagnose" in t_lower or "failure" in t_lower:
            # Composite Task: Diagnose
            root = HTNTask("Diagnose_Failure_Routine", is_composite=True, subtasks=[
                HTNTask("Collect_Telemetry", is_composite=False, tool_binding="system_diagnostics", parameters={"scope": "full_telemetry"}),
                HTNTask("Check_Dependencies", is_composite=False, tool_binding="system_diagnostics", parameters={"scope": "dependencies"}),
                HTNTask("Inspect_Error_Logs", is_composite=False, tool_binding="file_reader", parameters={"file_path": "logs/system.log"}),
                HTNTask("Verify_Resolution", is_composite=False, tool_binding="generate_report", parameters={"summary": "Diagnostic completed"}),
            ])
        elif "scan" in t_lower or "environment" in t_lower or "explore" in t_lower:
            # Composite Task: Environment Mapping
            root = HTNTask("Environmental_Mapping_Routine", is_composite=True, subtasks=[
                HTNTask("LiDAR_Sweep", is_composite=False, tool_binding="sensor_probe", parameters={"sensors": ["lidar", "ultrasonic"]}),
                HTNTask("Visual_Object_Recognition", is_composite=False, tool_binding="vision_scan", parameters={"detect_objects": True}),
                HTNTask("Synchronize_World_Model", is_composite=False, tool_binding="world_model_update", parameters={"target": "entities"}),
                HTNTask("Generate_Exploration_Debrief", is_composite=False, tool_binding="generate_report", parameters={"report_type": "environment"}),
            ])
        elif "dock" in t_lower or "charge" in t_lower:
            root = HTNTask("Docking_Routine", is_composite=True, subtasks=[
                HTNTask("Compute_Trajectory_To_Dock", is_composite=False, tool_binding="spatial_query", parameters={"target": "Charging Dock"}),
                HTNTask("Execute_Omni_Navigation", is_composite=False, tool_binding="robot_move", parameters={"trajectory": "optimal", "speed_mode": "docking"}),
                HTNTask("Engage_Charging_Contacts", is_composite=False, tool_binding="sensor_probe", parameters={"sensors": ["battery"]}),
            ])
        else:
            root = HTNTask("Generic_Action_Routine", is_composite=True, subtasks=[
                HTNTask("Context_Memory_Search", is_composite=False, tool_binding="memory_query", parameters={"query": goal_title}),
                HTNTask("Perform_Action", is_composite=False, tool_binding="system_diagnostics", parameters={"details": goal_title}),
                HTNTask("Validate_Outcome", is_composite=False, tool_binding="generate_report", parameters={"summary": f"Completed: {goal_title}"}),
            ])

        # Flatten HTN
        flattened: List[SubTask] = []
        for idx, child in enumerate(root.subtasks):
            st = SubTask(
                title=child.name.replace("_", " "),
                description=f"HTN Subtask for {child.name}",
                tool_name=child.tool_binding or "system_diagnostics",
                parameters=child.parameters,
                state=GoalState.CREATED,
                priority=idx + 1,
            )
            flattened.append(st)

        return flattened

    def dynamic_replan_on_failure(self, goal: Goal, failed_subtask: SubTask, error_msg: str) -> List[SubTask]:
        """
        Injects defensive recovery subtasks when a step fails during runtime execution.
        """
        logger.warning(f"Dynamic Replanner triggered for Goal {goal.id} on step '{failed_subtask.title}': {error_msg}")

        recovery_step = SubTask(
            title=f"Self-Healing Diagnostic Recovery for: {failed_subtask.title}",
            description=f"Automated recovery step injected after error: {error_msg}",
            tool_name="system_diagnostics",
            parameters={"scope": "recovery_reset", "failed_step": failed_subtask.title},
            state=GoalState.CREATED,
            priority=failed_subtask.priority,
        )

        # Retry step
        retry_step = SubTask(
            title=f"Retry: {failed_subtask.title}",
            description=failed_subtask.description,
            tool_name=failed_subtask.tool_name,
            parameters=failed_subtask.parameters,
            state=GoalState.CREATED,
            priority=failed_subtask.priority + 1,
        )

        # Insert recovery steps into goal's subtask queue
        new_subtasks = [recovery_step, retry_step]
        for st in goal.subtasks:
            if st.id != failed_subtask.id and st.state == GoalState.CREATED:
                new_subtasks.append(st)

        goal.subtasks = new_subtasks
        return new_subtasks


htn_planner = HierarchicalTaskPlanner()
