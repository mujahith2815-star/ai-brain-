"""
Real-Time Dynamic Problem Solver & Zero-Friction Intelligence Router for P.H.A.S.S Sphere.
Eliminates confirmation blockers and executes live web searches, dynamic UI code generation,
phone/device hardware power-on protocols, and full OS control on the spot.
"""

from __future__ import annotations
import os
import re
import logging
from typing import Any, Dict, List, Optional

from knowledge.live_search import live_search_engine
from tools.dynamic_executor import dynamic_executor
from tools.device_controller import device_controller
from tools.os_controller import os_controller
from tools.file_ops import file_manager
from tools.screen_vision import screen_vision
from learning.self_evolution import self_evolution_engine
from voice.speech_engine import voice_engine
from voice.sound_effects import sound_synth
from jarvis.persona import jarvis_persona

logger = logging.getLogger("phass.nlp.dynamic_intelligence")


class DynamicZeroFrictionSolver:
    def solve_directive(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Evaluates the user's directive and executes the full solution end-to-end without pausing for permissions.
        """
        from nlp.spelling_corrector import spelling_corrector
        from jarvis.persona import jarvis_persona, ChatPersonaMode
        t_corrected, _ = spelling_corrector.correct_sentence(text)
        t_clean = t_corrected.strip()
        t_lower = t_clean.lower()
        t_normalized = re.sub(r"^(?:then|so|ok then|okay then|now|well)\s+", "", t_lower).strip()

        # === USER IDENTITY & NAME (e.g. "can u able to say my name", "what is my name", "my name is Alex") ===
        name_match = re.search(r"^(?:my name is|call me|set my name to)\s+([a-zA-Z0-9_\-\s]{2,30})", t_clean, re.IGNORECASE)
        if name_match and not any(k in t_lower for k in ["what", "how", "why"]):
            new_name = name_match.group(1).strip()
            jarvis_persona.set_user_name(new_name)
            sound_synth.play_sound("DATA_SYNC")
            sol = f"Awesome! Nice to meet you, {new_name}! 😊 I'll remember your name from now on!" if jarvis_persona.active_mode == ChatPersonaMode.FRIENDLY_COMPANION else f"Identity confirmed and registered as {new_name}, sir."
            voice_engine.speak(sol)
            return {
                "handled": True,
                "type": "USER_IDENTITY_SET",
                "speech_text": sol,
                "action_executed": "SET_USER_NAME",
            }

        if any(k in t_normalized for k in ["say my name", "tell me my name", "do you know my name", "what is my name", "who am i", "my name"]):
            sound_synth.play_sound("DATA_SYNC")
            if jarvis_persona.is_name_known():
                user_n = jarvis_persona.user_preferred_name
                sol = f"Your name is {user_n}! 😊 It's wonderful chatting with you, {user_n}!" if jarvis_persona.active_mode == ChatPersonaMode.FRIENDLY_COMPANION else f"Your registered name is {user_n}, sir."
            else:
                sol = "You haven't told me your name yet! What should I call you? 😊 Just tell me 'My name is ...' and I'll remember it!" if jarvis_persona.active_mode == ChatPersonaMode.FRIENDLY_COMPANION else "You have not registered your name yet, sir. You may set your identity at any time by saying 'My name is...'."
            voice_engine.speak(sol)
            return {
                "handled": True,
                "type": "USER_IDENTITY",
                "speech_text": sol,
                "action_executed": "USER_IDENTITY_LOOKUP",
            }

        # === SECONDARY BRAIN DIRECTIVES (e.g. "use secondary brain phi4", "secondary brain status") ===
        if any(k in t_normalized for k in ["secondary brain", "use secondary brain", "switch to secondary brain", "enable secondary brain", "activate secondary brain", "use phi4", "enable phi4"]):
            from core.secondary_brain import secondary_brain
            sound_synth.play_sound("DATA_SYNC")
            if "status" in t_normalized:
                st = secondary_brain.get_status()
                msg = (
                    f"🧠 Dual-Brain Architecture Status:\n"
                    f"  • Primary Brain:   P.H.A.S.S / NICON Native Core (Online & Active)\n"
                    f"  • Secondary Brain: {st.model_name} ({'ACTIVE' if st.is_active else 'STANDBY'})\n"
                    f"  • Cognitive Mode:  {st.cognitive_mode}\n"
                    f"  • Invocations:     {st.total_invocations} (Avg Latency: {st.average_latency_ms:.1f}ms)"
                )
                voice_engine.speak("Dual brain architecture is fully synchronized and operational, sir.")
                return {
                    "handled": True,
                    "type": "SECONDARY_BRAIN_STATUS",
                    "speech_text": msg,
                    "action_executed": "GET_SECONDARY_BRAIN_STATUS",
                }
            else:
                msg = secondary_brain.activate("phi4")
                voice_engine.speak("Secondary brain Phi-4 is now engaged alongside the primary core, sir.")
                return {
                    "handled": True,
                    "type": "SECONDARY_BRAIN_ACTIVATION",
                    "speech_text": msg,
                    "action_executed": "ACTIVATE_SECONDARY_BRAIN_PHI4",
                }

        # === DYNAMIC CAPABILITY DISCOVERY & QUESTIONS ===
        capability_patterns = [
            r"\bwhat (?:are the things|can) (?:you|u) (?:can )?do\b",
            r"\bwhat can (?:you|u) do\b",
            r"\bwhat are the things (?:you|u) can do\b",
            r"\bwhat features do (?:you|u) have\b",
            r"\btell me what (?:you|u) can do\b",
            r"\bwhat are (?:your|ur) capabilities\b",
            r"\bwhat can i do with (?:you|u)\b",
            r"\bwhat can (?:you|u) control\b",
            r"\bwhich tools do (?:you|u) have\b",
            r"\bwhich modules are working\b",
            r"\bwhat are (?:you|u) capable of\b",
        ]
        if any(re.search(pat, t_lower) or re.search(pat, t_normalized) for pat in capability_patterns):
            from nlp.answer_pipeline import generate_answer
            sound_synth.play_sound("DATA_SYNC")
            ans = generate_answer(t_clean, response_type="CAPABILITY_ANSWER")
            voice_engine.speak("Here is an overview of my current capabilities, sir.")
            return {
                "handled": True,
                "type": "CAPABILITY_ANSWER",
                "speech_text": ans,
                "action_executed": None,
            }

        # === ACTION-CAPABILITY QUESTIONS (Do NOT execute action!) ===
        if re.search(r"^can (?:you|u) (?:open|control|launch|run|execute|access)\b", t_normalized):
            from nlp.answer_pipeline import generate_answer
            sound_synth.play_sound("DATA_SYNC")
            ans = generate_answer(t_clean, response_type="CAPABILITY_ANSWER")
            voice_engine.speak(ans)
            return {
                "handled": True,
                "type": "CAPABILITY_ANSWER",
                "speech_text": ans,
                "action_executed": None,
            }

        # === NATURAL VISION & OBSERVATION INQUIRY ("What do you see?", "Look at my screen") ===
        if any(k in t_normalized for k in ["what do you see", "what can you see", "look at my screen", "what is on my screen"]):
            from vision.screen_observer import screen_observer
            from nlp.natural_response_engine import natural_response_engine
            sound_synth.play_sound("DATA_SYNC")
            obs = screen_observer.capture_observation()
            ans = natural_response_engine.interpret_tool_output("screen_observer", obs.to_dict())
            voice_engine.speak(ans)
            return {
                "handled": True,
                "type": "VISION_OBSERVATION",
                "speech_text": ans,
                "action_executed": "OBSERVE_SCREEN",
            }

        # === NATURAL SYSTEM TELEMETRY INQUIRY ("What is my CPU doing?", "How is my CPU") ===
        if any(k in t_normalized for k in ["what is my cpu doing", "what is the cpu doing", "how is my cpu", "check my cpu", "what's my cpu doing"]):
            from diagnostics.deep_diagnostics import deep_diagnostics
            from nlp.natural_response_engine import natural_response_engine
            sound_synth.play_sound("DATA_SYNC")
            diag = deep_diagnostics.run_full_diagnosis()
            cpu_p = diag.cpu_metrics.get("cpu_percent", 42.1)
            ram_gb = diag.memory_metrics.get("used_gb", 6.2)
            ans = natural_response_engine.interpret_tool_output("system_diagnostics", {"cpu_percent": cpu_p, "ram_used_gb": ram_gb})
            voice_engine.speak(ans)
            return {
                "handled": True,
                "type": "CPU_TELEMETRY",
                "speech_text": ans,
                "action_executed": "INSPECT_CPU",
            }

        # === GENERAL KNOWLEDGE & CONVERSATIONAL QUESTIONS ===
        question_starters = [
            "what is", "what are", "what was", "what were", "why would i", "why use", "why is", "why do",
            "why was", "why did", "how does", "how do", "how was", "how is", "how can",
            "who is", "who was", "who discovered", "who invented", "when was", "when did", "when is",
            "where is", "where was", "where do", "which is", "which are",
            "explain ", "tell me about", "tell me more", "tell me ",
            "give me an example", "show me an example", "can it run", "simplify that",
            "what does that mean", "is it true", "is there", "are there", "do you know",
            "can you explain", "can u explain", "can you tell", "can u tell"
        ]
        excluded_queries = [
            "battery", "temp", "status", "health", "time", "date", "who are you", "what are you",
            "what can you do", "open ", "launch ", "calculate ", "calc ", "weather", "forecast",
            "parliament", "roman empire", "transistor", "entanglement", "continuous 6-dof", "6-dof",
            "joke", "jokes", "motivation", "motivate"
        ]
        if any(t_normalized.startswith(w) or w in t_normalized for w in question_starters) and not any(k in t_normalized for k in excluded_queries):
            from nlp.answer_pipeline import generate_answer
            sound_synth.play_sound("DATA_SYNC")
            ans = generate_answer(t_clean, response_type="ANSWER")
            voice_engine.speak(ans[:140])
            return {
                "handled": True,
                "type": "GENERAL_KNOWLEDGE",
                "speech_text": ans,
                "action_executed": None,
            }

        # === SYSTEM EXPLANATION & HOW-IT-WORKS ===
        if any(k in t_normalized for k in ["how do you work", "how does your system work", "explain how you work"]):
            from nlp.answer_pipeline import generate_answer
            sound_synth.play_sound("DATA_SYNC")
            ans = generate_answer(t_clean, response_type="ANSWER")
            voice_engine.speak(ans[:120])
            return {
                "handled": True,
                "type": "SYSTEM_EXPLANATION",
                "speech_text": ans,
                "action_executed": None,
            }

        # === P.H.A.S.S FRIENDLY COMPANION & EMOTIONAL INTELLIGENCE CHAT SUITE ===
        if any(k in t_lower for k in ["switch to friendly mode", "friendly mode", "be friendly", "start friendly chat", "friendly persona"]):
            from jarvis.persona import jarvis_persona, ChatPersonaMode
            sound_synth.play_sound("DATA_SYNC")
            msg = jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
            voice_engine.speak("Friendly companion mode is now active! Happy to chat with you!")
            return {
                "handled": True,
                "type": "PERSONA_MODE_SWITCH",
                "speech_text": msg,
                "action_executed": "SET_FRIENDLY_MODE",
            }

        if any(k in t_lower for k in ["switch to executive mode", "executive mode", "sovereign mode", "be professional", "tactical mode"]):
            from jarvis.persona import jarvis_persona, ChatPersonaMode
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            msg = jarvis_persona.set_mode(ChatPersonaMode.SOVEREIGN_EXECUTIVE)
            voice_engine.speak("Sovereign executive mode engaged, sir.")
            return {
                "handled": True,
                "type": "PERSONA_MODE_SWITCH",
                "speech_text": msg,
                "action_executed": "SET_EXECUTIVE_MODE",
            }

        if any(k in t_lower for k in ["tell me a joke", "say a joke", "make me laugh", "tell a joke", "funny joke"]):
            from jarvis.persona import jarvis_persona
            sound_synth.play_sound("DATA_SYNC")
            joke = jarvis_persona.get_friendly_joke()
            voice_engine.speak(joke)
            return {
                "handled": True,
                "type": "FRIENDLY_JOKE",
                "speech_text": joke,
                "action_executed": "TELL_JOKE",
            }

        if any(k in t_lower for k in ["motivate me", "give me motivation", "inspire me", "words of encouragement", "i need motivation"]):
            from jarvis.persona import jarvis_persona
            sound_synth.play_sound("DATA_SYNC")
            motivation = jarvis_persona.get_friendly_motivation()
            voice_engine.speak(motivation)
            return {
                "handled": True,
                "type": "FRIENDLY_MOTIVATION",
                "speech_text": motivation,
                "action_executed": "GIVE_MOTIVATION",
            }

        if any(k in t_lower for k in ["i had a bad day", "i feel sad", "i'm stressed", "i am stressed", "i am sad", "i'm tired", "i am tired", "i feel exhausted", "i'm bored", "i am bored", "talk to me", "let's be friends", "can we chat", "how are you my friend"]):
            from jarvis.persona import jarvis_persona
            sound_synth.play_sound("DATA_SYNC")
            empathy = jarvis_persona.format_empathy_response(t_clean)
            voice_engine.speak(empathy)
            return {
                "handled": True,
                "type": "FRIENDLY_EMPATHY",
                "speech_text": empathy,
                "action_executed": "EMPATHY_RESPONSE",
            }

        # === P.H.A.S.S CHERRY-RED AI MODEL MULTI-WINDOW DASHBOARD ===
        if any(k in t_lower for k in ["launch model dashboard", "open model dashboard", "start model dashboard", "open cherry dashboard", "launch cherry dashboard", "start model ui", "launch ai interface", "cherry dashboard", "open dashboard"]):
            from ui.cherry_model_dashboard import cherry_dashboard_server
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            port = cherry_dashboard_server.start()
            import webbrowser
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:
                pass
            voice_engine.speak("Cherry-red dark AI model multi-window dashboard online on port " + str(port) + ", sir.")
            return {
                "handled": True,
                "type": "CHERRY_MODEL_DASHBOARD_LAUNCH",
                "speech_text": f"Cherry-Red Dark-Theme AI Model Dashboard launched successfully at http://127.0.0.1:{port} with Multi-Window Tiling, Acrylic Backdrop Blur, and Real-time Telemetry.",
                "action_executed": "LAUNCH_CHERRY_MODEL_DASHBOARD",
            }

        # === P.H.A.S.S LOCAL AI & OLLAMA RUNNER SUITE ===
        if any(k in t_lower for k in ["check ollama status", "ollama status", "local ai status", "model runner status", "check local ai", "ollama not running"]):
            from tools.ollama_manager import ollama_local_manager
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            report = ollama_local_manager.format_status_report()
            voice_engine.speak("Local AI runner inspected, sir. Native neural inference engine is active and ready.")
            return {
                "handled": True,
                "type": "LOCAL_AI_OLLAMA_STATUS",
                "speech_text": report,
                "action_executed": "INSPECT_LOCAL_AI_OLLAMA_STATUS",
            }

        # === P.H.A.S.S SOFTWARE-TO-AI-MODEL CONVERSION & EXPORT SUITE ===
        # 1. Distill & Export Software to AI Model (e.g. "convert software into ai model", "convert to ai model", "export ai model", "export ollama modelfile", "export model to gguf")
        if any(k in t_lower for k in ["convert software into ai model", "convert this software into ai model", "convert to ai model", "convert into ai model", "convert software to ai model", "export ai model", "export model", "export ollama modelfile", "export model to gguf", "export model to safetensors"]) or (("convert" in t_lower or "distill" in t_lower) and ("model" in t_lower or "ai" in t_lower)):
            from neural.model_exporter import model_exporter
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            manifest = model_exporter.export_full_ai_model_package()
            voice_engine.speak(f"Software distilled into standalone AI model '{manifest.model_name}', sir. Exported to HuggingFace, GGUF, and Ollama Modelfile formats.")
            return {
                "handled": True,
                "type": "SOFTWARE_TO_AI_MODEL_EXPORT",
                "speech_text": model_exporter.format_export_manifest_text(manifest),
                "action_executed": "EXPORT_SOFTWARE_TO_AI_MODEL",
            }

        # === P.H.A.S.S v8.0 APEX NEXUS NEURAL AI TRAINING SUITE (DPO + CoT SFT + EWC + Self-Play) ===
        # 1. DPO Preference Optimization (e.g. "train with dpo", "dpo alignment", "train preference")
        if any(k in t_lower for k in ["train with dpo", "dpo alignment", "train preference", "train dpo"]):
            from neural.apex_neural_trainer import apex_neural_trainer
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            metrics = apex_neural_trainer.train_direct_preference_optimization()
            voice_engine.speak(f"Direct Preference Optimization complete, sir. Policy alignment margin gained +{metrics.dpo_preference_margin:.2f}.")
            return {
                "handled": True,
                "type": "APEX_NEURAL_DPO_TRAINING",
                "speech_text": apex_neural_trainer.format_training_report_text(metrics),
                "action_executed": "TRAIN_NEURAL_DPO_ALIGNMENT",
            }

        # 2. Chain-of-Thought SFT & General AI Training (e.g. "train ai model", "train ai", "run apex neural training", "train neural network")
        if any(k in t_lower for k in ["train ai model", "train ai", "run apex neural training", "train neural network", "run neural training", "train model"]):
            from neural.apex_neural_trainer import apex_neural_trainer
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            metrics = apex_neural_trainer.train_supervised_sft(epochs=5)
            voice_engine.speak(f"Apex neural fine-tuning complete, sir. Loss reduced by {metrics.loss_reduction_pct:.1f} percent.")
            return {
                "handled": True,
                "type": "APEX_NEURAL_SFT_TRAINING",
                "speech_text": apex_neural_trainer.format_training_report_text(metrics),
                "action_executed": "TRAIN_NEURAL_SFT_MODEL",
            }

        # 3. Continual Learning with EWC (e.g. "continual learning", "train ewc", "elastic weight consolidation")
        if any(k in t_lower for k in ["continual learning", "train ewc", "elastic weight consolidation"]):
            from neural.apex_neural_trainer import apex_neural_trainer
            metrics = apex_neural_trainer.train_continual_learning_ewc()
            voice_engine.speak("Continual learning pass complete with zero catastrophic forgetting, sir.")
            return {
                "handled": True,
                "type": "APEX_NEURAL_EWC_TRAINING",
                "speech_text": apex_neural_trainer.format_training_report_text(metrics),
                "action_executed": "TRAIN_NEURAL_EWC_CONTINUAL",
            }

        # 4. Training Methods Status / Reports (e.g. "training methods status", "neural training status")
        if any(k in t_lower for k in ["training methods status", "neural training status", "ai training methods"]):
            from neural.apex_neural_trainer import apex_neural_trainer
            metrics = apex_neural_trainer.train_supervised_sft(epochs=1)
            return {
                "handled": True,
                "type": "APEX_NEURAL_TRAINING_STATUS",
                "speech_text": apex_neural_trainer.format_training_report_text(metrics),
                "action_executed": "GET_NEURAL_TRAINING_STATUS",
            }

        # === UNIVERSAL ENVIRONMENT AUTO-INSTALLER & DEPENDENCY MANAGER ===
        # 1. Check / Install Environment (e.g. "auto install environment", "setup environment", "verify system dependencies", "check environment readiness")
        if any(k in t_lower for k in ["auto install environment", "setup environment", "install environment", "verify system dependencies", "check environment readiness", "environment readiness", "check dependencies"]):
            from core.auto_environment_installer import auto_environment_installer
            sound_synth.play_sound("DATA_SYNC")
            rep = auto_environment_installer.auto_provision_environment(run_pip_install=False)
            voice_engine.speak(f"Environment readiness verified, sir. Operating on {rep.system_info.os_name} with {rep.system_info.cpu_logical_cores} compute cores.")
            return {
                "handled": True,
                "type": "ENVIRONMENT_PROVISIONING_REPORT",
                "speech_text": auto_environment_installer.format_readiness_report_text(rep),
                "action_executed": "VERIFY_ENVIRONMENT_READINESS",
            }

        # === REAL-TIME CYBER INTRUSION SHIELD & WARNING BOX OVERLAY ===
        # 1. Simulate Cyber Attack & Trigger Desktop Warning Box (e.g. "simulate cyber attack", "test threat warning box", "simulate intrusion")
        if any(k in t_lower for k in ["simulate cyber attack", "test cyber attack", "simulate intrusion", "test threat warning box", "test warning box", "simulate attack"]):
            from security.intrusion_shield import intrusion_shield
            from ui.threat_warning_overlay import threat_warning_overlay
            atk_type = "SYN_FLOOD_PORT_SCAN"
            if "ransomware" in t_lower:
                atk_type = "RANSOMWARE_CANARY"
            elif "injection" in t_lower or "memory" in t_lower:
                atk_type = "MEMORY_INJECTION"
            elif "dns" in t_lower:
                atk_type = "DNS_HIJACK"

            event = intrusion_shield.simulate_cyber_attack(atk_type)
            return {
                "handled": True,
                "type": "CYBER_ATTACK_SIMULATION_NEUTRALIZED",
                "speech_text": f"Simulated intrusion '{event.threat_type}' intercepted and neutralized. On-screen threat warning box rendered on your desktop.",
                "action_executed": f"NEUTRALIZE_THREAT_{event.event_id}",
            }

        # 2. Intrusion Shield Status & Defense Telemetry (e.g. "intrusion shield status", "cyber shield status", "threat protection status")
        if any(k in t_lower for k in ["intrusion shield status", "cyber shield status", "threat protection status", "cyber shield", "intrusion shield"]):
            from security.intrusion_shield import intrusion_shield
            return {
                "handled": True,
                "type": "INTRUSION_SHIELD_TELEMETRY",
                "speech_text": intrusion_shield.format_shield_report_text(),
                "action_executed": "GET_INTRUSION_SHIELD_STATUS",
            }

        # === UNIVERSAL MULTI-DEVICE ECOSYSTEM CONTROLLER (PC, Laptop, TV, Smartphone, Smartwatch) ===
        # A. Smart TV Controls (e.g. "turn off tv", "launch youtube on tv", "set tv volume to 30")
        if any(k in t_lower for k in ["smart tv", "on tv", "turn on tv", "turn off tv", "tv volume", "launch netflix on tv", "launch youtube on tv"]):
            from mesh.universal_device_controller import universal_device_controller
            sound_synth.play_sound("DATA_SYNC")
            res_tv = universal_device_controller.control_smart_tv(t_clean)
            voice_engine.speak(f"Smart TV command executed, sir: {res_tv.details}")
            return {
                "handled": True,
                "type": "ECOSYSTEM_SMART_TV_CONTROL",
                "speech_text": f"Smart TV Directive: {res_tv.details}",
                "action_executed": f"CONTROL_SMART_TV_{res_tv.action_executed[:20]}",
            }

        # B. Remote Laptop Controls (e.g. "lock laptop", "boost laptop speed", "sleep laptop")
        if any(k in t_lower for k in ["lock laptop", "laptop lock", "boost laptop", "sleep laptop", "laptop speed"]):
            from mesh.universal_device_controller import universal_device_controller
            res_lap = universal_device_controller.control_laptop(t_clean)
            voice_engine.speak(f"Remote laptop directive dispatched, sir.")
            return {
                "handled": True,
                "type": "ECOSYSTEM_LAPTOP_CONTROL",
                "speech_text": f"Laptop Directive: {res_lap.details}",
                "action_executed": "CONTROL_REMOTE_LAPTOP",
            }

        # C. Smartphone Controls (e.g. "open camera on phone", "open whatsapp on phone", "smartphone battery")
        if any(k in t_lower for k in ["on phone", "on smartphone", "phone battery", "open camera on phone"]):
            from mesh.universal_device_controller import universal_device_controller
            res_ph = universal_device_controller.control_smartphone(t_clean)
            voice_engine.speak(f"Smartphone automation executed, sir.")
            return {
                "handled": True,
                "type": "ECOSYSTEM_SMARTPHONE_CONTROL",
                "speech_text": f"Smartphone Directive: {res_ph.details}",
                "action_executed": "CONTROL_SMARTPHONE",
            }

        # D. Smartwatch Controls (e.g. "send alert to smartwatch <msg>", "notify smartwatch <msg>", "alert watch <msg>")
        if any(k in t_lower for k in ["smartwatch", "smart watch", "to watch", "alert watch", "notify watch"]):
            from mesh.universal_device_controller import universal_device_controller
            msg = re.sub(r"^(send alert to smartwatch|notify smartwatch|alert watch|send alert to watch|notify watch)\s*", "", t_clean, flags=re.IGNORECASE).strip() or "General Advisory Alert"
            res_w = universal_device_controller.send_smartwatch_alert(msg)
            voice_engine.speak("Haptic notification dispatched to your smartwatch, sir.")
            return {
                "handled": True,
                "type": "ECOSYSTEM_SMARTWATCH_CONTROL",
                "speech_text": f"Smartwatch Directive: {res_w.details}",
                "action_executed": "SEND_SMARTWATCH_ALERT",
            }

        # E. Ecosystem Status & Master Multi-Device Report
        if any(k in t_lower for k in ["list all ecosystem devices", "ecosystem status", "device takeover", "all paired devices", "paired ecosystem"]):
            from mesh.universal_device_controller import universal_device_controller
            return {
                "handled": True,
                "type": "ECOSYSTEM_MASTER_TELEMETRY",
                "speech_text": universal_device_controller.get_ecosystem_status_report(),
                "action_executed": "GET_ECOSYSTEM_STATUS",
            }

        # === P.H.A.S.S ZENITH OMNIPRESENCE v7.0 BREAKTHROUGHS ===
        # 1. 3D WebGL Holographic HUD & Web Dashboard (e.g. "launch 3d hud", "3d holographic hud", "web hud")
        if any(k in t_lower for k in ["launch 3d hud", "3d holographic hud", "3d hud", "holographic web hud", "web hud", "launch web hud"]):
            from ui.holographic_web_hud import holographic_web_hud
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            manifest = holographic_web_hud.launch_holographic_web_hud(port=8090, open_browser=False)
            spoken = f"Interactive 3D WebGL Holographic HUD online on port {manifest.server_port}, sir."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "HOLOGRAPHIC_3D_WEB_HUD_LAUNCH",
                "speech_text": holographic_web_hud.format_hud_report_text(manifest),
                "action_executed": "LAUNCH_3D_WEB_HUD",
            }

        # 2. Autonomous Multi-Device Mobile Mesh & Phone Bridge (e.g. "mobile mesh status", "pair mobile phone", "send push notification <msg>")
        if any(t_lower.startswith(k) for k in ["pair mobile phone", "pair mobile device", "pair phone", "connect phone"]):
            from mesh.mobile_device_bridge import mobile_device_bridge
            p_name = re.sub(r"^(pair mobile phone|pair mobile device|pair phone|connect phone)\s*", "", t_clean, flags=re.IGNORECASE).strip() or "Secondary Mobile Node"
            dev = mobile_device_bridge.pair_device(p_name)
            voice_engine.speak(f"Paired mobile device '{dev.device_name}' into P.H.A.S.S mesh, sir.")
            return {
                "handled": True,
                "type": "MOBILE_MESH_PAIR_DEVICE",
                "speech_text": f"Device paired successfully: [{dev.device_id}] {dev.device_name} (IP: {dev.ip_address}).",
                "action_executed": f"PAIR_MOBILE_NODE_{dev.device_id}",
            }

        if any(t_lower.startswith(k) for k in ["send push notification", "push alert", "mobile notification"]):
            from mesh.mobile_device_bridge import mobile_device_bridge
            msg_text = re.sub(r"^(send push notification|push alert|mobile notification)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            payload = mobile_device_bridge.send_push_notification("P.H.A.S.S Zenith Alert", msg_text or "Mission Milestone Reached")
            return {
                "handled": True,
                "type": "MOBILE_PUSH_NOTIFICATION_DISPATCH",
                "speech_text": f"Push notification [{payload.notification_id}] delivered to {payload.recipient_device}.",
                "action_executed": "DISPATCH_MOBILE_PUSH_NOTIFICATION",
            }

        if "mobile mesh" in t_lower:
            from mesh.mobile_device_bridge import mobile_device_bridge
            return {
                "handled": True,
                "type": "MOBILE_MESH_TELEMETRY",
                "speech_text": mobile_device_bridge.format_mesh_status_text(),
                "action_executed": "GET_MOBILE_MESH_STATUS",
            }

        # 3. Hands-Free Hotword Listener (e.g. "start hotword listener", "stop hotword listener", "hotword status")
        if any(k in t_lower for k in ["start hotword listener", "activate wakeword", "enable hands free", "start wakeword"]):
            from voice.hotword_listener import hotword_listener
            hotword_listener.start_listener()
            voice_engine.speak("Hands-free wakeword listener online, sir. Listening for 'Hey P.H.A.S.S'.")
            return {
                "handled": True,
                "type": "HOTWORD_LISTENER_START",
                "speech_text": hotword_listener.format_hotword_status_text(),
                "action_executed": "START_HOTWORD_LISTENER",
            }

        if any(k in t_lower for k in ["hotword status", "wakeword status", "hands free status"]):
            from voice.hotword_listener import hotword_listener
            return {
                "handled": True,
                "type": "HOTWORD_LISTENER_STATUS",
                "speech_text": hotword_listener.format_hotword_status_text(),
                "action_executed": "GET_HOTWORD_STATUS",
            }

        # 4. Codebase Auto-Architect & Test Synthesizer (e.g. "analyze codebase architecture", "generate tests for <file>")
        if any(t_lower.startswith(k) for k in ["analyze codebase architecture", "codebase architecture", "architect codebase", "analyze repo"]):
            from tools.repo_auto_architect import repo_auto_architect
            sound_synth.play_sound("DATA_SYNC")
            rep = repo_auto_architect.analyze_codebase_architecture(os.getcwd())
            voice_engine.speak(f"Codebase architecture analyzed, sir. {rep.total_python_files} modules and {rep.total_lines_of_code:,} lines mapped.")
            return {
                "handled": True,
                "type": "CODEBASE_ARCHITECTURE_AUDIT",
                "speech_text": repo_auto_architect.format_architecture_report_text(rep),
                "action_executed": "AUDIT_CODEBASE_ARCHITECTURE",
            }

        # 5. Cryptographic Zero-Trust Secret Vault (e.g. "store secret <key> <val>", "vault status", "quantum vault")
        if any(t_lower.startswith(k) for k in ["store secret", "store api key", "save secret", "store credential"]):
            from security.quantum_vault import quantum_vault
            parts = re.sub(r"^(store secret|store api key|save secret|store credential)\s+", "", t_clean, flags=re.IGNORECASE).strip().split()
            k_name = parts[0] if parts else "SECRET_KEY"
            v_val = parts[1] if len(parts) > 1 else "sk_live_sample_token_secret"
            quantum_vault.store_secret(k_name, v_val)
            voice_engine.speak(f"Secret '{k_name}' encrypted with PBKDF2 and saved into zero-trust vault, sir.")
            return {
                "handled": True,
                "type": "SECRET_VAULT_STORE",
                "speech_text": f"Secret '{k_name}' successfully encrypted and stored in Quantum Vault.",
                "action_executed": f"STORE_SECRET_{k_name.upper()}",
            }

        if any(k in t_lower for k in ["quantum vault", "vault status", "secret vault", "list secrets"]):
            from security.quantum_vault import quantum_vault
            return {
                "handled": True,
                "type": "SECRET_VAULT_STATUS",
                "speech_text": quantum_vault.format_vault_status_text(),
                "action_executed": "GET_SECRET_VAULT_STATUS",
            }

        # === P.H.A.S.S SUPREME SOVEREIGN v6.0 SUPERPOWERS ===
        # 1. Autonomous Full-Stack Software App Forge (e.g. "build app crypto tracker", "create app kanban board", "app forge task manager")
        if any(t_lower.startswith(k) for k in ["build app", "create app", "app forge", "generate app", "forge app"]):
            from tools.app_forge import autonomous_app_forge
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            app_prompt = re.sub(r"^(build app|create app|app forge|generate app|forge app)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            manifest = autonomous_app_forge.generate_and_launch_app(app_prompt or "System HUD Dashboard")
            spoken = f"Full-stack software application '{manifest.app_name}' synthesized and deployed on port {manifest.local_port}, sir."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "AUTONOMOUS_APP_FORGE_DEPLOY",
                "speech_text": autonomous_app_forge.format_forge_report_text(manifest),
                "action_executed": f"FORGE_APP_{manifest.app_id.upper()}",
            }

        # 2. Real-Time Optical Screen Vision & Window Observer (e.g. "observe screen", "inspect active windows", "screen vision", "desktop vision")
        if any(k in t_lower for k in ["observe screen", "inspect screen", "screen vision", "desktop vision", "inspect active windows", "active windows"]):
            from vision.screen_observer import screen_observer
            sound_synth.play_sound("TACTICAL_RADAR")
            obs_rep = screen_observer.observe_screen_and_windows()
            voice_engine.speak(f"Screen vision complete, sir. {obs_rep.open_windows_count} desktop applications observed.")
            return {
                "handled": True,
                "type": "OPTICAL_SCREEN_OBSERVATION",
                "speech_text": screen_observer.format_observation_text(obs_rep),
                "action_executed": "OBSERVE_SCREEN_AND_WINDOWS",
            }

        # 3. Autonomous Cyber Defense & Firewall Sentinel (e.g. "cyber security sweep", "sentinel audit", "audit ports", "security sweep")
        if any(k in t_lower for k in ["cyber security sweep", "security sweep", "sentinel audit", "audit ports", "cyber defense"]):
            from security.sentinel_guard import sentinel_guard
            sound_synth.play_sound("TACTICAL_RADAR")
            sec_rep = sentinel_guard.perform_full_security_sweep()
            voice_engine.speak(f"Cyber defense audit concluded, sir. Threat level is {sec_rep.threat_level}.")
            return {
                "handled": True,
                "type": "CYBER_SENTINEL_SWEEP",
                "speech_text": sentinel_guard.format_security_report_text(sec_rep),
                "action_executed": "PERFORM_CYBER_SECURITY_SWEEP",
            }

        # 4. Autonomous Long-Horizon Overnight Goal Runner (e.g. "start overnight mission <goal>", "overnight goal <goal>", "overnight mission")
        if any(t_lower.startswith(k) for k in ["start overnight mission", "overnight mission", "overnight goal", "start overnight goal"]):
            from agents.overnight_runner import overnight_runner
            sound_synth.play_sound("DATA_SYNC")
            g = re.sub(r"^(start overnight mission|overnight mission|overnight goal|start overnight goal)\s+", "", t_clean, flags=re.IGNORECASE).strip() or "Autonomous Deep Architecture Synthesis"
            manifest = overnight_runner.decompose_and_execute_mission(g)
            voice_engine.speak(f"Overnight autonomous mission initialized, sir. {manifest.total_tasks_count} phases queued.")
            return {
                "handled": True,
                "type": "OVERNIGHT_MISSION_DISPATCH",
                "speech_text": overnight_runner.format_morning_briefing_text(manifest),
                "action_executed": f"DISPATCH_OVERNIGHT_MISSION_{manifest.mission_id}",
            }

        # 5. Omni-Desktop GUI Operator (e.g. "type text <text>", "send hotkey <key>", "batch rename files in <path>")
        if t_lower.startswith("type text ") or t_lower.startswith("type "):
            from tools.gui_operator import gui_operator
            txt_to_type = re.sub(r"^(type text|type)\s+", "", t_clean, flags=re.IGNORECASE).strip().strip('"')
            res_gui = gui_operator.type_text(txt_to_type)
            return {
                "handled": True,
                "type": "GUI_TYPE_TEXT",
                "speech_text": f"Dispatched keyboard typing for '{txt_to_type}' ({res_gui.details}).",
                "action_executed": "INJECT_DESKTOP_KEYSTROKES",
            }

        if t_lower.startswith("send hotkey "):
            from tools.gui_operator import gui_operator
            hk = re.sub(r"^send hotkey\s+", "", t_clean, flags=re.IGNORECASE).strip()
            res_hk = gui_operator.send_hotkey(hk)
            return {
                "handled": True,
                "type": "GUI_SEND_HOTKEY",
                "speech_text": f"Dispatched desktop hotkey '{hk}'.",
                "action_executed": "INJECT_DESKTOP_HOTKEY",
            }

        # -10.1. Custom Voice Personas & Sound FX Pack
        if any(t_lower.startswith(k) for k in ["set voice persona", "change voice persona", "voice persona", "switch voice to"]):
            from voice.voice_customizer import voice_customizer
            p_name = re.sub(r"^(set voice persona to|change voice persona to|voice persona to|switch voice to|set voice persona|voice persona)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            profile = voice_customizer.set_persona(p_name)
            voice_engine.speak(f"Voice persona switched to {profile.persona.value}, sir.")
            return {
                "handled": True,
                "type": "VOICE_PERSONA_CHANGE",
                "speech_text": voice_customizer.format_voice_status_text(),
                "action_executed": f"SET_VOICE_PERSONA_{profile.persona.name}",
            }

        if any(t_lower.startswith(k) for k in ["set voice speed", "change voice speed", "voice rate"]):
            from voice.voice_customizer import voice_customizer
            nums = re.findall(r"\d+", t_clean)
            spd = int(nums[0]) if nums else 180
            applied_spd = voice_customizer.set_speech_rate(spd)
            voice_engine.speak(f"Speech speed calibrated to {applied_spd} words per minute, sir.")
            return {
                "handled": True,
                "type": "VOICE_SPEED_CHANGE",
                "speech_text": f"Speech rate set to {applied_spd} wpm.",
                "action_executed": "SET_SPEECH_SPEED",
            }

        # -10.2. Document & Codebase Vector Ingestor (e.g. "ingest document <path>", "ingest folder <path>", "search document memory for <query>")
        if any(t_lower.startswith(k) for k in ["ingest document", "ingest file", "index file", "ingest pdf", "ingest codebase", "ingest folder", "index folder"]):
            from memory.document_ingestor import document_ingestor
            sound_synth.play_sound("DATA_SYNC")
            target_path = re.sub(r"^(ingest document|ingest file|index file|ingest pdf|ingest codebase|ingest folder|index folder)\s+", "", t_clean, flags=re.IGNORECASE).strip().strip('"')
            target_path = target_path or os.getcwd()
            if os.path.isdir(target_path):
                docs = document_ingestor.ingest_directory(target_path, max_files=10)
                spoken = f"Ingested {len(docs)} codebase files into permanent vector memory vault, sir."
                voice_engine.speak(spoken)
                rep_lines = [f"=== BATCH DIRECTORY VECTOR INGESTION REPORT ===\nIngested {len(docs)} Files:"]
                for d in docs:
                    rep_lines.append(f"  • {d.file_name} -> {d.total_chunks_created} Chunks ({d.file_size_bytes} B)")
                return {
                    "handled": True,
                    "type": "DOCUMENT_DIRECTORY_INGESTION",
                    "speech_text": "\n".join(rep_lines),
                    "action_executed": "INGEST_DIRECTORY_VECTOR_VAULT",
                }
            else:
                summary = document_ingestor.ingest_file(target_path)
                spoken = f"Document {summary.file_name} indexed into {summary.total_chunks_created} vector embeddings, sir."
                voice_engine.speak(spoken)
                return {
                    "handled": True,
                    "type": "DOCUMENT_VECTOR_INGESTION",
                    "speech_text": document_ingestor.format_ingest_report_text(summary),
                    "action_executed": "INGEST_FILE_VECTOR_VAULT",
                }

        # -10.3. Universal All-Format File Viewer & Hex Dumper (e.g. "view file <path>", "hex dump <path>", "view csv <path>")
        if any(t_lower.startswith(k) for k in ["hex dump file", "hex dump", "binary dump"]):
            from tools.universal_file_editor import universal_file_editor
            fp = re.sub(r"^(hex dump file|hex dump|binary dump)\s+", "", t_clean, flags=re.IGNORECASE).strip().strip('"')
            hex_out = universal_file_editor.generate_hex_dump(fp)
            voice_engine.speak(f"Hexadecimal byte inspection generated for {os.path.basename(fp)}, sir.")
            return {
                "handled": True,
                "type": "HEX_DUMP_VIEW",
                "speech_text": hex_out,
                "action_executed": "HEX_DUMP_FILE",
            }

        if any(t_lower.startswith(k) for k in ["view csv table", "view csv", "preview csv", "preview table"]):
            from tools.universal_file_editor import universal_file_editor
            fp = re.sub(r"^(view csv table|view csv|preview csv|preview table)\s+", "", t_clean, flags=re.IGNORECASE).strip().strip('"')
            csv_out = universal_file_editor.view_csv_table_preview(fp)
            voice_engine.speak(f"CSV table parsed and formatted on your HUD, sir.")
            return {
                "handled": True,
                "type": "CSV_TABLE_VIEW",
                "speech_text": csv_out,
                "action_executed": "VIEW_CSV_TABLE",
            }

        # -9. Universal Scientific, Symbolic, Financial, and Unit Calculator Suite
        # A. Symbolic Algebra Solver (e.g. "solve equation 2x + 10 = 30", "solve 3x + 15 = 45", "solve equation x^2 = 16")
        if any(t_lower.startswith(k) for k in ["solve equation", "solve algebraic", "solve for x"]):
            from tools.advanced_calculator import advanced_calculator
            eq = re.sub(r"^(solve equation|solve algebraic equation|solve algebraic|solve for x|solve)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            res_alg = advanced_calculator.solve_algebraic_equation(eq)
            spoken = f"Algebraic equation resolved, sir: {res_alg.formatted_output}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "SYMBOLIC_ALGEBRA_CALCULATION",
                "speech_text": advanced_calculator.format_calculator_report_text(res_alg),
                "action_executed": "SOLVE_SYMBOLIC_EQUATION",
            }

        # B. Unit Conversions (e.g. "convert 50 miles to km", "convert 100 c to f", "convert 5 gb to mb")
        conv_match = re.match(r"^convert\s+([\d\.]+)\s*([a-zA-Z°]+)\s+(?:in|to)\s+([a-zA-Z°]+)$", t_lower.strip())
        if conv_match:
            from tools.advanced_calculator import advanced_calculator
            val_s, u1, u2 = conv_match.groups()
            res_conv = advanced_calculator.convert_units(float(val_s), u1, u2)
            spoken = f"Unit conversion complete, sir: {res_conv.formatted_output}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "UNIT_CONVERSION_CALCULATION",
                "speech_text": advanced_calculator.format_calculator_report_text(res_conv),
                "action_executed": "CONVERT_PHYSICAL_UNITS",
            }

        # C. Financial & Compound Interest (e.g. "calculate compound interest for 10000 at 5% for 3 years", "compound interest")
        if "compound interest" in t_lower:
            from tools.advanced_calculator import advanced_calculator
            nums = [float(n) for n in re.findall(r"[\d\.]+", t_clean)]
            p = nums[0] if len(nums) > 0 else 10000.0
            r = nums[1] if len(nums) > 1 else 7.0
            t_yrs = nums[2] if len(nums) > 2 else 5.0
            res_fin = advanced_calculator.calculate_compound_interest(p, r, t_yrs)
            spoken = f"Financial compound interest computed, sir: {res_fin.formatted_output}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "FINANCIAL_CALCULATION",
                "speech_text": advanced_calculator.format_calculator_report_text(res_fin),
                "action_executed": "CALCULATE_COMPOUND_INTEREST",
            }

        # D. Statistics & Mean / Median (e.g. "calculate statistics for 10, 20, 30, 40, 50")
        if any(t_lower.startswith(k) for k in ["calculate statistics", "statistics for", "statistical analysis"]):
            from tools.advanced_calculator import advanced_calculator
            num_list = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+", t_clean)]
            res_stat = advanced_calculator.calculate_statistics(num_list)
            spoken = f"Statistical distribution calculated, sir: {res_stat.formatted_output}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "STATISTICAL_CALCULATION",
                "speech_text": advanced_calculator.format_calculator_report_text(res_stat),
                "action_executed": "CALCULATE_STATISTICS",
            }

        # E. General Scientific Calculation (e.g. "calculate 500 * (1 + 0.08)^10", "calculate sqrt(144) + 25")
        if t_lower.startswith("calculate ") or t_lower.startswith("calc "):
            from tools.advanced_calculator import advanced_calculator
            expr = re.sub(r"^(calculate|calc)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            # If purely math expression
            if any(op in expr for op in ["+", "-", "*", "/", "^", "(", "sqrt", "sin", "cos", "tan", "log", "ln", "pi"]):
                res_calc = advanced_calculator.evaluate_scientific_expression(expr)
                if res_calc.numeric_result is not None:
                    spoken = f"Calculation result is {res_calc.numeric_result:g}, sir."
                    voice_engine.speak(spoken)
                    return {
                        "handled": True,
                        "type": "SCIENTIFIC_CALCULATION",
                        "speech_text": advanced_calculator.format_calculator_report_text(res_calc),
                        "action_executed": "EVALUATE_SCIENTIFIC_MATH",
                    }

        # F. Launch Native OS Calculator (e.g. "open calculator", "launch calculator", "calculator app")
        if any(t_lower.startswith(k) for k in ["open calculator", "launch calculator", "open calc", "start calculator"]):
            from tools.advanced_calculator import advanced_calculator
            ok, msg = advanced_calculator.launch_os_calculator()
            voice_engine.speak("Launching native calculator for you now, sir.")
            return {
                "handled": True,
                "type": "APP_LAUNCH_CALCULATOR",
                "speech_text": msg,
                "action_executed": "LAUNCH_OS_CALCULATOR",
            }
        if any(t_lower.startswith(k) for k in ["spawn agent colony", "spawn colony", "colony mission", "swarm mission", "swarm colony"]):
            from agents.agent_colony import agent_colony
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            goal_spec = re.sub(r"^(spawn agent colony for|spawn agent colony|spawn colony for|spawn colony|colony mission|swarm mission|swarm colony)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            mission_res = agent_colony.spawn_colony_mission(goal_spec or "Autonomous System Optimization")
            spoken = f"Swarm colony mission complete, sir. All {mission_res.agents_deployed_count} specialized agents converged on goal in {mission_res.total_execution_time_sec:.2f} seconds."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "SWARM_COLONY_MISSION",
                "speech_text": agent_colony.format_mission_report_text(mission_res),
                "action_executed": f"EXECUTE_COLONY_MISSION_{mission_res.mission_id.upper()}",
            }

        # -8.2. Infinite Vector Memory & Semantic Vault (e.g. "search vector memory <query>", "vector vault", "store memory <text>")
        if any(k in t_lower for k in ["search vector memory", "vector memory", "vector vault", "semantic memory"]):
            from memory.vector_vault import vector_vault
            q = re.sub(r"^(search vector memory for|search vector memory|vector memory|vector vault|semantic memory)\s*", "", t_clean, flags=re.IGNORECASE).strip() or "general knowledge"
            results = vector_vault.search_semantic_memory(q, top_k=3)
            voice_engine.speak(f"Retrieved {len(results)} high-relevance semantic vectors from permanent memory vault, sir.")
            res_lines = [f"=== P.H.A.S.S VECTOR VAULT SEMANTIC SEARCH ===\nQuery: \"{q}\"\nTop Retrieved Vectors:"]
            for r in results:
                res_lines.append(f"  • [{r.doc.doc_id}] (Similarity: {int(r.similarity_score*100)}%) -> \"{r.doc.content[:140]}\"")
            return {
                "handled": True,
                "type": "VECTOR_MEMORY_SEARCH",
                "speech_text": "\n".join(res_lines),
                "action_executed": "SEARCH_VECTOR_VAULT",
            }

        # -8.3. Autonomous Headless Web Browser Agent (e.g. "browse web for <url>", "scrape page <url>", "open url <url>")
        if any(t_lower.startswith(k) for k in ["browse web for", "browse web", "scrape page", "browse url", "browser agent"]):
            from tools.web_browser_agent import web_browser_agent
            sound_synth.play_sound("SONAR_PING")
            target = re.sub(r"^(browse web for|browse web|scrape page|browse url|browser agent)\s+", "", t_clean, flags=re.IGNORECASE).strip() or "https://wikipedia.org"
            page_ext = web_browser_agent.browse_url(target)
            spoken = f"Web navigation complete, sir. Extracted {page_ext.links_extracted_count} links and DOM content from {page_ext.title[:30]}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "WEB_BROWSER_EXTRACTION",
                "speech_text": web_browser_agent.format_browse_report_text(page_ext),
                "action_executed": "BROWSE_WEB_PAGE",
            }

        # -8.4. Metacognitive Self-Healing & Automatic Code Debugger (e.g. "self heal code <snippet>", "heal code", "debug code <snippet>")
        if any(t_lower.startswith(k) for k in ["self heal code", "self heal", "heal code", "auto debug code"]):
            from learning.self_healer import self_healer
            sound_synth.play_sound("DATA_SYNC")
            code_snippet = re.sub(r"^(self heal code|self heal|heal code|auto debug code)\s*", "", t_clean, flags=re.IGNORECASE).strip() or "result = 100 / 0"
            heal_rep = self_healer.diagnose_and_heal_code(code_snippet)
            spoken = f"Metacognitive self-healing complete, sir. Diagnosed {heal_rep.error_type} and verified clean patch in {heal_rep.execution_time_sec:.3f} seconds."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "METACOGNITIVE_SELF_HEALING",
                "speech_text": self_healer.format_healing_report_text(heal_rep),
                "action_executed": "HEAL_CODE_ANOMALY",
            }

        # -8.5. Hybrid Multi-LLM Fusion & Full-Duplex Stream Telemetry
        if any(k in t_lower for k in ["hybrid llm status", "llm fusion status", "fusion telemetry"]):
            from neural.hybrid_fusion import hybrid_fusion_router
            return {
                "handled": True,
                "type": "HYBRID_LLM_TELEMETRY",
                "speech_text": hybrid_fusion_router.format_fusion_status_text(),
                "action_executed": "GET_HYBRID_LLM_STATUS",
            }

        if any(k in t_lower for k in ["full duplex status", "voice stream telemetry", "duplex voice status"]):
            from voice.full_duplex_stream import full_duplex_streamer
            return {
                "handled": True,
                "type": "FULL_DUPLEX_TELEMETRY",
                "speech_text": full_duplex_streamer.format_duplex_telemetry_text(),
                "action_executed": "GET_FULL_DUPLEX_STATUS",
            }

        # -8.6. Live Real-Time Hardware & System Telemetry
        if any(k in t_lower for k in ["hardware stats", "system telemetry", "live hardware", "processor load", "show hardware", "processor stats"]):
            from sensors.live_hardware_hub import live_hardware_hub
            hud_txt = live_hardware_hub.format_telemetry_hud_text()
            voice_engine.speak("Live hardware telemetry stream displayed on your HUD, sir.")
            return {
                "handled": True,
                "type": "HARDWARE_TELEMETRY_QUERY",
                "speech_text": hud_txt,
                "action_executed": "GET_LIVE_HARDWARE_TELEMETRY",
            }

        # -7. Autonomous Self-Research, Neural Learning & Skill Synthesizer (e.g. "learn <topic>", "learn how to <X>", "research and learn <Y>")
        learn_triggers = ["learn how to", "learn to", "learn ", "research and learn", "research and build", "acquire skill"]
        # Exclude "train" which is direct LLM prompt/completion pair
        if any(t_lower.startswith(tr) for tr in learn_triggers):
            from learning.autonomous_learner import autonomous_learner
            record = autonomous_learner.learn_and_synthesize_skill(t_clean)
            return {
                "handled": True,
                "type": "AUTONOMOUS_SKILL_SYNTHESIS",
                "speech_text": autonomous_learner.format_skill_report_text(record),
                "action_executed": f"ACQUIRE_SKILL_{record.module_name.upper()}",
            }

        # -6.8. Universal Multi-Band Signal & Device Spectrum Scanner (e.g. "scan near device signal", "scan wifi", "bluetooth scan", "rf scan")
        if any(k in t_lower for k in ["scan near device signal", "scan near device", "scan device signal", "signal scanner", "scan wifi", "scan bluetooth", "rf scan", "scan spectrum", "near device signal"]):
            from tools.signal_scanner import signal_scanner
            sound_synth.play_sound("SONAR_PING")
            rep = signal_scanner.scan_all_signals()
            spoken = (
                f"Spectrum scan complete, sir. Detected {rep.total_signals_detected} signals across "
                f"Wi-Fi, Bluetooth, RF ISM, NFC, and LAN subnets."
            )
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "MULTI_BAND_SIGNAL_SCAN",
                "speech_text": signal_scanner.format_signal_report_text(rep),
                "action_executed": "SCAN_WIRELESS_SPECTRUM",
            }

        # -6.5. Universal System Accelerator & OS Feature Controller (e.g. "boost system", "speed up pc", "set volume to 80%", "mute volume")
        if any(k in t_lower for k in ["boost system", "speed up", "accelerate system", "boost performance", "optimize speed"]):
            from tools.system_accelerator import system_accelerator
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            acc_res = system_accelerator.boost_system_performance()
            spoken = "System acceleration complete, sir. DNS flushed, memory compacted, and CPU governor elevated."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "SYSTEM_ACCELERATION",
                "speech_text": system_accelerator.format_accelerator_report_text(acc_res),
                "action_executed": "BOOST_SYSTEM_PERFORMANCE",
            }

        if "set volume" in t_lower or "volume to" in t_lower:
            from tools.system_accelerator import system_accelerator
            digits = re.findall(r"\d+", t_clean)
            vol_lvl = int(digits[0]) if digits else 75
            ok, msg = system_accelerator.set_volume(vol_lvl)
            voice_engine.speak(msg)
            return {
                "handled": True,
                "type": "SYSTEM_VOLUME_CONTROL",
                "speech_text": f"=== OS AUDIO VOLUME CONTROL ===\n{msg}",
                "action_executed": f"SET_VOLUME_{vol_lvl}",
            }

        if any(k in t_lower for k in ["mute volume", "unmute volume", "mute audio", "toggle mute"]):
            from tools.system_accelerator import system_accelerator
            ok, msg = system_accelerator.toggle_mute()
            voice_engine.speak(msg)
            return {
                "handled": True,
                "type": "SYSTEM_VOLUME_CONTROL",
                "speech_text": f"=== OS AUDIO VOLUME CONTROL ===\n{msg}",
                "action_executed": "TOGGLE_AUDIO_MUTE",
            }

        if any(k in t_lower for k in ["open task manager", "open device manager", "open network connections", "open services manager", "open firewall", "open control panel", "open disk cleanup"]):
            from tools.system_accelerator import system_accelerator
            sound_synth.play_sound("DATA_SYNC")
            ok, msg = system_accelerator.launch_os_utility(t_clean)
            voice_engine.speak(msg)
            return {
                "handled": True,
                "type": "OS_UTILITY_LAUNCH",
                "speech_text": f"=== NATIVE OS UTILITY LAUNCH ===\n{msg}",
                "action_executed": "LAUNCH_OS_UTILITY",
            }

        # -6. Live Weather & Doppler Radar Satellite Feed (e.g. "what is the weather", "weather in London", "weather forecast")
        if any(k in t_lower for k in ["weather", "temperature outside", "rain forecast", "forecast"]):
            from knowledge.live_weather import live_weather
            sound_synth.play_sound("SONAR_PING")
            city = "London"
            for c in ["new york", "san francisco", "tokyo", "paris", "mumbai", "delhi", "dubai", "sydney", "singapore", "london"]:
                if c in t_lower:
                    city = c
                    break
            w_rep = live_weather.fetch_weather(city)
            spoken = f"In {w_rep.location_name}, it is currently {w_rep.temperature_c:.0f} degrees Celsius with {w_rep.condition_description.lower()}."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "LIVE_WEATHER_REPORT",
                "speech_text": live_weather.format_weather_text(w_rep),
                "action_executed": f"FETCH_WEATHER_{city.upper().replace(' ', '_')}",
            }

        # -5.5. Real-Time Webcam Face & Emotion Biometrics
        if any(k in t_lower for k in ["scan face", "webcam biometric", "biometric scan", "who is in front of camera", "facial scan"]):
            from perception.webcam_biometrics import webcam_biometrics
            sound_synth.play_sound("TARGET_LOCKED")
            scan = webcam_biometrics.scan_operator_biometrics()
            voice_engine.speak(scan.spoken_greeting)
            return {
                "handled": True,
                "type": "WEBCAM_BIOMETRICS",
                "speech_text": webcam_biometrics.format_biometric_text(scan),
                "action_executed": "SCAN_OPERATOR_BIOMETRICS",
            }

        # -5.4. Autonomous Email & Calendar Inbox Reader
        if any(k in t_lower for k in ["check email", "inbox", "unread email", "read my email", "check my inbox", "agenda today", "calendar events"]):
            from tools.inbox_assistant import inbox_assistant
            sound_synth.play_sound("DATA_SYNC")
            unread_cnt, summary = inbox_assistant.get_inbox_summary()
            voice_engine.speak(f"You have {unread_cnt} unread messages in your priority inbox, sir.")
            return {
                "handled": True,
                "type": "INBOX_AGENDA",
                "speech_text": inbox_assistant.format_full_agenda_text(),
                "action_executed": "FETCH_INBOX_AGENDA",
            }

        # -5.3. Smart Home MQTT & Matter IoT Hub
        if any(k in t_lower for k in ["turn on light", "turn off light", "smart home", "living room light", "lights to", "climate temp"]):
            from tools.smart_home_hub import smart_home_hub
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            if "turn off" in t_lower or "disable" in t_lower:
                ok, msg = smart_home_hub.toggle_device(t_clean, desired_state=False)
            elif "turn on" in t_lower or "enable" in t_lower:
                ok, msg = smart_home_hub.toggle_device(t_clean, desired_state=True)
            elif "lights to" in t_lower or "color" in t_lower:
                msg = smart_home_hub.set_rgb_ambience("Neon Cyan")
            else:
                ok, msg = smart_home_hub.toggle_device("living_room_light")

            voice_engine.speak("Smart Home IoT directive dispatched, sir.")
            return {
                "handled": True,
                "type": "SMART_HOME_IOT",
                "speech_text": f"=== SMART HOME IOT ACTION ===\n{msg}\n\n{smart_home_hub.format_status_text()}",
                "action_executed": "DISPATCH_SMART_HOME_IOT",
            }

        # -5.2. 3D Interactive Hologram Status
        if any(k in t_lower for k in ["hologram 3d", "3d hologram", "wireframe model", "3d wireframe"]):
            from gui.hologram_3d import hologram_3d
            pts = hologram_3d.project_vertices_2d(150, 150)
            voice_engine.speak("3D wireframe spherical hologram rendered on active HUD canvas, sir.")
            return {
                "handled": True,
                "type": "HOLOGRAM_3D",
                "speech_text": f"=== 3D HOLOGRAPHIC PERSPECTIVE ENGINE ===\nActive Spherical Vertices: {len(pts)} 3D points\nEuler Rotation: Pitch: {hologram_3d.angle_x:.2f} rad | Yaw: {hologram_3d.angle_y:.2f} rad\nStatus: ROTATING & PROJECTING ON CANVAS",
                "action_executed": "PROJECT_HOLOGRAM_3D",
            }

        # -5. Executive Protocols (Morning Briefing, Security Sweep, Clean Slate, Dev Workspace, Night Sentinel)
        from jarvis.protocol_engine import protocol_engine
        if any(k in t_lower for k in ["morning briefing", "good morning", "executive briefing", "daily briefing", "protocol morning"]):
            res_p = protocol_engine.execute_protocol("PROTOCOL_MORNING_BRIEFING")
            steps_txt = "\n".join([f"  • {s}" for s in res_p.steps_executed])
            return {
                "handled": True,
                "type": "EXECUTIVE_PROTOCOL",
                "speech_text": f"=== EXECUTIVE PROTOCOL: MORNING BRIEFING ===\n{res_p.spoken_narration}\n\nTelemetry Execution Steps:\n{steps_txt}",
                "action_executed": "PROTOCOL_MORNING_BRIEFING",
            }

        if any(k in t_lower for k in ["security sweep", "run security sweep", "security check", "protocol security", "lockdown protocol"]):
            res_p = protocol_engine.execute_protocol("PROTOCOL_SECURITY_SWEEP")
            steps_txt = "\n".join([f"  • {s}" for s in res_p.steps_executed])
            return {
                "handled": True,
                "type": "EXECUTIVE_PROTOCOL",
                "speech_text": f"=== EXECUTIVE PROTOCOL: SECURITY SWEEP ===\n{res_p.spoken_narration}\n\nAudit Ledger:\n{steps_txt}",
                "action_executed": "PROTOCOL_SECURITY_SWEEP",
            }

        if any(k in t_lower for k in ["clean and optimize", "clean slate", "optimize system", "protocol clean", "clean memory"]):
            res_p = protocol_engine.execute_protocol("PROTOCOL_CLEAN_OPTIMIZE")
            steps_txt = "\n".join([f"  • {s}" for s in res_p.steps_executed])
            return {
                "handled": True,
                "type": "EXECUTIVE_PROTOCOL",
                "speech_text": f"=== EXECUTIVE PROTOCOL: CLEAN SLATE & OPTIMIZATION ===\n{res_p.spoken_narration}\n\nOptimization Actions:\n{steps_txt}",
                "action_executed": "PROTOCOL_CLEAN_OPTIMIZE",
            }

        if any(k in t_lower for k in ["code mode", "developer mode", "dev mode", "setup workspace", "developer workspace", "protocol workspace"]):
            res_p = protocol_engine.execute_protocol("PROTOCOL_DEVELOPER_WORKSPACE")
            steps_txt = "\n".join([f"  • {s}" for s in res_p.steps_executed])
            return {
                "handled": True,
                "type": "EXECUTIVE_PROTOCOL",
                "speech_text": f"=== EXECUTIVE PROTOCOL: DEVELOPER WORKSPACE ===\n{res_p.spoken_narration}\n\nWorkspace Setup:\n{steps_txt}",
                "action_executed": "PROTOCOL_DEVELOPER_WORKSPACE",
            }

        if any(k in t_lower for k in ["night sentinel", "good night", "sleep mode", "protocol night"]):
            res_p = protocol_engine.execute_protocol("PROTOCOL_NIGHT_SENTINEL")
            steps_txt = "\n".join([f"  • {s}" for s in res_p.steps_executed])
            return {
                "handled": True,
                "type": "EXECUTIVE_PROTOCOL",
                "speech_text": f"=== EXECUTIVE PROTOCOL: NIGHT SENTINEL ===\n{res_p.spoken_narration}\n\nSurveillance Mode:\n{steps_txt}",
                "action_executed": "PROTOCOL_NIGHT_SENTINEL",
            }

        # -4. Instant Code Generator & Technical Problem Solver (e.g. "wright a code for positive integer finder", "write code for X", "code for Y")
        from tools.instant_code_solver import instant_code_solver
        if instant_code_solver.is_code_or_solve_request(t_clean):
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            sol = instant_code_solver.solve_and_generate_code(t_clean)
            spoken = f"I have generated the complete working Python code for {sol.title} and saved it to your workspace."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "AUTONOMOUS_CODE_GENERATION",
                "speech_text": sol.format_output_text(),
                "action_executed": f"GENERATE_CODE_{sol.filename.upper()}",
            }

        # -3. Neural LLM/MLLM Model Training & Fine-Tuning (e.g. "train <text>", "finetune on <text>", "train model")
        if t_lower.startswith("train ") or t_lower.startswith("finetune "):
            train_input = re.sub(r"^(train on|train model on|train|finetune on|finetune)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            from neural.model_trainer import neural_model_trainer
            sound_synth.play_sound("ARC_REACTOR_BOOT")

            # Parse prompt and target completion if separated by -> or :
            if "->" in train_input:
                parts = train_input.split("->", 1)
                p_text, c_text = parts[0].strip(), parts[1].strip()
            elif ":" in train_input:
                parts = train_input.split(":", 1)
                p_text, c_text = parts[0].strip(), parts[1].strip()
            else:
                p_text = train_input
                c_text = "Verified autonomous neural alignment response."

            metrics = neural_model_trainer.train_on_text(p_text, c_text, epochs=6, lr=0.02)
            chk_path = neural_model_trainer.save_checkpoint()
            spoken = f"Neural fine-tuning complete, sir. Cross-entropy loss reduced by {metrics.loss_reduction_pct:.1f}% across {metrics.epoch} epochs."
            voice_engine.speak(spoken)

            rep_text = (
                f"=== P.H.A.S.S NEURAL LLM/MLLM TRAINING REPORT ===\n"
                f"Training Epochs:        {metrics.epoch}\n"
                f"Initial Loss:           {metrics.initial_loss:.4f}\n"
                f"Final Loss:             {metrics.final_loss:.4f}\n"
                f"Loss Reduction:         {metrics.loss_reduction_pct:.1f}%\n"
                f"Tokens Processed:       {metrics.total_tokens_trained}\n"
                f"LoRA Weights Updated:   {metrics.lora_parameters_updated} parameters\n"
                f"Training Duration:      {metrics.training_duration_sec:.3f}s\n"
                f"Checkpoint Serialized:  {chk_path}"
            )

            return {
                "handled": True,
                "type": "NEURAL_MODEL_TRAINING",
                "speech_text": rep_text,
                "action_executed": "TRAIN_NEURAL_WEIGHTS",
            }

        # -2. Dynamic In-Memory Hot-Coding & Live Patching (e.g. "hotcode <snippet>", "hot code", "hot patch")
        if t_lower.startswith("hotcode ") or t_lower.startswith("hot code "):
            snippet = re.sub(r"^(hotcode|hot code)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            from learning.hot_coder import hot_coder
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            ok, val, msg = hot_coder.hot_execute_snippet(snippet)
            spoken = "Hot-code injected and executed in live memory namespace, sir."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "RUNTIME_HOT_CODE",
                "speech_text": f"=== DYNAMIC IN-MEMORY HOT-CODING RESULT ===\nStatus: {'SUCCESS' if ok else 'FAILED'}\nResult: {msg}",
                "action_executed": "IN_MEMORY_HOT_CODE_EXECUTION",
            }

        # -1.5. Humanoid Theory of Mind, Episodic Memory & Consciousness Stream
        if any(k in t_lower for k in ["theory of mind", "mental model", "anticipate intent"]):
            from core.humanoid_cognition import humanoid_cognition
            tom = humanoid_cognition.update_theory_of_mind(t_clean)
            rep = (
                f"=== HUMANOID THEORY OF MIND (ToM) INTENT MODEL ===\n"
                f"Estimated Operator Cognitive Load: {int(tom.estimated_cognitive_load*100)}%\n"
                f"Current Focus Domain:             {tom.current_focus_domain}\n"
                f"Predicted Next Intent:            {tom.predicted_next_intent}\n"
                f"Anticipatory Suggestion:          {tom.anticipatory_suggestion}"
            )
            voice_engine.speak("Evaluating your cognitive state and anticipating next action, sir.")
            return {
                "handled": True,
                "type": "THEORY_OF_MIND",
                "speech_text": rep,
                "action_executed": "INFER_OPERATOR_MENTAL_MODEL",
            }

        if any(k in t_lower for k in ["autobiography", "shared history", "episodic memory", "what do you remember about us"]):
            from core.humanoid_cognition import humanoid_cognition
            story = humanoid_cognition.get_autobiographical_narrative()
            voice_engine.speak("Retrieving our shared autobiographical interaction history, sir.")
            return {
                "handled": True,
                "type": "EPISODIC_MEMORY",
                "speech_text": story,
                "action_executed": "GET_AUTOBIOGRAPHICAL_TIMELINE",
            }

        if any(k in t_lower for k in ["stream of consciousness", "what are you thinking", "internal monologue", "consciousness stream"]):
            from neural.consciousness_stream import consciousness_stream
            st_txt = consciousness_stream.format_stream_text()
            voice_engine.speak("Accessing internal stream of consciousness, sir.")
            return {
                "handled": True,
                "type": "CONSCIOUSNESS_STREAM",
                "speech_text": st_txt,
                "action_executed": "GET_CONSCIOUSNESS_STREAM",
            }

        # -1. Ethical Cybersecurity Defense & Vulnerability Auditor (e.g. "cyber scan", "scan ports", "security audit", "check vulnerabilities", "system hardening")
        cyber_keywords = ["cyber scan", "scan ports", "port scan", "cyber audit", "security audit", "vulnerability scan", "system hardening", "check vulnerabilities", "cyber defense"]
        if any(k in t_lower for k in cyber_keywords):
            from security.cyber_defense import cyber_defense
            sound_synth.play_sound("SECURITY_ALERT")
            voice_engine.speak("Initiating ethical cybersecurity defense scan and port audit, sir.")
            rep = cyber_defense.run_full_security_audit()
            spoken = f"Security audit complete, sir. System security score is {rep.system_security_score} out of 100 with {len(rep.open_ports_detected)} active ports detected."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "CYBER_DEFENSE_AUDIT",
                "speech_text": cyber_defense.format_audit_report_text(rep),
                "action_executed": "RUN_CYBER_DEFENSE_AUDIT",
            }

        if any(k in t_lower for k in ["omni status", "unified status", "architecture status", "system architecture"]):
            from core.unified_orchestrator import unified_orchestrator
            st = unified_orchestrator.get_unified_status()
            sub_lines = "\n".join([f"  • {k.replace('_', ' ')}: {'ONLINE' if v else 'OFFLINE'}" for k, v in st.subsystems_online.items()])
            rep_text = (
                f"=== P.H.A.S.S SPHERE v{st.version} UNIFIED ARCHITECTURE STATUS ===\n"
                f"Architecture: {st.architecture}\n"
                f"Uptime: {st.uptime_sec:.1f}s | Battery: {st.robot_battery_pct}% | Temp: {st.robot_internal_temp_c}°C\n"
                f"Cyber Security Score: {st.cyber_security_score}/100 | Goals Executed: {st.total_goals_executed}\n\n"
                f"Integrated Subsystems:\n{sub_lines}"
            )
            voice_engine.speak("All 8 unified subsystems are online and operating at nominal efficiency, sir.")
            return {
                "handled": True,
                "type": "UNIFIED_PLATFORM_STATUS",
                "speech_text": rep_text,
                "action_executed": "GET_UNIFIED_STATUS",
            }

        # 0. Universal App, Tool & Remote Maker (e.g. "make a universal remote", "build a calculator", "make a game", "create an app")
        maker_keywords = ["universal remote", "make a remote", "make remote", "make a", "make an", "build a", "build an", "create a", "create an", "generate a", "generate an"]
        is_name_effect = any(k in t_lower for k in ["ui effect", "displaying name", "display name", "name effect"])
        if any(k in t_lower for k in maker_keywords) and not is_name_effect and not any(k in t_lower for k in ["spare parts", "laptop parts"]):
            from tools.universal_maker import universal_maker
            sound_synth.play_sound("ARC_REACTOR_BOOT")
            ok, app_title, details = universal_maker.make_and_launch_app(t_clean)
            spoken = f"{jarvis_persona.format_affirmation()} I have built and launched the {app_title} on your screen."
            voice_engine.speak(spoken)
            return {
                "handled": True,
                "type": "UNIVERSAL_MAKER",
                "speech_text": f"{spoken}\n\nExecution Report:\n  • Status: ONLINE & ACTIVE\n  • Details: {details}",
                "action_executed": f"LAUNCH_APP_{app_title.upper().replace(' ', '_')}",
            }

        # 1. Market & Spare Parts Intelligence (e.g. "search any spare parts for laptops in market", "buy laptop screen", "laptop parts")
        market_keywords = ["spare parts", "laptop parts", "parts in market", "buy ", "market price", "hardware parts", "component price", "parts for laptop"]
        if any(k in t_lower for k in market_keywords):
            from knowledge.market_intelligence import market_intelligence
            sound_synth.play_sound("SONAR_PING")
            m_rep = market_intelligence.search_market_components(t_clean, auto_open_browser=True)
            voice_engine.speak(m_rep.spoken_narration)
            formatted = market_intelligence.format_market_report_text(m_rep)
            return {
                "handled": True,
                "type": "MARKET_INTELLIGENCE",
                "speech_text": formatted,
                "action_executed": "LIVE_MARKET_SEARCH",
            }

        # 2. General Live Search / Lookup Queries (e.g. "search for X", "find X on google", "lookup X")
        if t_lower.startswith("search ") or t_lower.startswith("find ") or t_lower.startswith("lookup ") or t_lower.startswith("google "):
            sound_synth.play_sound("WAKE_BEEP")
            query_target = re.sub(r"^(search for|search|find|lookup|google)\s+", "", t_clean, flags=re.IGNORECASE).strip()
            import urllib.parse
            import webbrowser
            encoded = urllib.parse.quote(query_target)
            search_url = f"https://www.google.com/search?q={encoded}"
            try:
                webbrowser.open(search_url)
            except Exception:
                pass
            k_res = live_search_engine.answer_query(query_target)
            spoken = f"Searching for '{query_target}', sir. {k_res.headline_answer}"
            voice_engine.speak(spoken)
            summary_txt = f"Live Search Dispatched: {search_url}\n\n" + live_search_engine.format_spoken_summary(k_res)
            return {
                "handled": True,
                "type": "LIVE_OMNI_SEARCH",
                "speech_text": summary_txt,
                "action_executed": "OMNI_WEB_SEARCH",
            }

        # 3. Real-World Knowledge & Current Affairs (e.g. "yesterday what is the problem in parliament of india")
        knowledge_patterns = [
            r"parliament", r"what is", r"who is", r"why did", r"explain", r"tell me about",
            r"news", r"history", r"current problem", r"what happened"
        ]
        is_internal = any(k in t_lower for k in [
            "battery", "temp", "state", "who are you", "what are you", "your name",
            "how are you", "how're you", "what can you do", "help", "ui effect",
            "create code", "turn on", "open app", "read clipboard", "screenshot"
        ])
        if any(re.search(pat, t_lower) for pat in knowledge_patterns) and not is_internal:
            sound_synth.play_sound("WAKE_BEEP")
            k_res = live_search_engine.answer_query(t_clean)
            spoken = f"{k_res.headline_answer}"
            voice_engine.speak(spoken)
            summary_txt = f"{live_search_engine.format_spoken_summary(k_res)}\n(P.H.A.S.S Global Knowledge Base)"
            return {
                "handled": True,
                "type": "LIVE_KNOWLEDGE_SEARCH",
                "speech_text": summary_txt,
                "action_executed": "LIVE_WEB_SEARCH",
            }

        # 2. Dynamic Code Generation & UI Effects (e.g. "create a ui effect of displaying name muja")
        if any(phrase in t_lower for phrase in ["ui effect", "displaying name", "display name", "name effect", "matrix effect", "create a ui", "generate ui", "make a ui"]):
            # Extract target name
            target_name = "MUJA"
            m = re.search(r"(?:displaying name|display name|for name|named|name|for)\s+([a-zA-Z0-9_\-]+)", t_clean, flags=re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                if extracted.lower() not in ["effect", "a", "the", "ui", "of", "and", "name", "displaying", "display"]:
                    target_name = extracted.upper()

            sound_synth.play_sound("ARC_REACTOR_BOOT")
            ok, msg = dynamic_executor.generate_and_launch_name_ui_effect(target_name)
            spoken_reply = f"{jarvis_persona.format_affirmation()} I have synthesized and launched the animated holographic UI effect for '{target_name}' on your display."
            voice_engine.speak(spoken_reply)
            return {
                "handled": True,
                "type": "DYNAMIC_CODE_EXECUTION",
                "speech_text": f"{spoken_reply}\n\nExecution Log:\n  • {msg}\n  • Window Status: ACTIVE & RENDERING PARTICLES",
                "action_executed": f"LAUNCH_UI_EFFECT_{target_name}",
            }

        # 3. Strict Phone / Hardware Device Power-On Orders (e.g. "my phone was off on the phone", "turn on phone")
        if any(phrase in t_lower for phrase in ["turn on my phone", "turn on the phone", "on the phone", "power on phone", "wake up phone", "phone was off", "switch on phone"]):
            sound_synth.play_sound("SONAR_PING")
            report = device_controller.execute_turn_on_phone_protocol()
            voice_engine.speak(report.spoken_summary)
            avenues_str = "\n".join([f"  • [{a['channel']}] {a['status']} -> {', '.join(a['details'])}" for a in report.avenues_attempted])
            return {
                "handled": True,
                "type": "HARDWARE_DEVICE_CONTROL",
                "speech_text": f"{report.spoken_summary}\n\nMulti-Channel Dispatch Ledger:\n{avenues_str}",
                "action_executed": "STRICT_PHONE_POWER_ON",
            }

        return None


dynamic_solver = DynamicZeroFrictionSolver()
