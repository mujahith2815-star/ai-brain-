# Orvix Sphere API Reference

## Knowledge Store (`knowledge.sqlite_store`)
- `KnowledgeStore.store_fact(key, value, category)`
- `KnowledgeStore.get_fact(key) -> FactResult`
- `KnowledgeStore.add_list_item(list_name, item, quantity, notes)`
- `KnowledgeStore.get_list(list_name) -> ListResult`
- `KnowledgeStore.log_task_execution(task_name, action, result, approved)`
- `KnowledgeStore.queue_approval(action_name, reason, tool, args)`
- `KnowledgeStore.get_pending_approvals()`
- `KnowledgeStore.resolve_approval(action_id, approve)`

## Safety Guard (`proactive.safety`)
- `SafetyGuard.validate_action(tool_name, args) -> (allowed: bool, reason: str)`
- `SafetyGuard.is_destructive(tool_name, args) -> bool`
- `SafetyGuard.audit_log(action, decision, reason)`

## Task Scheduler (`proactive.scheduler`)
- `TaskScheduler.add_task(name, cron_expr, action_fn, args, enabled)`
- `TaskScheduler.remove_task(name)`
- `TaskScheduler.pause_all()`
- `TaskScheduler.resume_all()`
- `TaskScheduler.list_tasks() -> List[Dict]`

## Autonomous Agent (`proactive.autonomous_agent`)
- `AutonomousAgent.execute_action(name, tool, args, requires_approval)`
- `AutonomousAgent.propose_action(name, reason, tool, args)`
- `AutonomousAgent.approve_action(action_id)`
- `AutonomousAgent.reject_action(action_id)`
- `AutonomousAgent.get_approval_queue()`
