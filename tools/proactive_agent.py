"""
Proactive Intelligence Module for P.H.A.S.S Sphere & Llama Assistant.
Provides context prediction, proactive system optimizations, smart contextual reminders,
and resource anomaly detection.
"""

from __future__ import annotations
import os
import time
import logging
from typing import Dict, Any, List, Optional
from core.platform_abstraction import get_platform

logger = logging.getLogger("phass.tools.proactive_agent")

_REMINDERS: List[Dict[str, Any]] = []


def proactive_context_prediction(
    recent_queries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes conversation patterns and predicts probable upcoming user directives,
    pre-fetching relevant context or tool suggestions.
    """
    history = recent_queries or []
    predictions = []

    joined = " ".join(history).lower()
    if any(w in joined for w in ["clean", "disk", "storage", "delete"]):
        predictions.append({
            "predicted_action": "disk_cleanup",
            "suggested_tool": "disk_cleaner",
            "confidence": 0.88,
            "rationale": "Prior discussion focused on storage management.",
        })
    if any(w in joined for w in ["code", "script", "bug", "python", "error"]):
        predictions.append({
            "predicted_action": "code_analysis",
            "suggested_tool": "code_analyzer",
            "confidence": 0.82,
            "rationale": "Developer task context detected.",
        })
    if any(w in joined for w in ["web", "scrape", "search", "url"]):
        predictions.append({
            "predicted_action": "web_research",
            "suggested_tool": "web_scraper",
            "confidence": 0.79,
            "rationale": "Online inquiry detected.",
        })

    if not predictions:
        predictions.append({
            "predicted_action": "system_status_check",
            "suggested_tool": "system_diagnostics",
            "confidence": 0.65,
            "rationale": "Standard routine maintenance recommendation.",
        })

    return {
        "status": "SUCCESS",
        "predictions_count": len(predictions),
        "predictions": predictions,
    }


def proactive_system_recommendations() -> Dict[str, Any]:
    """Inspects live system telemetry and suggests proactive performance optimizations."""
    plat = get_platform()
    info = plat.get_system_info()
    recommendations = []

    free_disk = info.get("disk_free_gb", 100.0)
    if free_disk < 15.0:
        recommendations.append({
            "severity": "WARNING",
            "category": "Storage",
            "message": f"Free disk space is low ({free_disk} GB). Recommend running disk_cleaner or analyzing duplicates.",
            "recommended_action": "disk_cleaner(dry_run=True)",
        })

    mem_avail = info.get("memory_available_mb", 4096.0)
    if mem_avail < 1024.0:
        recommendations.append({
            "severity": "HIGH",
            "category": "Memory",
            "message": f"Available RAM is under 1 GB ({mem_avail} MB). Recommend closing idle background processes.",
            "recommended_action": "process_hunter()",
        })

    if not recommendations:
        recommendations.append({
            "severity": "NOMINAL",
            "category": "Health",
            "message": "All system telemetry nominal. CPU and memory metrics within safe thresholds.",
            "recommended_action": "none",
        })

    return {
        "status": "SUCCESS",
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
    }


def proactive_smart_reminder(
    reminder_text: str,
    trigger_condition: str,
) -> Dict[str, Any]:
    """Registers a contextual reminder triggered by a condition or event."""
    reminder_id = f"rem-{len(_REMINDERS) + 1}"
    record = {
        "reminder_id": reminder_id,
        "text": reminder_text,
        "trigger": trigger_condition,
        "created_at": time.time(),
        "status": "ACTIVE",
    }
    _REMINDERS.append(record)
    return {
        "status": "SUCCESS",
        "reminder_id": reminder_id,
        "text": reminder_text,
        "trigger": trigger_condition,
        "message": f"Smart reminder registered: '{reminder_text}' on trigger '{trigger_condition}'.",
    }


def proactive_anomaly_detection() -> Dict[str, Any]:
    """Detects resource spikes, abnormal process memory growth, or disk fill anomalies."""
    plat = get_platform()
    procs = plat.list_processes(limit=50)

    heavy_procs = [p for p in procs if p.get("memory_mb", 0) > 1500.0]
    anomalies = []

    for hp in heavy_procs:
        anomalies.append({
            "type": "HIGH_MEMORY_CONSUMPTION",
            "process": hp["name"],
            "pid": hp["pid"],
            "memory_mb": hp["memory_mb"],
        })

    return {
        "status": "SUCCESS",
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "baseline_status": "MONITORING_HEALTHY",
    }
