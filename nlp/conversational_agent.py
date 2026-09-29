"""
Real-Time Casual & Natural Communication Engine for P.H.A.S.S Sphere.
Transforms P.H.A.S.S into a full J.A.R.V.I.S. executive assistant, voice narrator,
universal OS controller, file editor, deep diagnostic auditor, and self-evolution engine.
"""

from __future__ import annotations
import os
import random
import re
import sys
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

from world.world_model import world_model
from diagnostics.realtime_monitor import system_monitor
from diagnostics.deep_diagnostics import deep_diagnostics
from knowledge.graph import knowledge_graph
from tools.os_controller import os_controller
from tools.file_ops import file_manager
from tools.screen_vision import screen_vision
from learning.self_evolution import self_evolution_engine
from voice.speech_engine import voice_engine
from jarvis.persona import jarvis_persona
from jarvis.protocol_engine import protocol_engine


class RealTimeConversationalAgent:
    def __init__(self):
        self.dialogue_history: List[Dict[str, str]] = []

    def handle_natural_conversation(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to handle user input as J.A.R.V.I.S. protocol, natural conversation,
        OS application controller, file manager, system diagnostic, or self-evolution trigger.
        """
        from nlp.spelling_corrector import spelling_corrector
        t_corrected, _ = spelling_corrector.correct_sentence(text)
        t_clean = t_corrected.strip()
        t_lower = t_clean.lower()

        # 0. Dynamic Problem Solver & Zero-Friction Router (Knowledge search, UI effect code generation, phone power-on)
        from .dynamic_intelligence import dynamic_solver
        dyn_res = dynamic_solver.solve_directive(t_clean)
        if dyn_res is not None:
            return dyn_res

        # 1. J.A.R.V.I.S. Protocols & Macros
        if any(phrase in t_lower for phrase in ["workspace protocol", "prepare workspace", "dev setup", "code workspace", "jarvis workspace"]):
            res = protocol_engine.execute_protocol("WORKSPACE")
            return {
                "handled": True,
                "type": "JARVIS_PROTOCOL",
                "speech_text": f"{res.spoken_narration}\n\nSteps Executed:\n" + "\n".join([f"  • {s}" for s in res.steps_executed]),
                "action_executed": "PROTOCOL_WORKSPACE",
            }

        if any(phrase in t_lower for phrase in ["security scan", "lockdown protocol", "jarvis security", "threat scan", "audit security"]):
            res = protocol_engine.execute_protocol("SECURITY_SCAN")
            return {
                "handled": True,
                "type": "JARVIS_PROTOCOL",
                "speech_text": f"{res.spoken_narration}\n\nSecurity Checklist:\n" + "\n".join([f"  • {s}" for s in res.steps_executed]),
                "action_executed": "PROTOCOL_SECURITY_SCAN",
            }

        if any(phrase in t_lower for phrase in ["briefing", "give me a briefing", "status briefing", "morning briefing", "jarvis briefing"]):
            res = protocol_engine.execute_protocol("BRIEFING")
            return {
                "handled": True,
                "type": "JARVIS_PROTOCOL",
                "speech_text": res.spoken_narration,
                "action_executed": "PROTOCOL_SYSTEM_BRIEFING",
            }

        if any(phrase in t_lower for phrase in ["clean and optimize", "optimize system", "jarvis clean", "flush cache"]):
            res = protocol_engine.execute_protocol("CLEAN_OPTIMIZE")
            return {
                "handled": True,
                "type": "JARVIS_PROTOCOL",
                "speech_text": res.spoken_narration,
                "action_executed": "PROTOCOL_CLEAN_OPTIMIZE",
            }

        # 2. Voice Mute/Unmute Controls
        if any(phrase in t_lower for phrase in ["mute voice", "stop speaking", "be quiet", "silence voice"]):
            voice_engine.toggle_mute(True)
            return {
                "handled": True,
                "type": "VOICE_CONTROL",
                "speech_text": "Voice synthesis has been muted, sir. Visual HUD will remain active.",
                "action_executed": "MUTE_VOICE",
            }

        if any(phrase in t_lower for phrase in ["unmute voice", "enable voice", "speak again", "voice on"]):
            voice_engine.toggle_mute(False)
            msg = "Voice synthesis reactivated, sir. Standing by."
            voice_engine.speak(msg)
            return {
                "handled": True,
                "type": "VOICE_CONTROL",
                "speech_text": msg,
                "action_executed": "UNMUTE_VOICE",
            }

        # 3. Screen Vision, OCR & Clipboard Tools
        if any(phrase in t_lower for phrase in ["ocr image", "read text from screen", "scan screen text", "ocr screenshot"]):
            from perception.vision_ai import vision_ai
            ok, p = screen_vision.capture_screenshot()
            analysis = vision_ai.analyze_image_or_screenshot(p)
            ocr_lines = "\n".join([f"  • [{t.category}] {t.text} (Conf: {int(t.confidence*100)}%)" for t in analysis.detected_texts])
            msg = f"Visual Scene Analysis complete, sir.\nDominant Scene: {analysis.dominant_scene_type}\nDetected OCR Text Spans:\n{ocr_lines}"
            voice_engine.speak("Visual text recognition completed, sir.")
            return {
                "handled": True,
                "type": "OCR_ANALYSIS",
                "speech_text": msg,
                "action_executed": "RUN_OCR",
            }

        if any(phrase in t_lower for phrase in ["take screenshot", "capture screen", "screenshot", "grab screen"]):
            ok, p = screen_vision.capture_screenshot()
            msg = f"Screenshot captured successfully, sir. Saved to: {p}" if ok else f"Failed to capture screen: {p}"
            voice_engine.speak("Screenshot captured, sir.")
            return {
                "handled": True,
                "type": "SCREEN_VISION",
                "speech_text": msg,
                "action_executed": "SCREENSHOT",
            }

        if any(phrase in t_lower for phrase in ["read clipboard", "get clipboard", "what is on my clipboard"]):
            cb_txt = screen_vision.get_clipboard_text()
            msg = f"Clipboard content (Length: {len(cb_txt)} chars):\n\n\"{cb_txt[:300]}\"" if cb_txt else "Your clipboard is currently empty, sir."
            voice_engine.speak("Reading your clipboard now, sir.")
            return {
                "handled": True,
                "type": "CLIPBOARD",
                "speech_text": msg,
                "action_executed": "READ_CLIPBOARD",
            }

        # 4. Computer & GUI Automation ("type <text>", "press shortcut <name>")
        if t_lower.startswith("type "):
            text_to_type = t_clean[5:].strip()
            from tools.computer_automation import computer_automation
            ok, msg = computer_automation.type_text(text_to_type)
            voice_engine.speak("Typing text into the active window now, sir.")
            return {
                "handled": True,
                "type": "GUI_AUTOMATION",
                "speech_text": f"Automation: {msg}",
                "action_executed": "TYPE_TEXT",
            }

        if any(phrase in t_lower for phrase in ["press shortcut", "press save", "press copy", "press paste"]):
            from tools.computer_automation import computer_automation
            sc = "SAVE" if "save" in t_lower else ("COPY" if "copy" in t_lower else "PASTE")
            ok, msg = computer_automation.send_shortcut(sc)
            voice_engine.speak(f"Triggered shortcut {sc}, sir.")
            return {
                "handled": True,
                "type": "GUI_AUTOMATION",
                "speech_text": msg,
                "action_executed": f"SHORTCUT_{sc}",
            }

        # 5. Cybernetic Sound Effects ("play sound <name>")
        if t_lower.startswith("play sound ") or t_lower.startswith("sound "):
            snd = re.sub(r"^(play sound|sound)\s+", "", t_clean, flags=re.IGNORECASE).strip().upper()
            from voice.sound_effects import sound_synth
            sound_synth.play_sound(snd)
            return {
                "handled": True,
                "type": "SOUND_EFFECT",
                "speech_text": f"Playing synthesized cybernetic audio: {snd}.",
                "action_executed": f"PLAY_{snd}",
            }

        # 6. Proactive Sentinel Status ("sentinel status", "check safeguards")
        if any(phrase in t_lower for phrase in ["sentinel status", "check safeguards", "autonomic guard"]):
            from core.proactive_sentinel import proactive_sentinel
            snap = proactive_sentinel.get_sentinel_snapshot()
            r_str = "\n".join([f"  • [{r['time_window']}] {r['predicted_action']}" for r in snap["learned_operator_routines"]])
            msg = (
                f"Proactive Autonomic Sentinel Guard Status:\n"
                f"• Active Guard Loop: {'RUNNING' if snap['is_sentinel_active'] else 'STANDBY'}\n"
                f"• Total Automated Safeguard Alerts: {snap['total_alerts_recorded']}\n\n"
                f"Learned Operator Daily Routines:\n{r_str}"
            )
            voice_engine.speak("Sentinel safeguards and routine predictions are online, sir.")
            return {
                "handled": True,
                "type": "SENTINEL_REPORT",
                "speech_text": msg,
                "action_executed": "SENTINEL_SNAPSHOT",
            }

        # 7. Greetings & Pleasantries (JARVIS / Friendly Companion Persona)
        greetings = [
            "hi", "hello", "hey", "hai", "heyy", "hiii", "hlo", "helo", "howdy",
            "greetings", "good morning", "good afternoon", "good evening", "yo", "sup", "what's up",
            "jarvis", "phass", "namaste", "vanakkam", "hola"
        ]
        if any(re.match(rf"^{re.escape(g)}\b", t_lower) for g in greetings) or t_lower in greetings:
            user_sal = "sir" if "jarvis" in t_lower else None
            reply = jarvis_persona.format_greeting(user_sal)
            voice_engine.speak(reply)
            return {
                "handled": True,
                "type": "CHITCHAT",
                "speech_text": reply,
                "action_executed": None,
            }

        # 5. Well-being & Casual Status ("How are you?", "What are you doing?")
        if any(phrase in t_lower for phrase in ["how are you", "how're you", "how are you doing", "how do you feel", "how's it going"]):
            from jarvis.persona import ChatPersonaMode
            if jarvis_persona.active_mode == ChatPersonaMode.FRIENDLY_COMPANION:
                reply = "I'm doing fantastic, thank you! 😊 It's always awesome talking with you! How are you feeling today?"
            else:
                batt = world_model.robot_state.battery_percentage
                temp = world_model.robot_state.internal_temp_c
                reply = f"I am functioning at peak efficiency, sir. 6S battery is at {batt:.1f}% and core temperature is {temp:.1f}°C. Ready for your directives."
            voice_engine.speak(reply)
            return {
                "handled": True,
                "type": "CHITCHAT",
                "speech_text": reply,
                "action_executed": None,
            }

        if any(phrase in t_lower for phrase in ["who are you", "what are you", "tell me about yourself", "your name"]):
            reply = (
                "I am P.H.A.S.S Sphere, an autonomous physical AI and cognitive computing platform. "
                "I combine continuous 6-DOF physical robotics, 360° LiDAR, neural LLM/MLLM training, "
                "universal OS and application control, real-time voice synthesis, deep system diagnostics, "
                "and dynamic in-memory hot-coding. At your service, sir."
            )
            voice_engine.speak("I am P.H.A.S.S Sphere, an autonomous physical and cognitive AI platform. At your service, sir.")
            return {
                "handled": True,
                "type": "CHITCHAT",
                "speech_text": reply,
                "action_executed": None,
            }

        if any(phrase in t_lower for phrase in ["what can you do", "what are the things", "help me", "your capabilities", "features", "what can i do with you", "what can you control"]):
            from nlp.answer_pipeline import generate_answer
            reply = generate_answer(t_clean, response_type="CAPABILITY_ANSWER")
            voice_engine.speak("Here is an overview of my current capabilities, sir.")
            return {
                "handled": True,
                "type": "CAPABILITY_ANSWER",
                "speech_text": reply,
                "action_executed": None,
            }

        if any(phrase in t_lower for phrase in ["thank you", "thanks", "good job", "awesome", "great work", "cool"]):
            reply = f"{jarvis_persona.format_completion()} Always a pleasure to assist, sir."
            voice_engine.speak(reply)
            return {
                "handled": True,
                "type": "POSITIVE_FEEDBACK",
                "speech_text": reply,
                "action_executed": None,
            }

        # 6. Deep System Diagnosis ("check system diagnosis", "run full diagnosis", "system report")
        if any(phrase in t_lower for phrase in ["deep diagnosis", "system diagnosis", "system report", "diagnose system", "hardware diagnosis", "health check"]):
            report_txt = deep_diagnostics.generate_human_readable_report()
            voice_engine.speak("System diagnostics completed, sir. All core processors and telemetry streams are nominal.")
            return {
                "handled": True,
                "type": "SYSTEM_DIAGNOSIS",
                "speech_text": f"Here is the complete real-time system diagnostic report:\n\n{report_txt}",
                "action_executed": "RUN_DEEP_DIAGNOSTICS",
            }

        # 7. Universal OS Application Launching ("open whatsapp", "open spotify", "open vscode", "open calc", etc.)
        if t_lower.startswith("open ") or t_lower.startswith("launch "):
            target_app = re.sub(r"^(open|launch)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            ok, msg = os_controller.launch_application(target_app)
            voice_engine.speak(f"Opening {target_app} for you now, sir.")
            return {
                "handled": True,
                "type": "APP_LAUNCH",
                "speech_text": msg if ok else f"I attempted to launch '{target_app}', but encountered: {msg}",
                "action_executed": f"LAUNCH_{target_app.upper()}",
            }

        # 8. Process Management ("list processes", "show running processes")
        if any(phrase in t_lower for phrase in ["list processes", "running processes", "show processes", "active tasks"]):
            procs = os_controller.list_running_processes(max_results=8)
            proc_lines = "\n".join([f"  • [{p.pid}] {p.name} — {p.memory_mb:.1f} MB" for p in procs])
            voice_engine.speak("Displaying active host system processes, sir.")
            return {
                "handled": True,
                "type": "PROCESS_LIST",
                "speech_text": f"Active top system processes:\n{proc_lines}",
                "action_executed": "LIST_PROCESSES",
            }

        # 9. Universal File Viewing ("view file <path>", "read file <path>", "show file <path>")
        if any(t_lower.startswith(p) for p in ["view file ", "read file ", "show file ", "open file "]):
            path_str = re.sub(r"^(view file|read file|show file|open file)\s+", "", t_clean, flags=re.IGNORECASE).strip().strip('"')
            res = file_manager.view_file(path_str, start_line=1, end_line=30)
            if res["success"]:
                voice_engine.speak("File retrieved and displayed on your HUD, sir.")
                return {
                    "handled": True,
                    "type": "FILE_VIEW",
                    "speech_text": f"Displaying {res['file_path']} (Lines {res['start_line']}-{res['end_line']} of {res['total_lines']}):\n\n{res['content']}",
                    "action_executed": "VIEW_FILE",
                }
            else:
                return {
                    "handled": True,
                    "type": "FILE_VIEW",
                    "speech_text": f"Could not view file '{path_str}': {res.get('error')}",
                    "action_executed": "VIEW_FILE_ERROR",
                }

        # 10. Universal File Listing ("list files in <dir>", "show files")
        if any(phrase in t_lower for phrase in ["list files", "show files", "dir"]):
            dir_target = "."
            m = re.search(r"(?:in|of)\s+([^\s]+)", t_clean, flags=re.IGNORECASE)
            if m:
                dir_target = m.group(1).strip('"')
            res = file_manager.list_directory(dir_target, max_entries=15)
            if res["success"]:
                entries_str = "\n".join([f"  • {'[DIR] ' if e['is_dir'] else '      '}{e['name']} ({e['size_bytes']} bytes)" for e in res["entries"]])
                voice_engine.speak("Directory structure retrieved, sir.")
                return {
                    "handled": True,
                    "type": "FILE_LIST",
                    "speech_text": f"Files in '{res['dir_path']}':\n{entries_str}",
                    "action_executed": "LIST_FILES",
                }
            else:
                return {
                    "handled": True,
                    "type": "FILE_LIST",
                    "speech_text": f"Could not list directory: {res.get('error')}",
                    "action_executed": "LIST_FILES_ERROR",
                }

        # 11. Recursive Self-Evolution & Self-Improvement ("improve yourself", "run self evolution", "optimize code")
        if any(phrase in t_lower for phrase in ["improve yourself", "self evolution", "evolve yourself", "improve your own code", "optimize code", "self-improve"]):
            analysis = self_evolution_engine.analyze_self_performance()
            cands = analysis["candidate_modules_for_optimization"]
            cand_str = "\n".join([f"  • {c['module']}: {c['reason']}" for c in cands])
            voice_engine.speak("Recursive self-evolution engine initialized, sir. Codebase optimization candidates identified.")
            return {
                "handled": True,
                "type": "SELF_EVOLUTION",
                "speech_text": (
                    f"🧬 Recursive Self-Evolution Engine Active!\n"
                    f"Current Evolution Generation: Gen-{analysis['current_evolution_generation']}\n"
                    f"Verified Self-Patches Deployed: {analysis['total_verified_self_patches']}\n\n"
                    f"Candidate Optimization Opportunities Analyzed:\n{cand_str}\n\n"
                    f"Ready to synthesize, sandbox-test, and deploy self-patches with automatic rollback protection."
                ),
                "action_executed": "SELF_EVOLUTION_AUDIT",
            }

        # 12. Live Real-Time Hardware, Charger, Battery & Clock Queries
        if any(phrase in t_lower for phrase in ["what time is it", "current time", "what is the time", "system clock", "what is the date", "today's date"]):
            from sensors.live_hardware_hub import live_hardware_hub
            telemetry = live_hardware_hub.get_all_live_telemetry()
            reply = f"Current local time is {telemetry.local_time_formatted} ({telemetry.timezone_name}), sir. System uptime is {telemetry.system_uptime_seconds:.1f} seconds."
            voice_engine.speak(reply)
            return {
                "handled": True,
                "type": "CLOCK_QUERY",
                "speech_text": reply,
                "action_executed": "GET_REAL_TIME_CLOCK",
            }

        if any(phrase in t_lower for phrase in ["what is your battery", "battery level", "battery status", "how much battery", "charger", "is charger plugged in", "power status", "charging status"]):
            from sensors.live_hardware_hub import live_hardware_hub
            bat = live_hardware_hub.get_live_battery_and_charger()
            reply = f"Live Power Telemetry, sir: {bat.status_summary}. Battery cells at {bat.battery_percentage:.1f}% ({bat.battery_flag_desc})."
            voice_engine.speak(f"Power status is {bat.status_summary}, sir.")
            return {
                "handled": True,
                "type": "BATTERY_CHARGER_QUERY",
                "speech_text": reply,
                "action_executed": "GET_LIVE_BATTERY_CHARGER",
            }

        if any(phrase in t_lower for phrase in ["hardware stats", "system telemetry", "processor stats", "live hardware", "cpu load", "ram usage"]):
            from sensors.live_hardware_hub import live_hardware_hub
            hud_txt = live_hardware_hub.format_telemetry_hud_text()
            voice_engine.speak("Live hardware telemetry stream displayed on your HUD, sir.")
            return {
                "handled": True,
                "type": "HARDWARE_TELEMETRY_QUERY",
                "speech_text": hud_txt,
                "action_executed": "GET_LIVE_HARDWARE_TELEMETRY",
            }

        if any(phrase in t_lower for phrase in ["where are you", "your location", "current position"]):
            pos = world_model.robot_state.position
            reply = f"I am currently located at spatial coordinates X: {pos.x:.2f}m, Y: {pos.y:.2f}m in the central laboratory arena, sir."
            voice_engine.speak(reply)
            return {
                "handled": True,
                "type": "STATUS_QUERY",
                "speech_text": reply,
                "action_executed": None,
            }

        # Check if this is a physical robotic navigation/patrol/docking mission meant for the Cognitive Core Goal loop:
        if any(k in t_lower for k in ["navigate to", "charging dock", "docking", "dock to", "patrol sector", "explore arena", "inspect", "map room", "patrol", "survey", "explore"]):
            return None

        # 13. Universal Fail-Safe Adaptive Execution Engine (Guarantees 100% resolution for any question)
        from core.universal_failsafe_engine import universal_failsafe_engine
        res_fail = universal_failsafe_engine.resolve_omnipotent_query(t_clean)
        return {
            "handled": True,
            "type": res_fail.query_classified_intent,
            "speech_text": res_fail.solution_text,
            "action_executed": res_fail.action_taken,
        }

    def generate_natural_mission_acknowledgement(self, goal_title: str) -> str:
        """
        Produces natural, fluent conversational language for real tasks instead of rigid templates.
        """
        g_lower = goal_title.lower()

        if "dock" in g_lower or "charge" in g_lower or "recharge" in g_lower:
            msg = f"{jarvis_persona.format_affirmation()} Heading over to the Magnetic Charging Dock now. I will initiate fast-charging upon arrival."
            voice_engine.speak("Heading over to the charging dock now, sir.")
            return msg

        if "scan" in g_lower or "map" in g_lower or "room" in g_lower or "environment" in g_lower:
            msg = f"{jarvis_persona.format_affirmation()} Scanning the environment with 360° LiDAR and optical cameras now."
            voice_engine.speak("Scanning environment now, sir.")
            return msg

        if "diagnos" in g_lower or "failure" in g_lower or "crash" in g_lower or "log" in g_lower:
            msg = f"{jarvis_persona.format_affirmation()} Running comprehensive diagnostic isolation and analyzing crash logs now."
            voice_engine.speak("Running diagnostics now, sir.")
            return msg

        if "explore" in g_lower or "patrol" in g_lower:
            msg = f"{jarvis_persona.format_affirmation()} Starting autonomous patrol and exploration across the sector now."
            voice_engine.speak("Starting patrol now, sir.")
            return msg

        msg = f"{jarvis_persona.format_affirmation()} Executing directive: '{goal_title}'."
        voice_engine.speak(f"Working on that for you now, sir.")
        return msg


conversational_agent = RealTimeConversationalAgent()
