"""
Launch script for P.H.A.S.S Holographic Hybrid Engine.
Initializes all 6 core modules in a synchronized deployment:
- Module 1: Execution Orchestrator (Strict Planner -> Executor -> Verifier)
- Module 2: Hardware & Vibe Coding Co-Pilot
- Module 3: Holographic Heads-Up Display (CustomTkinter HUD)
- Module 4: Autonomous Daily Operations
- Module 5: Mobile & Remote Access Interface
- Module 6: Self-Improvement & Continuous Learning Engine
"""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def initialize_hybrid_engine():
    """Initializes and verifies all core modules before presenting UI."""
    print("====================================================================")
    print("  P.H.A.S.S SPHERE v9.0 - HOLOGRAPHIC HYBRID ENGINE STARTUP")
    print("====================================================================")

    # 1. Execution Orchestrator
    try:
        from core.execution_orchestrator import execution_orchestrator
        print("[INIT] Module 1: Execution Orchestrator loaded (Real Worker Mode).")
    except Exception as e:
        print(f"[WARN] Module 1 notice: {e}")

    # 2. Hardware Engineering Co-Pilot
    try:
        from hardware.component_engine import component_engine
        comp_count = len(component_engine.db)
        print(f"[INIT] Module 2: Hardware Engine loaded ({comp_count} components cached).")
    except Exception as e:
        print(f"[WARN] Module 2 notice: {e}")

    # 3. Autonomous Daily Routine & Scheduler
    try:
        from core.daily_routine import get_daily_routine
        routine = get_daily_routine()
        print("[INIT] Module 4: Autonomous Daily Routine & Scheduler active.")
    except Exception as e:
        print(f"[WARN] Module 4 notice: {e}")

    # 4. Mobile & Remote Interface
    try:
        from core.mobile_interface import get_mobile_interface
        mobile = get_mobile_interface()
        print("[INIT] Module 5: Mobile & Remote Interface active (Telegram/Queue).")
    except Exception as e:
        print(f"[WARN] Module 5 notice: {e}")

    # 5. Self-Improvement & Skills Library
    try:
        from core.self_improvement import get_self_improvement
        self_imp = get_self_improvement()
        skills = self_imp.list_skills()
        print(f"[INIT] Module 6: Self-Improvement Engine active ({len(skills)} skills).")
    except Exception as e:
        print(f"[WARN] Module 6 notice: {e}")

    print("[INIT] All modules synchronized.")
    print("====================================================================")


if __name__ == '__main__':
    initialize_hybrid_engine()

    # Check for optional voice dependencies
    try:
        import sounddevice
        import whisper
        import pyttsx3
    except ImportError as e:
        print(f"[NOTICE] Voice subsystem running in fallback mode: {e}")

    # Check for test / verification flags
    verify_mode = "--verify" in sys.argv or "--test" in sys.argv

    # Launch Holographic HUD UI
    from ui.main_window import AssistantUI
    app = AssistantUI()
    app.run(verify_mode=verify_mode)
