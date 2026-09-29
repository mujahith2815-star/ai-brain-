"""
Interactive Standalone AI Model Chat Interface for P.H.A.S.S Sphere v8.0.
Chat with the trained P.H.A.S.S model locally via clean, warm, friendly conversational language.
Supports Dual-Brain Architecture (Primary Native Core + Secondary Brain Phi-4).
"""

import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Auto-detect and re-exec with virtual environment if current python is not .venv
    venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python) and os.path.normpath(sys.executable).lower() != os.path.normpath(venv_python).lower():
        if not os.environ.get("_ORVIX_VENV_SWITCHED"):
            os.environ["_ORVIX_VENV_SWITCHED"] = "1"
            import subprocess
            res = subprocess.run([venv_python] + sys.argv, cwd=BASE_DIR)
            sys.exit(res.returncode)

# Redirect all paths to BASE_DIR
os.chdir(BASE_DIR)

# Ensure runtime folders exist
for folder in ['logs', 'knowledge', 'models', 'proactive']:
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

# UTF-8 encoding with character fallback protection
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, BASE_DIR)

from tools.ollama_manager import ollama_local_manager
from jarvis.persona import jarvis_persona, ChatPersonaMode
from core.secondary_brain import secondary_brain
from config.llama_config import llama_config
from core.llama_tool_agent import llama_tool_agent

try:
    from cli.rich_ui import print_banner as rich_print_banner, print_chat_message as rich_print_chat_message, print_status_table as rich_print_status_table
    RICH_CLI_AVAILABLE = True
except Exception:
    RICH_CLI_AVAILABLE = False

# Install global error capture hook for human-in-the-loop diagnostics
try:
    from logging.error_hook import setup_global_exception_hook
    setup_global_exception_hook()
except Exception:
    pass

# Startup Voice Integrity & Self-Healing Guard: Scan core/voice_interface.py, fix errors, test, and restart voice service
try:
    if not getattr(sys, "frozen", False):
        from core.voice_guardian import ensure_voice_interface_healthy
        _vg_res = ensure_voice_interface_healthy()
        if _vg_res.get("repaired"):
            print(f"[Voice Guardian] {_vg_res.get('message')}")
except Exception as _e:
    pass

from core.voice_interface import get_voice_interface, VoiceInterface
from config.voice_config import voice_config
from voice import SpeechSynthesizer, SpeechRecognizer, WakeWordDetector, VoiceLoop

# Singleton voice interface
voice = get_voice_interface()
voice_synthesizer = SpeechSynthesizer()
voice_recognizer = SpeechRecognizer()
voice_wake_detector = WakeWordDetector()


def process_query(text: str) -> str:
    """Process a query through the P.H.A.S.S strict execution engine with response sanitization."""
    from nlp.answer_pipeline import process_query as _process_query
    return _process_query(text)


def process_voice_command(text: str) -> str:
    """Process voice command input and speak the assistant response."""
    print(f"\n🎤 Heard: {text}")
    response = process_query(text)
    print(f"🤖 Response: {response}\n")
    voice_intf = get_voice_interface()
    voice_intf.speak(response)
    return response


def handle_universal_slash_command(user_input: str) -> bool:
    """Handles Universal Control & Terminal Mastery slash commands. Returns True if handled."""
    low = user_input.strip().lower()
    parts = user_input.strip().split(maxsplit=1)
    cmd_name = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd_name == "/cmd":
        from knowledge.commands import get_command_summary
        from tools.terminal_tools import lookup_command
        if not arg:
            s = get_command_summary()
            print("\n💻 Orvix Terminal Command Knowledge Base (v1.1.0):")
            print(f"  • Total Pre-loaded Commands: {s['total_commands']}")
            print(f"  • Supported Shells:          {', '.join(f'{k} ({v})' for k, v in s['shells'].items())}")
            print(f"  • Command Categories ({len(s['categories'])}): {', '.join(s['categories'].keys())}")
            print("\nUsage: /cmd <command_name>, /cmd-search <query>, /cmd-suggest <intent>, /cmd-explain <cmd>, /term <cmd>\n")
        else:
            res = lookup_command(arg)
            if res.get("status") == "SUCCESS":
                c = res["command"]
                print(f"\n📖 Command: {c.get('name')} [{c.get('shell').upper()}]")
                print(f"  • Category:    {c.get('category')}")
                print(f"  • Description: {c.get('description')}")
                print(f"  • Syntax:      {c.get('syntax')}")
                if c.get("flags"):
                    print("  • Flags:")
                    for f, desc in c["flags"].items():
                        print(f"      {f:<12} {desc}")
                if c.get("examples"):
                    print("  • Examples:")
                    for ex in c["examples"]:
                        if isinstance(ex, dict):
                            print(f"      {ex.get('cmd'):<30} # {ex.get('desc')}")
                equiv = c.get("windows_equivalent") or c.get("linux_equivalent")
                if equiv:
                    print(f"  • Cross-Platform Equivalent: {equiv}")
                print(f"  • Safety:      {c.get('safety', 'safe').upper()} (destructive: {c.get('is_destructive', False)})\n")
            else:
                print(f"\n⚠️ {res.get('message', 'Command not found')}\n")
        return True

    elif cmd_name == "/cmd-search":
        from knowledge.commands import search_commands
        if not arg:
            print("\n⚠️ Usage: /cmd-search <keyword or phrase>\n")
        else:
            results = search_commands(arg, limit=6)
            print(f"\n🔍 Command Search Results for '{arg}' ({len(results)} matches):")
            for r in results:
                print(f"  • {r.get('name'):<18} [{r.get('shell')}] {r.get('description')[:60]}")
                print(f"      Syntax: {r.get('syntax')}")
            print()
        return True

    elif cmd_name == "/cmd-suggest":
        from tools.terminal_tools import suggest_command
        if not arg:
            print("\n⚠️ Usage: /cmd-suggest <natural language intent>\n")
        else:
            res = suggest_command(arg)
            print(f"\n💡 Command Suggestions for intent '{arg}':")
            for s in res.get("suggestions", []):
                print(f"  • {s.get('name'):<15} [{s.get('shell')}] - {s.get('description')}")
                print(f"      Syntax: {s.get('syntax')}")
            print()
        return True

    elif cmd_name == "/cmd-find":
        from tools.command_brain import CommandBrain
        if not arg:
            print("\n⚠️ Usage: /cmd-find <task description or intent>\n")
        else:
            brain = CommandBrain()
            res = brain.find(arg)
            layer_label = {
                "layer1_core": "Layer 1: Core Catalog",
                "layer2_discovered": "Layer 2: Discovered OS Cache",
                "layer2_live": "Layer 2: Live OS Discovery",
                "layer3_learned": "Layer 3: Learned Patterns",
            }.get(res.get("layer"), "Unknown Layer")
            print(f"\n🧠 Command Brain Cascade Search [{layer_label}] for '{arg}':")
            if not res.get("results"):
                print(f"  No exact command found. {res.get('message', '')}\n")
            else:
                for r in res["results"]:
                    print(f"  • {r.get('name'):<20} [{r.get('shell', 'any')}] (Confidence: {int(r.get('confidence', 0)*100)}%)")
                    print(f"      Syntax: {r.get('syntax')}")
                    if r.get("description"):
                        print(f"      Desc:   {r.get('description')[:80]}")
                print()
        return True

    elif cmd_name == "/cmd-explain":
        from tools.command_brain import CommandBrain
        if not arg:
            print("\n⚠️ Usage: /cmd-explain <command string>\n")
        else:
            brain = CommandBrain()
            exp = brain.explain(arg)
            print(f"\n🔬 Command Documentation & Analysis for '{arg}':")
            print(f"  • Source:       {exp.get('source')}")
            if exp.get("shell"):
                print(f"  • Shell:        {exp.get('shell')}")
            if exp.get("category"):
                print(f"  • Category:     {exp.get('category')}")
            if exp.get("description"):
                print(f"  • Description:  {exp.get('description')}")
            if exp.get("syntax"):
                print(f"  • Syntax:       {exp.get('syntax')}")
            if exp.get("parameters"):
                print("  • Parameters:")
                for param in exp["parameters"][:6]:
                    print(f"      {param}")
            if exp.get("examples"):
                print("  • Examples:")
                for ex in exp["examples"][:4]:
                    if isinstance(ex, dict):
                        print(f"      {ex.get('cmd'):<30} # {ex.get('desc')}")
                    else:
                        print(f"      {ex}")
            if exp.get("safety"):
                print(f"  • Safety Level: {exp.get('safety').upper()}")
            print()
        return True

    elif cmd_name == "/cmd-categories":
        from knowledge.commands import get_all_categories, get_by_category
        cats = get_all_categories()
        print(f"\n📂 Command Categories ({len(cats)} available):")
        for c in cats:
            count = len(get_by_category(c))
            print(f"  • {c:<16} ({count} commands)")
        print("\nTip: Use '/cmd-search <category>' to explore commands in any category.\n")
        return True

    elif cmd_name == "/cmd-learned":
        from knowledge.commands import load_learned_commands
        learned = load_learned_commands()
        print(f"\n🧠 Autonomous Feedback Learner ({len(learned)} commands learned):")
        if not learned:
            print("  No custom commands learned yet. As you execute terminal commands, the agent will learn your patterns.\n")
        else:
            for l in learned:
                print(f"  • {l.get('name'):<18} ({l.get('times_executed', 1)} runs, {l.get('success_count', 1)} successes)")
                print(f"      Syntax: {l.get('syntax')}")
            print()
        return True

    elif cmd_name == "/cmd-history":
        from knowledge.commands import get_success_rate, get_history
        stats = get_success_rate()
        recent = get_history(limit=5)
        print("\n📊 Terminal Execution History & Analytics:")
        print(f"  • Total Commands Executed: {stats['total_executed']}")
        print(f"  • Success Rate:            {stats['success_rate_percent']}% ({stats['successful']} success, {stats['failed']} failed)")
        print(f"  • Average Duration:        {stats['avg_duration_ms']} ms")
        if recent:
            print("  • Recent Executions:")
            for r in recent:
                st_icon = "[OK]" if r["success"] else "[X]"
                print(f"      {st_icon} {r['command']:<30} (shell: {r['shell']}, {round(r['execution_time_ms'], 1)}ms)")
        print()
        return True

    elif cmd_name == "/cmd-stats":
        from tools.command_brain import CommandBrain
        brain = CommandBrain()
        st = brain.stats()
        print(f"\n📊 3-Layer Command Intelligence System (v1.2.0):")
        print(f"  • Layer 1 (Core Commands):       {st['layer1_core_commands']} pre-loaded commands")
        print(f"  • Layer 2 (Discovered OS Tools):  {st['layer2_discovered_total']} cached in SQLite")
        for src, cnt in st.get("layer2_by_source", {}).items():
            print(f"      - {src:<14} : {cnt} tools")
        print(f"  • Layer 3 (Learned Patterns):    {st['layer3_learned_patterns']} workflow chains")
        print(f"  • Status:                        {st['status']}\n")
        return True

    elif cmd_name == "/cmd-discover":
        from tools.command_discovery import CommandDiscovery
        print("\n🔍 Running live OS discovery across PowerShell, System32, Bash, Python, and Winget...")
        disc = CommandDiscovery()
        res = disc.discover_all()
        print(f"  ✓ Discovery Complete! Total tools found: {res['total']}")
        for src, cnt in res.get("by_source", {}).items():
            print(f"      - {src:<14} : {cnt} tools")
        print()
        return True

    elif cmd_name == "/cmd-patterns":
        from knowledge.commands.command_patterns import get_all_patterns
        pats = get_all_patterns()
        print(f"\n🧩 Learned Multi-Command Workflow Patterns ({len(pats)} patterns):")
        if not pats:
            print("  No multi-command patterns promoted yet. Repeating successful command chains promotes them automatically.\n")
        else:
            for p in pats:
                chain_str = " && ".join(p.get("command_chain", []))
                print(f"  • {p.get('pattern_name'):<25} (Successes: {p.get('success_count', 1)}, Shell: {p.get('shell')})")
                print(f"      Task:  {p.get('description')}")
                print(f"      Chain: {chain_str}")
            print()
        return True

    elif cmd_name == "/cmd-live":
        from tools.command_brain import CommandBrain
        if not arg:
            print("\n⚠️ Usage: /cmd-live <binary or keyword>\n")
        else:
            brain = CommandBrain()
            matches = brain._query_live_os(arg)
            print(f"\n⚡ Live OS Query Results for '{arg}':")
            if not matches:
                print("  No live command or binary found on OS PATH or PowerShell.\n")
            else:
                for m in matches:
                    print(f"  • {m.get('name'):<20} [{m.get('shell')}] {m.get('description')}")
                    print(f"      Path/Syntax: {m.get('syntax')}")
                print()
        return True

    elif cmd_name == "/term":
        from tools.terminal_tools import run_terminal
        if not arg:
            print("\n⚠️ Usage: /term <command to execute>\n")
        else:
            print(f"\n⚡ Executing: {arg}...")
            res = run_terminal(arg)
            print(f"Status: {res['status']} | Shell: {res['shell']} | Exit Code: {res['exit_code']} | Duration: {res['duration_ms']}ms")
            if res.get("stdout"):
                print(f"\n{res['stdout'].strip()}\n")
            if res.get("stderr"):
                print(f"\n[STDERR]\n{res['stderr'].strip()}\n")
        return True

    elif cmd_name in ("/sys", "/hw"):
        from tools.hardware_controller import get_hardware_summary
        hw = get_hardware_summary()
        cpu = hw.get("cpu", {})
        ram = hw.get("ram", {})
        disks = hw.get("disks", {}).get("disks", [])
        bat = hw.get("battery", {})
        print(f"\n🖥️ System & Hardware Overview:")
        print(f"  • OS:         {hw.get('os')}")
        print(f"  • CPU:        {cpu.get('processor_model')} ({cpu.get('logical_cores')} logical cores, {cpu.get('current_usage_percent')}% load)")
        if ram.get("total_gb"):
            print(f"  • RAM:        {ram.get('used_gb')} GB / {ram.get('total_gb')} GB ({ram.get('usage_percent')}%)")
        for d in disks[:3]:
            print(f"  • Disk [{d.get('mountpoint')}]: {d.get('used_gb')} GB / {d.get('total_gb')} GB ({d.get('usage_percent')}%)")
        if bat.get("has_battery"):
            print(f"  • Battery:    {bat.get('percent')}% (Plugged: {bat.get('power_plugged')})")
        print()
        return True

    elif cmd_name == "/apps":
        from tools.app_controller import list_running_apps
        apps_res = list_running_apps(limit=15)
        apps = apps_res.get("apps", [])
        print(f"\n📱 Running Desktop Applications ({len(apps)} found):")
        for a in apps:
            title = f" - '{a.get('title')[:40]}'" if a.get("title") else ""
            print(f"  • PID {a.get('pid'):<6} {a.get('name'):<20} {a.get('memory_mb', 0)} MB{title}")
        print()
        return True

    elif cmd_name == "/net":
        from tools.network_controller import get_ip_addresses, get_active_connections
        ips = get_ip_addresses().get("ip_addresses", [])
        conns = get_active_connections(limit=8).get("connections", [])
        print(f"\n🌐 Network Configuration & Connections:")
        print("  • IP Addresses:")
        for ip in ips:
            print(f"      {ip.get('interface'):<15} {ip.get('family'):<6} {ip.get('address')}")
        print(f"  • Active Sockets (showing first {len(conns)}):")
        for c in conns:
            print(f"      {c.get('type'):<5} {c.get('status'):<12} Local: {c.get('local_address')} | Remote: {c.get('remote_address')}")
        print()
        return True

    elif cmd_name == "/svc":
        from tools.service_controller import list_services
        svcs = list_services(limit=15).get("services", [])
        print(f"\n⚙️ System Services (showing {len(svcs)}):")
        for s in svcs:
            print(f"  • {s.get('name'):<25} Status: {s.get('status'):<10} ({s.get('display_name', '')[:35]})")
        print()
        return True

    elif cmd_name == "/proc":
        from tools.process_controller import list_processes
        procs = list_processes(sort_by="cpu", limit=12).get("processes", [])
        print(f"\n📈 Top Active Processes by CPU:")
        for p in procs:
            print(f"  • PID {p.get('pid'):<6} {p.get('name'):<22} CPU: {p.get('cpu_percent'):<5}% | RAM: {p.get('memory_mb'):<7} MB")
        print()
        return True

    elif cmd_name == "/router":
        from tools.model_router import model_router
        if not arg:
            st = model_router.get_status()
            print("\n🔀 Orvix Hybrid Model Router Status (v1.4.0):")
            print(f"  • Current Mode:      {st['mode'].upper()}")
            print(f"  • Primary Engine:    {st['primary_engine']['name']} ({st['primary_engine']['model']})")
            print(f"  • Primary Available: {'YES' if st['primary_engine']['available'] else 'NO (Missing API Key or Offline)'}")
            print(f"  • Fallback Engine:   {st['fallback_engine']['name']} ({st['fallback_engine']['model']})")
            print(f"  • Fallback Available:{'YES' if st['fallback_engine']['available'] else 'NO (Ollama or model not loaded)'}")
            print(f"  • Rate Limit RPM:    {st['rate_limits']['current_rpm']}/{st['rate_limits']['rpm_limit']} (Remaining: {st['rate_limits']['rpm_remaining']})")
            print("  • Routing Stats:")
            for k, v in st['stats'].items():
                print(f"      {k:<22} {v}")
            print("\nUsage: /router <auto | cloud_first | local_first | cloud_only | local_only>\n")
        else:
            try:
                new_mode = model_router.switch_mode(arg)
                print(f"\n✅ Model Router mode switched to: '{new_mode.upper()}'.\n")
            except Exception as e:
                print(f"\n⚠️ Error switching mode: {e}\n")
        return True

    elif cmd_name == "/engines":
        from tools.model_router import model_router
        print("\n🔍 Testing Cognitive Engines Connectivity & Latency...")
        t_res = model_router.test_engines()
        g = t_res.get("gemini", {})
        q = t_res.get("qwen", {})
        g_st = f"✅ Online ({g.get('latency_ms')} ms)" if g.get("available") else "⚠️ Offline"
        q_st = "✅ Ready (Ollama localhost:11434)" if q.get("available") else "⚠️ Offline"
        print(f"  • Gemini 2.0 Flash: {g_st} (Type: {g.get('type')})")
        print(f"  • Qwen2.5-7B (W:):  {q_st} (Type: {q.get('type')})")
        print(f"  • Current Route Mode: {t_res.get('current_mode').upper()}\n")
        return True

    elif cmd_name == "/qwen-download":
        from tools.qwen_downloader import download_qwen_model
        print("\n📥 Triggering Qwen2.5-7B Download to W: drive...")
        download_qwen_model()
        print()
        return True

    elif cmd_name == "/qwen-test":
        from tools.qwen_engine import qwen_engine
        print("\n🧪 Direct Probe: Querying Qwen2.5-7B on W: drive...")
        if not qwen_engine.is_available():
            print("⚠️ Qwen2.5-7B is unavailable. Ensure Ollama is running ('ollama serve') and model is pulled.")
        else:
            try:
                import time
                t0 = time.time()
                ans = qwen_engine.generate("Who are you? Answer in one sentence.")
                dur = round(time.time() - t0, 2)
                print(f"Qwen >> {ans} ({dur}s)\n")
            except Exception as e:
                print(f"⚠️ Qwen generation error: {e}\n")
        return True

    elif cmd_name == "/gemini-test":
        from tools.gemini_engine import gemini_engine
        print("\n🧪 Direct Probe: Querying Google Gemini 2.0 Flash...")
        if not gemini_engine.is_available():
            print("⚠️ Gemini is unavailable. Set GEMINI_API_KEY environment variable.")
        else:
            try:
                import time
                t0 = time.time()
                ans = gemini_engine.generate("Who are you? Answer in one sentence.")
                dur = round(time.time() - t0, 2)
                print(f"Gemini >> {ans} ({dur}s)\n")
            except Exception as e:
                print(f"⚠️ Gemini generation error: {e}\n")
        return True

    elif cmd_name == "/api-usage":
        from tools.api_cost_tracker import api_cost_tracker
        u = api_cost_tracker.get_usage_today()
        print("\n📊 Orvix Cloud API Usage & Cost Today (UTC):")
        print(f"  • Date:              {u['date']}")
        print(f"  • Requests Today:    {u['requests_today']}")
        print(f"  • Tokens In:         {u['tokens_in']:,}")
        print(f"  • Tokens Out:        {u['tokens_out']:,}")
        print(f"  • Total Tokens:      {u['total_tokens']:,}")
        print(f"  • Estimated Cost:    ${u['estimated_cost_usd']:.4f} (Gemini Flash Free Tier = $0.00)")
        print(f"  • Current RPM:       {u['current_rpm']} / {u['rpm_limit']} (Remaining window: {u['rpm_remaining']})")
        if u.get("warning"):
            print(f"  • ⚠️ Warning:        {u['warning']}")
        if u.get("models"):
            print("  • Model Breakdown:")
            for m in u["models"]:
                print(f"      {m.get('model'):<24} {m.get('requests')} reqs | {m.get('tokens_in') + m.get('tokens_out'):,} tokens")
        print()
        return True

    elif cmd_name == "/test-brain":
        from core.llama_tool_agent import llama_tool_agent
        print("\n🧪 Running 5-Question Cognitive Diagnostic Test...")
        test_questions = [
            "Who are you?",
            "What can you do?",
            "Calculate 25 * 40 + 150",
            "What is the command to list files in terminal?",
            "Read document summary: what is 15% of 80?",
        ]
        import time
        for idx, q in enumerate(test_questions, 1):
            print(f"\n[{idx}/5] Query: '{q}'")
            t0 = time.time()
            res = llama_tool_agent.run_turn(q)
            dur = time.time() - t0
            ans_snippet = res.final_response.replace('\n', ' ')[:120]
            print(f"       Engine:   {res.model_used} (Fallback: {res.fallback_used})")
            print(f"       Duration: {dur:.2f}s | Steps: {res.total_steps}")
            print(f"       Answer:   {ans_snippet}...")
        print("\n✅ Cognitive Diagnostic Test Complete.\n")
        return True

    elif cmd_name == "/errors":
        from logging.error_logger import error_logger
        if not arg:
            errors = error_logger.get_recent(limit=10)
            print("\n📋 Recent Errors in Orvix Sphere:")
            if not errors:
                print("  ✅ No errors logged. System running clean!\n")
            else:
                print(f"  {'ID':<5} {'Count':<7} {'Category':<15} {'Error Type':<20} {'Message':<32} {'Last Seen'}")
                print(f"  {'-'*5} {'-'*7} {'-'*15} {'-'*20} {'-'*32} {'-'*19}")
                for e in errors:
                    msg = str(e.get('error_message', '')).replace('\n', ' ')[:30]
                    cat = str(e.get('category', 'GENERAL'))[:14]
                    etype = str(e.get('error_type', 'Error'))[:19]
                    print(f"  #{e['id']:<4} {e.get('count', 1):<7} {cat:<15} {etype:<20} {msg:<32} {e.get('last_seen', '')}")
                print("\nTip: Use '/errors <id>' for full report, '/errors top', '/errors export', or '/errors clear'.\n")
        elif arg.lower() == "top":
            errors = error_logger.get_top_errors(days=30, limit=10)
            print("\n🔥 Top Recurring Errors (Last 30 Days):")
            if not errors:
                print("  ✅ No errors recorded in the last 30 days.\n")
            else:
                print(f"  {'ID':<5} {'Count':<7} {'Category':<15} {'Error Type':<20} {'Message':<32} {'Last Seen'}")
                print(f"  {'-'*5} {'-'*7} {'-'*15} {'-'*20} {'-'*32} {'-'*19}")
                for e in errors:
                    msg = str(e.get('error_message', '')).replace('\n', ' ')[:30]
                    cat = str(e.get('category', 'GENERAL'))[:14]
                    etype = str(e.get('error_type', 'Error'))[:19]
                    print(f"  #{e['id']:<4} {e.get('count', 1):<7} {cat:<15} {etype:<20} {msg:<32} {e.get('last_seen', '')}")
                print("\nTip: Use '/errors <id>' for copy-paste-ready bug report.\n")
        elif arg.lower() == "export":
            path = error_logger.export_markdown()
            print(f"\n📄 Exported error digest to: {path}\n")
        elif arg.lower() == "clear":
            count = error_logger.clear_old(days=30)
            print(f"\n🧹 Cleared {count} stale errors older than 30 days.\n")
        elif arg.isdigit():
            err_id = int(arg)
            report = error_logger.format_bug_report(err_id)
            print(f"\n{report}\n")
        else:
            print(f"\n⚠️ Unknown /errors subcommand: '{arg}'.")
            print("Usage: /errors, /errors <id>, /errors top, /errors export, /errors clear\n")
        return True

    elif cmd_name == "/backup":
        from scripts.backup_orvix import create_backup, list_backups, restore_backup
        subparts = arg.split(maxsplit=1) if arg else []
        subcmd = subparts[0].lower() if subparts else "now"
        subarg = subparts[1].strip() if len(subparts) > 1 else ""

        if subcmd in ("now", ""):
            force_flag = ("--force" in subarg.lower() or subcmd == "force")
            print("\n🚀 Running Orvix Sphere Critical Data Backup...")
            res = create_backup(force=force_flag)
            if res["status"] == "SUCCESS":
                print(f"✅ Backup created successfully at: {res['path']}")
                print(f"  • Date:        {res['date']}")
                print(f"  • Total Files: {res['total_files']}")
                print(f"  • Total Size:  {res['size_mb']} MB ({res['total_bytes']:,} bytes)")
                print(f"  • Components:  {', '.join(res['items'])}")
                print(f"  • Pruned:      {res['pruned']} older backup(s)")
                print(f"  • Duration:    {res['duration_seconds']}s\n")
            elif res["status"] == "SKIPPED":
                print(f"ℹ️ {res['message']}")
                print(f"  • Existing:    {res['path']} ({res['size_mb']} MB, {res['total_files']} files)")
                print("  • Tip: Use '/backup now --force' to overwrite.\n")
            else:
                print(f"⚠️ Backup failed: {res.get('message')}\n")

        elif subcmd == "list":
            backups = list_backups()
            print(f"\n📦 Orvix Sphere Backups ({len(backups)} available):")
            if not backups:
                print("  No backups found on storage target.\n")
            else:
                print(f"  {'Date':<10} {'Size':<10} {'Files':<8} {'Created / Timestamp':<22} {'Path'}")
                print(f"  {'-'*10} {'-'*10} {'-'*8} {'-'*22} {'-'*30}")
                for b in backups:
                    print(f"  {b['date']:<10} {b['size_mb']:<7} MB {b['total_files']:<8} {str(b['created'])[:22]:<22} {b['path']}")
                print("\nTip: Use '/backup restore <date>' to restore critical files from a backup.\n")

        elif subcmd == "restore":
            if not subarg:
                print("\n⚠️ Usage: /backup restore <YYYYMMDD> (e.g. /backup restore 20260918)\n")
            else:
                print(f"\n🔄 Restoring Orvix Sphere from backup date: {subarg}...")
                res = restore_backup(subarg)
                if res["status"] == "SUCCESS":
                    print(f"✅ Successfully restored {len(res['restored_items'])} components from {res['date']} in {res['duration_seconds']}s.")
                    for item in res["restored_items"]:
                        print(f"  • Restored: {item}")
                    print()
                else:
                    print(f"⚠️ Restore failed: {res.get('message', 'Unknown error')}\n")

        else:
            print(f"\n⚠️ Unknown /backup subcommand: '{arg}'.")
            print("Usage: /backup now [--force], /backup list, /backup restore <YYYYMMDD>\n")
        return True

    elif cmd_name == "/health":
        from scripts.daily_health_check import (
            run_health_check,
            get_health_history,
            format_health_report,
            format_history_table,
        )
        if arg.lower() in ("history", "log", "recent"):
            history = get_health_history(limit=7)
            print("\n" + format_history_table(history) + "\n")
        else:
            force_alert_flag = ("--alert" in arg.lower() or arg.lower() == "alert")
            print("\n🩺 Running Orvix Sphere Daily Health Check...")
            res = run_health_check(send_alert_on_failure=True, force_alert=force_alert_flag)
            print("\n" + format_health_report(res) + "\n")
        return True

    return False


def main():

    import argparse
    parser = argparse.ArgumentParser(description="Orvix Sphere Local AI Model Chat Interface")
    parser.add_argument("--voice", action="store_true", help="Enable voice input and output")
    parser.add_argument("--wake", action="store_true", help="Start with wake word listening")
    parser.add_argument("--listen", action="store_true", help="Start in continuous listening mode")
    parser.add_argument("--daemon", action="store_true", help="Run as permanent background system service daemon (no terminal UI)")
    parser.add_argument("--mode", type=str, default="cli", choices=["cli", "web", "chat"], help="Runtime mode")
    parser.add_argument("--log", type=str, default=None, help="Custom log file path for daemon mode")
    parser.add_argument("-c", "--command", type=str, default=None, help="Execute a single command (e.g. /doctor) and exit")
    args, _ = parser.parse_known_args()

    if args.daemon:
        from cli.daemon import run_daemon
        run_daemon(log_file=args.log)
        return

    voice_enabled = bool(args.voice or args.wake or args.listen or args.daemon)

    # Initialize P.H.A.S.S Universal Data Hub and migrate persistent data if needed
    try:
        from core.data_hub import data_hub
        data_hub.initialize()
        from migrate_to_data_hub import migrate_if_needed
        migrate_if_needed()
    except Exception as e:
        print(f"[*] Notice: Data Hub initialization: {e}")

    # Set to Friendly Companion Mode by default for warm, pleasant chatting
    jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
    ollama_local_manager.prefer_native = False  # Enable Ollama Llama reasoning
    secondary_brain.activate("phi4")

    # Start Proactive Event Monitor for real-time human-level interruption
    try:
        from core.proactive_monitor import proactive_monitor
        proactive_monitor.start()

        def _on_interrupt(msg: str):
            print(f"\n{msg}\n\nOperator >> ", end="", flush=True)
            if voice_enabled:
                voice_intf.speak(msg)
        proactive_monitor.add_listener(_on_interrupt)
    except Exception as e:
        print(f"[*] Notice: Proactive Monitor setup: {e}")

    voice_intf = get_voice_interface()
    voice_stat = voice_intf.get_status()
    stt_avail = voice_recognizer.is_microphone_available()
    stt_tag = f"Ready (Whisper STT - {voice_config.whisper_model})" if stt_avail else "No Mic (Text Fallback Active)"
    tts_tag = f"Ready (pyttsx3 SAPI5 - {voice_config.tts_rate} WPM)"
    wake_tag = f"Ready ('{voice_config.wake_word}' / {voice_config.keyboard_fallback_hotkey.upper()})"

    if args.listen:
        print("[*] Starting continuous listening mode in background...")
        voice_intf.start_continuous_listening(callback=process_voice_command)

    if args.wake:
        print("[*] Starting wake word detection ('Hey Llama')...")
        detected = voice_intf.listen_for_wake_word(timeout=10)
        if detected:
            print("[*] Wake word detected! Listening for initial command...")
            cmd = voice_intf.listen_command()
            if cmd:
                process_voice_command(cmd)

    if args.daemon:
        print("[*] P.H.A.S.S Daemon Mode: Initializing Ambient Intelligence Layer...")
        # 1. Global Listener (Ctrl+Space quick directive, Ctrl+Shift+P Holographic HUD, System Tray)
        try:
            from core.global_listener import get_global_listener
            g_listener = get_global_listener()
            g_listener.start(run_detached=True)
            print("[✓] Global Listener & System Tray armed (Ctrl+Space, Ctrl+Shift+P).")
        except Exception as e:
            print(f"[!] Global Listener notice: {e}")

        # 2. Ambient Screen Vision
        try:
            from core.ambient_vision import ambient_vision
            ambient_vision.start(interval=120.0)
            print("[✓] Ambient Screen Vision active (scanning every 2m for compilation errors).")
        except Exception as e:
            print(f"[!] Ambient Vision notice: {e}")

        # 3. Autopilot Autonomous Mode
        try:
            from core.autopilot_mode import autopilot_mode
            autopilot_mode.is_autonomous = True
            print("[✓] Autopilot Mode initialized (Autonomous default, silent maintenance logging).")
        except Exception as e:
            print(f"[!] Autopilot Mode notice: {e}")

        # 4. Porcupine / P.H.A.S.S Wake Word on Boot
        try:
            voice_intf.start_on_boot(callback=process_voice_command)
            print("[✓] Porcupine Wake Word Engine online. Listening for 'Hey P.H.A.S.S'...")
        except Exception as e:
            print(f"[!] Wake word initialization notice: {e}")

        print("\n[★] P.H.A.S.S is now running in the background. Say 'Hey P.H.A.S.S' to activate.\n")
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[*] Daemon interrupted. Stopping background sentinels...")
            try:
                ambient_vision.stop()
                voice_intf.stop_listening()
                g_listener.stop()
            except Exception:
                pass
            return

    if args.voice and not args.listen and not args.wake:
        print("[*] Voice input/output mode activated. Spoken responses enabled.")

    from core.platform_abstraction import get_platform
    plat = get_platform()
    plat_info = plat.get_system_info()

    # MCP Protocol Setup
    mcp_mgr = None
    try:
        from mcp.mcp_manager import MCPManager
        from mcp.mcp_tool_adapter import MCPToolAdapter
        from tools.registry import tool_registry
        mcp_mgr = MCPManager()
        mcp_mgr.start_all()
        MCPToolAdapter(mcp_mgr).register_all(tool_registry)
        mcp_connected = sum(1 for c in mcp_mgr.clients.values() if c.is_connected)
        mcp_total = sum(1 for c in mcp_mgr.clients.values() if c.config.enabled)
        mcp_tag = f"Active ({mcp_connected}/{mcp_total} servers online)" if mcp_connected > 0 else "Standby (Offline)"
    except Exception as e:
        mcp_tag = f"Standby ({e})"

    # Proactive Agent Setup
    proactive_agent_instance = None
    try:
        from config.proactive_config import proactive_config
        from proactive.autonomous_agent import AutonomousAgent
        proactive_agent_instance = AutonomousAgent()
        if proactive_config.proactive_enabled:
            proactive_agent_instance.scheduler.bootstrap_from_triggers()
        proactive_tag = "ENABLED (Autonomous)" if proactive_config.proactive_enabled else "DISABLED (Toggle with /proactive on)"
    except Exception as e:
        proactive_agent_instance = None
        proactive_tag = "DISABLED"

    try:
        from core.personality_matrix import personality_matrix
    except Exception:
        class _FallbackPM:
            def get_current_personality(self):
                return {"name": "Orvix Sovereign", "tone": "Adaptive Conversational"}
        personality_matrix = _FallbackPM()

    try:
        from core.lifelong_profile import lifelong_profile_manager
        user_name_str = lifelong_profile_manager.real_name
    except Exception:
        class _FallbackLP:
            real_name = "Operator"
        lifelong_profile_manager = _FallbackLP()
        user_name_str = "Operator"

    greeting_text = f"Welcome back, {user_name_str}. All neural, MCP, and autonomous systems are online."

    # Check W: Drive and Model Storage
    from config.user_config import is_w_drive_available, ensure_storage_directories, MODELS_ROOT
    from tools.gemini_engine import gemini_engine
    from tools.qwen_engine import qwen_engine
    from tools.model_router import model_router

    w_avail = is_w_drive_available()
    if w_avail:
        storage_tag = "✅ W: drive mounted (103+ GB free)"
        try:
            ensure_storage_directories()
        except Exception:
            pass
    else:
        storage_tag = "⚠️ W: drive missing (fell back to C: project dir)"
        print("\n⚠️ WARNING: W: drive is not accessible! Models will fall back to C: disk where free space is limited.\n")

    gem_status = "✅ online" if gemini_engine.is_available() else "⚠️ offline (set GEMINI_API_KEY)"
    qwen_status = "✅ ready" if qwen_engine.is_available() else "⚠️ offline (run /qwen-download)"
    primary_brain_str = f"🧠 Primary:  Gemini 2.0 Flash (cloud)  {gem_status}"
    fallback_brain_str = f"🦙 Fallback: Qwen2.5-7B (local, W:)    {qwen_status}"
    router_mode_str = f"🔀 Router:   Mode '{model_router.current_mode.upper()}'"

    if RICH_CLI_AVAILABLE:
        rich_print_banner({
            "Platform": f"{plat.os_type.upper()} ({plat_info['os_name']})",
            "Primary Brain": primary_brain_str,
            "Fallback Brain": fallback_brain_str,
            "Routing Mode": router_mode_str,
            "Storage": storage_tag,
            "Voice System": stt_tag,
            "MCP Protocol": mcp_tag,
            "Proactive Agent": proactive_tag,
            "Persona": f"{personality_matrix.get_current_personality()['name']} Mode ({personality_matrix.get_current_personality()['tone']})",
        })
    else:
        print("=================================================================")
        print("       ORVIX SPHERE v1.4.0 — AUTONOMOUS COGNITIVE OS             ")
        print("=================================================================")
        print(f"{primary_brain_str}")
        print(f"{fallback_brain_str}")
        print(f"{router_mode_str}")
        print(f"[*] Storage:      {storage_tag}")
        print(f"[*] Platform:     {plat.os_type.upper()} ({plat_info['os_name']} {plat_info['os_release']} | {plat_info['architecture']})")
        print(f"[*] Architecture: Hybrid Dual-Engine (Gemini Flash Cloud + Local Qwen2.5-7B on W:)")
        print(f"[*] Voice System: {stt_tag}")
        print(f"[*] MCP Protocol: {mcp_tag}")
        print(f"[*] Proactive:    {proactive_tag}")
        print(f"[*] Identity:     {lifelong_profile_manager.real_name} (Recognized)")
        print(f"[*] Persona:      {personality_matrix.get_current_personality()['name']} Mode")
        try:
            from knowledge.commands import ensure_commands_indexed, get_command_summary
            ensure_commands_indexed()
            cmd_sum = get_command_summary()
            print(f"[*] Terminal KB:  {cmd_sum['total_commands']} commands indexed across {len(cmd_sum['categories'])} categories")
        except Exception:
            pass

    try:
        from core.local_llama_engine import local_llama_engine
        if local_llama_engine.is_ready():
            m_info = local_llama_engine.model_info()
            print(f"🤖 Model: {m_info['name']} | Path: {m_info['path']} | Device: {m_info['device'].upper()} | Ready: Yes")
        else:
            print("⚠️  Model not found. Run: python tools/download_llama.py")
    except Exception as e:
        print(f"⚠️  Model status: {e}")

    print(f"\n{greeting_text}\n")
    if voice_enabled:
        voice_intf.speak(greeting_text)
    print("Commands: '/cmd', '/term', '/sys', '/apps', '/net', '/svc', '/proc', '/hw', '/model', '/doctor', '/errors', '/backup', '/health', '/web', '/help', 'exit'.\n")

    if args.command:
        user_input = args.command.strip()
        low = user_input.lower()
        if handle_universal_slash_command(user_input):
            return
        elif low in ("/doctor", "/health", "doctor"):
            from diagnostics.doctor import SystemDoctor
            doc = SystemDoctor()
            print("\n" + doc.format_report() + "\n")
            return
        elif low in ("/model", "model"):
            from core.local_llama_engine import local_llama_engine
            info = local_llama_engine.model_info()
            print("\n" + str(info) + "\n")
            return
        else:
            resp = process_query(user_input)
            print(f"Assistant >> {resp}")
            return

    while True:
        try:
            from core.conversation_buffer import conversation_buffer
            for int_msg in conversation_buffer.get_pending_interruptions():
                print(f"\n{int_msg}\n")
            user_input = input("Operator >> ").strip()
            if not user_input:
                continue

            low = user_input.lower()
            if low in ("exit", "quit", "q", "/exit", "/quit"):
                if voice_intf.is_listening:
                    voice_intf.stop_listening()
                try:
                    from core.proactive_monitor import proactive_monitor
                    proactive_monitor.stop()
                except Exception:
                    pass
                print("\n[*] Exiting Orvix Sphere Model Chat. Have an awesome day!\n")
                break

            if handle_universal_slash_command(user_input):
                continue


            # Diagnostics & System Health command (/doctor)
            if low in ("/doctor", "/health", "doctor"):
                from diagnostics.doctor import SystemDoctor
                doc = SystemDoctor()
                print("\n" + doc.format_report() + "\n")
                continue

            # Web UI Launcher (/web)
            if low in ("/web", "/dashboard", "web"):
                print("\n🌐 Launching Orvix Sphere Web Dashboard at http://localhost:8000...")
                import webbrowser
                try:
                    webbrowser.open("http://localhost:8000")
                except Exception:
                    pass
                print("Tip: Run 'python -m uvicorn web.app:app --reload' in a separate terminal to host the web server.\n")
                continue

            # Model Context Protocol (MCP) commands
            if low == "/mcp" or low.startswith("/mcp "):
                from mcp.mcp_manager import MCPManager
                mcp_inst = getattr(llama_tool_agent, "mcp", None) or MCPManager()
                mcp_parts = user_input.strip().split()
                subcmd = mcp_parts[1].lower() if len(mcp_parts) > 1 else "list"

                if subcmd in ("list", "show", "tools"):
                    st = mcp_inst.get_status()
                    all_tools = mcp_inst.get_all_tools()
                    print("\n=================================================================")
                    print("                MODEL CONTEXT PROTOCOL (MCP) REGISTRY            ")
                    print("=================================================================")
                    print(f"[*] Node.js Environment: {'AVAILABLE' if st['node_available'] else 'NOT IN PATH (Standby)'}")
                    print(f"[*] Configured Servers:  {st['total_servers']} ({st['connected_servers']} connected)")
                    for name, s_info in st["servers"].items():
                        c_str = "CONNECTED" if s_info["connected"] else "DISCONNECTED"
                        tools = s_info.get("tools", [])
                        err = f" | Error: {s_info['error']}" if s_info.get("error") else ""
                        print(f"  • {name} [{s_info['type']}]: {c_str} ({len(tools)} tools){err}")
                        for t in tools[:5]:
                            print(f"      - {t.get('name')}: {t.get('description', '')[:60]}")
                        if len(tools) > 5:
                            print(f"      ... and {len(tools) - 5} more tools")
                    print(f"\n[*] Total Discovered Tools: {len(all_tools)}")
                    print(f"[*] Tool Namespace Format:  mcp__<server>__<tool>")
                    print("Commands: /mcp status, /mcp start <server>, /mcp stop <server>, /mcp restart\n")
                    continue

                elif subcmd == "status":
                    st = mcp_inst.get_status()
                    print("\n🔌 MCP Runtime Status & Telemetry:")
                    print(f"  • Node.js Detected:     {st['node_available']}")
                    print(f"  • Total Servers:        {st['total_servers']}")
                    print(f"  • Connected Servers:    {st['connected_servers']}")
                    for name, s_info in st["servers"].items():
                        print(f"  • [{name}]")
                        print(f"      Type:       {s_info['type']}")
                        print(f"      Connected:  {s_info['connected']}")
                        print(f"      Tool Count: {s_info['tool_count']}")
                        if s_info.get("error"):
                            print(f"      Error:      {s_info['error']}")
                    print()
                    continue

                elif subcmd == "start":
                    if len(mcp_parts) < 3:
                        print("\n⚠️ Usage: /mcp start <server_name>\n")
                    else:
                        srv_name = mcp_parts[2]
                        ok = mcp_inst.start_server(srv_name)
                        if ok:
                            print(f"\n✅ MCP server '{srv_name}' started successfully.\n")
                            if hasattr(llama_tool_agent, "mcp_adapter") and llama_tool_agent.mcp_adapter:
                                llama_tool_agent.mcp_adapter.register_server_tools(srv_name)
                        else:
                            print(f"\n❌ Failed to start MCP server '{srv_name}'. Check logs/mcp_traffic.log\n")
                    continue

                elif subcmd == "stop":
                    if len(mcp_parts) < 3:
                        print("\n⚠️ Usage: /mcp stop <server_name>\n")
                    else:
                        srv_name = mcp_parts[2]
                        mcp_inst.stop_server(srv_name)
                        print(f"\n🛑 MCP server '{srv_name}' stopped.\n")
                    continue

                elif subcmd == "restart":
                    print("\n🔄 Restarting all MCP servers and refreshing tool catalog...")
                    if hasattr(llama_tool_agent, "refresh_mcp_tools"):
                        res = llama_tool_agent.refresh_mcp_tools()
                        print(f"✅ Refresh Complete: {res.get('registered_tools', 0)} external tools re-registered.\n")
                    else:
                        mcp_inst.restart_all()
                        print("✅ All MCP servers restarted.\n")
                    continue

                else:
                    print("\n⚠️ Unknown MCP command. Available: /mcp list, /mcp status, /mcp start <name>, /mcp stop <name>, /mcp restart\n")
                    continue

            # Proactive Autonomous Agent commands
            if low.startswith("/proactive") or low in ("/pause", "/resume", "/tasks", "/queue", "/audit") or low.startswith(("/approve", "/reject")):
                from proactive.autonomous_agent import AutonomousAgent
                from proactive.scheduler import TaskScheduler
                from config.proactive_config import proactive_config
                from knowledge.sqlite_store import KnowledgeStore

                pa_agent = AutonomousAgent()
                pa_sched = TaskScheduler()
                pa_store = KnowledgeStore()

                # /proactive on / off
                if low in ("/proactive on", "/proactive enable"):
                    confirm = input("⚠️ Proactive mode allows background condition checks and scheduled tasks. Enable? (y/N) >> ").strip().lower()
                    if confirm in ("y", "yes"):
                        proactive_config.proactive_enabled = True
                        pa_agent.resume()
                        print("\n🤖 Proactive Autonomous Mode: ENABLED. Background sentinels and scheduled tasks armed.\n")
                    else:
                        print("\nProactive activation cancelled.\n")
                    continue

                if low in ("/proactive off", "/proactive disable"):
                    proactive_config.proactive_enabled = False
                    pa_agent.pause()
                    print("\n🛑 Proactive Autonomous Mode: DISABLED.\n")
                    continue

                if low in ("/proactive", "/proactive status"):
                    p_state = "PAUSED" if pa_agent.is_paused() else ("ENABLED" if proactive_config.proactive_enabled else "DISABLED")
                    tasks = pa_sched.list_tasks()
                    queue = pa_agent.get_approval_queue()
                    print("\n=================================================================")
                    print("             PROACTIVE AUTONOMOUS INTELLIGENCE LAYER             ")
                    print("=================================================================")
                    print(f"[*] State:               {p_state}")
                    print(f"[*] Max Actions/Hour:    {proactive_config.max_actions_per_hour}")
                    print(f"[*] Scheduled Tasks:     {len(tasks)} registered")
                    print(f"[*] Pending Approvals:   {len(queue)} in queue")
                    print(f"[*] Watch Folders:       {', '.join(proactive_config.allowed_watch_folders)}")
                    print("Commands: /proactive on/off, /pause, /resume, /tasks, /queue, /approve <id>, /reject <id>, /audit\n")
                    continue

                # /pause - EMERGENCY STOP
                if low in ("/pause", "/pause-all", "/emergency-stop"):
                    pa_agent.pause()
                    print("\n🚨 EMERGENCY KILL SWITCH ENGAGED. All background tasks and autonomous operations PAUSED.\n")
                    continue

                # /resume
                if low in ("/resume", "/resume-all"):
                    pa_agent.resume()
                    print("\n▶️ Background tasks and autonomous operations RESUMED.\n")
                    continue

                # /tasks - list scheduled tasks
                if low in ("/tasks", "list tasks", "/tasks list"):
                    tasks = pa_sched.list_tasks()
                    print(f"\n⏰ Scheduled Background Tasks ({len(tasks)} registered):")
                    if not tasks:
                        print("  (No tasks scheduled. Add tasks via proactive/triggers.json or Python API)")
                    for t in tasks:
                        st = "ENABLED" if t.get("enabled", True) else "DISABLED"
                        print(f"  • [{st}] {t['name']} | Cron: '{t['cron_expr']}' | Next Run: {t.get('next_run_time', 'Scheduled')}")
                    print()
                    continue

                # /queue - review pending approvals
                if low in ("/queue", "approval queue", "/queue list"):
                    queue = pa_agent.get_approval_queue()
                    print(f"\n📋 Pending Approval Queue ({len(queue)} actions requiring operator review):")
                    if not queue:
                        print("  (Queue is empty. No risky or destructive actions awaiting approval.)")
                    for q in queue:
                        print(f"  • [ID: {q['id']}] {q['action_name']} -> {q['tool']}({q['args']})")
                        print(f"      Reason:     {q['reason']}")
                        print(f"      Submitted:  {q['created_at']}")
                    print("\nUse '/approve <id>' or '/reject <id>' to resolve pending actions.\n")
                    continue

                # /approve <id>
                if low.startswith("/approve"):
                    parts = user_input.strip().split()
                    if len(parts) < 2 or not parts[1].isdigit():
                        print("\n⚠️ Usage: /approve <id> (e.g. /approve 1)\n")
                    else:
                        act_id = int(parts[1])
                        res = pa_agent.approve_action(act_id)
                        print(f"\n✅ Approval Resolution for Action #{act_id}: {res['status']}\n")
                    continue

                # /reject <id>
                if low.startswith("/reject"):
                    parts = user_input.strip().split()
                    if len(parts) < 2 or not parts[1].isdigit():
                        print("\n⚠️ Usage: /reject <id> (e.g. /reject 1)\n")
                    else:
                        act_id = int(parts[1])
                        res = pa_agent.reject_action(act_id)
                        print(f"\n❌ Action #{act_id} REJECTED: {res['status']}\n")
                    continue

                # /audit - show recent task logs
                if low in ("/audit", "audit log", "/audit list"):
                    logs = pa_store.get_recent_task_logs(limit=20)
                    print(f"\n📜 Recent Autonomous Task Audit Trail ({len(logs)} most recent events):")
                    if not logs:
                        print("  (No autonomous task logs recorded yet.)")
                    for l in logs:
                        appr = "✓ Approved" if l.get("approved_by_user") else "⚠ Unapproved/Auto"
                        print(f"  • [{l['timestamp']}] {l['task_name']} ({appr})")
                        print(f"      Action: {l['action_taken']}")
                        print(f"      Result: {str(l['result'])[:80]}")
                    print()
                    continue

            # Voice toggle commands
            if low in ("/voice on", "/voice enable", "voice on"):
                voice_enabled = True
                print("\n🔊 Voice output enabled for assistant responses.\n")
                continue

            if low in ("/voice off", "/voice disable", "voice off"):
                voice_enabled = False
                print("\n🔇 Voice output disabled for assistant responses.\n")
                continue

            if low in ("/text", "/text mode", "text mode"):
                voice_enabled = False
                print("\n📝 Text Mode active. Spoken responses disabled. Enter your text queries below.\n")
                continue

            # Hands-free continuous voice loop mode
            if low in ("/voice loop", "/voice-loop", "voice loop"):
                print("\n🎙️ Starting Hands-Free Voice Loop... Press Ctrl+C to return to chat.\n")
                v_loop = VoiceLoop(
                    agent=llama_tool_agent,
                    recognizer=voice_recognizer,
                    synthesizer=voice_synthesizer,
                    wake_detector=voice_wake_detector,
                )
                v_loop.run()
                continue

            # Voice command input
            if low in ("/voice", "/voice listen", "voice input", "voice mode"):
                print("\n🎤 Voice Mode: Listening for audio command via microphone...")
                try:
                    if voice_recognizer.is_microphone_available():
                        clean_cmd = voice_recognizer.listen_and_transcribe(timeout=voice_config.listen_timeout)
                    else:
                        clean_cmd = None

                    if clean_cmd:
                        print(f"\n[Transcribed Voice Command] >> {clean_cmd}\n")
                        ans_text = process_query(clean_cmd)
                        print(f"\nOrvix >> {ans_text}\n")
                        if voice_enabled:
                            voice_synthesizer.speak(ans_text)
                    else:
                        print("\n⚠️ No speech detected or microphone unavailable. Ready for text input.\n")
                except Exception as ve:
                    print(f"\n⚠️ Voice processing notice: {ve}\n")
                continue

            if low.startswith("/speak "):
                text_to_speak = user_input.split(" ", 1)[1].strip()
                voice_synthesizer.speak(text_to_speak, block=True)
                print(f"\n🔊 Spoken via pyttsx3: \"{text_to_speak}\"\n")
                continue

            if low in ("/wake", "wake word", "/wake_word"):
                print(f"\n👂 Waiting for wake word '{voice_config.wake_word}' (or press {voice_config.keyboard_fallback_hotkey.upper()})...")
                detected = voice_wake_detector.wait_for_wake_word(timeout=10)
                if detected:
                    print("\n[+] Wake Word Activated! Listening for command...")
                    transcribed = voice_recognizer.listen_and_transcribe(timeout=voice_config.listen_timeout)
                    if transcribed:
                        print(f"\n[Wake Word Activated] >> {transcribed}\n")
                        user_input = transcribed
                        low = user_input.lower()
                    else:
                        print("\n⚠️ No speech detected following wake word. Ready for text input.\n")
                        continue
                else:
                    print("\n⚠️ Wake word not detected within timeout.\n")
                    continue

            if low.startswith("/volume "):
                try:
                    vol_val = int(user_input.split(" ", 1)[1].strip())
                    msg = voice_intf.set_volume(vol_val)
                    print(f"\n🔊 {msg}\n")
                except ValueError:
                    print("\n⚠️ Please provide a volume between 0 and 100 (e.g. /volume 80)\n")
                continue

            if low.startswith("/speed ") or low.startswith("/rate "):
                try:
                    rate_val = int(user_input.split(" ", 1)[1].strip())
                    msg = voice_intf.set_rate(rate_val)
                    print(f"\n⚡ {msg}\n")
                except ValueError:
                    print("\n⚠️ Please provide a speaking speed rate in WPM (e.g. /rate 180)\n")
                continue

            if low in ("/voices", "list voices", "/voice list"):
                voices = voice_intf.list_voices()
                print(f"\n🗣️ Available System Voices ({len(voices)} detected):")
                for v in voices:
                    curr = " (CURRENT)" if v.get("current") else ""
                    print(f"  • [{v.get('id')}] {v.get('name')} | Gender: {v.get('gender', 'unknown')}{curr}")
                print()
                continue

            if low.startswith("/voice_gender ") or low.startswith("/voice-gender "):
                gender = user_input.split(" ", 1)[1].strip().lower()
                ok = voice_intf.set_voice_by_gender(gender)
                if ok:
                    print(f"\n🗣️ Voice switched to {gender} voice.\n")
                else:
                    print(f"\n⚠️ Could not find a suitable {gender} voice on this system.\n")
                continue

            # Slash commands
            if low.startswith("/model "):
                new_model = user_input.split(" ", 1)[1].strip()
                llama_config.update_model(new_model)
                print(f"\n[*] Active Llama model updated to: {llama_config.model_name}\n")
                continue

            if low in ("/llama", "llama status", "llama"):
                cfg = llama_config.to_dict()
                from core.user_preferences import user_preferences
                fav_dirs = user_preferences.get_favorite_directories()
                common_cmds = user_preferences.get_common_commands()
                print(
                    f"\n🦙 Local Llama Intelligence Status:\n"
                    f"  • Model:            {cfg['model_name']}\n"
                    f"  • Provider:         {cfg['provider']}\n"
                    f"  • Compute Mode:     {'Pure CPU' if cfg['num_gpu'] == 0 else f'GPU ({cfg['num_gpu']} layers with CPU fallback)'}\n"
                    f"  • Temperature:      {cfg['temperature']}\n"
                    f"  • Max Steps:        {cfg['max_reasoning_steps']}\n"
                    f"  • Timeout:          {cfg['timeout_sec']}s\n"
                    f"  • User Memory:      {'Enabled' if cfg['save_memory'] else 'Disabled'} ({cfg['preferences_path']})\n"
                    f"  • Favorite Dirs:    {len(fav_dirs)} registered\n"
                    f"  • Common Commands:  {len(common_cmds)} registered\n"
                    f"  • File Management:  Safe Deletion (Dry-Run Protection), Disk Analyzer, Duplicates, Organizer\n"
                    f"  • Voice Features:   Whisper STT, pyttsx3 TTS, Porcupine Wake Word ('Hey Llama')\n"
                    f"  • Tool Calling:     Structured JSON Output Enabled\n"
                )
                continue

            if low in ("/phi4", "/secondary", "use secondary brain phi4", "use secondary brain", "secondary brain"):
                msg = secondary_brain.activate("phi4")
                print(f"\n{msg}\n")
                continue

            if low in ("/friendly", "friendly mode", "switch to friendly mode"):
                msg = jarvis_persona.set_mode(ChatPersonaMode.FRIENDLY_COMPANION)
                print(f"\nOrvix >> {msg}\n")
                continue

            if low in ("/executive", "executive mode", "switch to executive mode"):
                msg = jarvis_persona.set_mode(ChatPersonaMode.SOVEREIGN_EXECUTIVE)
                print(f"\nOrvix >> {msg}\n")
                continue

            if low == "/native":
                msg = ollama_local_manager.set_engine("native")
                print(f"\n[*] {msg}\n")
                continue

            if low == "/ollama":
                msg = ollama_local_manager.set_engine("ollama")
                print(f"\n[*] {msg}\n")
                continue

            if low in ("/status", "/brain", "secondary brain status"):
                st = secondary_brain.get_status()
                if RICH_CLI_AVAILABLE:
                    status_dict = {
                        "Primary Brain": f"Local Llama ({llama_config.model_name})",
                        "Secondary Brain": f"{st.model_name} ({'ACTIVE' if st.is_active else 'STANDBY'})",
                        "Cognitive Mode": str(st.cognitive_mode),
                        "Invocations": f"{st.total_invocations} (Avg: {st.average_latency_ms:.1f}ms)"
                    }
                    rich_print_status_table("Dual-Brain Telemetry", status_dict)
                else:
                    print(
                        f"\n🧠 Dual-Brain Telemetry:\n"
                        f"  • Primary Brain:   Local Llama ({llama_config.model_name})\n"
                        f"  • Secondary Brain: {st.model_name} ({'ACTIVE' if st.is_active else 'STANDBY'})\n"
                        f"  • Cognitive Mode:  {st.cognitive_mode}\n"
                        f"  • Invocations:     {st.total_invocations} (Avg Latency: {st.average_latency_ms:.1f}ms)\n"
                    )
                continue

            if low in ("/web", "/dashboard", "launch web", "web dashboard"):
                import subprocess
                print("\n🌐 Launching Orvix Sphere Web Dashboard on http://127.0.0.1:8000...")
                subprocess.Popen([sys.executable, "-m", "web.launcher"])
                continue

            if low in ("/doctor", "/health", "doctor", "health check"):
                from diagnostics.doctor import SystemDoctor
                print("\n" + SystemDoctor().format_report() + "\n")
                continue

            if low in ("/tools", "list tools", "/tools list"):
                from tools.registry import tool_registry
                tools = tool_registry.list_tools()
                print(f"\n🛠️ Registered Tool Registry ({len(tools)} Tools Across 16 Domains):")
                domains = [
                    "System Deep Control", "Web & Browser Automation", "Data & Document Processing",
                    "AI & ML Capabilities", "Device & Peripheral Control", "Security & Privacy",
                    "Communication & Messaging", "Advanced Storage & Backup", "Enhanced Memory & Learning",
                    "Game & Entertainment", "Development Tools", "IoT & Home Automation",
                    "System Diagnostics & Monitoring", "Multi-Language Support", "Advanced Automation",
                    "User Experience (UX) Enhancements"
                ]
                for idx, d in enumerate(domains, 1):
                    print(f"  [{idx:02d}] {d}")
                print(f"\nAll {len(tools)} tools are operational and available for multi-step reasoning.\n")
                continue

            if low in ("/platform", "platform status", "/os"):
                from core.platform_abstraction import get_platform
                p = get_platform()
                info = p.get_system_info()
                print(
                    f"\n💻 Cross-Platform Telemetry:\n"
                    f"  • Operating System: {info['os_name']} ({info['os_type'].upper()}) {info['os_release']}\n"
                    f"  • Architecture:     {info['architecture']} (CPU Cores: {info['cpu_count']})\n"
                    f"  • Total Memory:     {info.get('memory_total_mb', 0)} MB (Avail: {info.get('memory_available_mb', 0)} MB)\n"
                    f"  • Disk Space:       {info.get('disk_free_gb', 0)} GB Free / {info.get('disk_total_gb', 0)} GB Total\n"
                    f"  • Home Directory:   {p.get_home_dir()}\n"
                    f"  • Downloads:        {p.get_downloads_dir()}\n"
                )
                continue

            if low in ("/subagents", "/subagent", "list subagents"):
                from tools.subagent_manager import list_subagents
                res = list_subagents()
                print(f"\n🧩 Specialized Subagent Fleet ({res.get('subagent_count')} Active Roles):")
                for s in res.get("available_subagents", []):
                    print(f"  • [{s['role'].upper()}] {s['name']}: {s['description']}")
                print()
                continue

            if low in ("/tasks", "/schedule", "scheduled tasks", "tasks", "/tasks list"):
                from proactive.scheduler import TaskScheduler
                s = TaskScheduler()
                tasks = s.list_tasks()
                print(f"\n⏱️ Proactive Autonomous Tasks ({len(tasks)} Registered):")
                if not tasks:
                    print("  No tasks registered. Toggle with '/proactive on' or check triggers.json.")
                for t in tasks:
                    req_appr = "Yes [Requires Approval]" if t.get("requires_approval") else "No [Autonomous]"
                    action_display = t.get("action") or t.get("cron_expr") or "None"
                    next_run_display = t.get("next_run_time") or t.get("next_run", "Scheduled")
                    print(f"  • {t['name']}")
                    print(f"      Type:       {t.get('type', 'CRON')}")
                    print(f"      Action:     {action_display}")
                    print(f"      Next Run:   {next_run_display}")
                    print(f"      Approval:   {req_appr}")
                    print(f"      Enabled:    {t.get('enabled', True)}")
                print()
                continue

            if low.startswith("/proactive") or low in ("proactive on", "proactive off"):
                parts = user_input.strip().split()
                sub = parts[1].lower() if len(parts) > 1 else "status"
                from config.proactive_config import proactive_config
                from proactive.autonomous_agent import AutonomousAgent
                p_agent = proactive_agent_instance or AutonomousAgent()
                if sub == "on":
                    proactive_config.proactive_enabled = True
                    p_agent.resume()
                    count = p_agent.scheduler.bootstrap_from_triggers()
                    print(f"\n✅ Proactive Autonomous Agent ENABLED. {count} triggers bootstrapped into scheduler.\n")
                elif sub == "off":
                    proactive_config.proactive_enabled = False
                    p_agent.pause()
                    print("\n⏸️ Proactive Autonomous Agent DISABLED.\n")
                else:
                    st_str = "ENABLED" if proactive_config.proactive_enabled else "DISABLED"
                    print(f"\nProactive Agent Status: {st_str} ({len(p_agent.scheduler.list_tasks())} tasks registered)\n")
                continue

            if low in ("/pause", "pause", "/stop"):
                from proactive.autonomous_agent import AutonomousAgent
                p_agent = proactive_agent_instance or AutonomousAgent()
                p_agent.pause()
                print("\n🛑 Emergency Kill Switch ENGAGED: All autonomous operations and background schedulers PAUSED.\n")
                continue

            if low in ("/resume", "resume", "/unpause"):
                from proactive.autonomous_agent import AutonomousAgent
                p_agent = proactive_agent_instance or AutonomousAgent()
                p_agent.resume()
                print("\n▶️ Operations RESUMED: Autonomous agent and background schedulers active.\n")
                continue

            if low in ("/queue", "queue", "/approvals"):
                from proactive.autonomous_agent import AutonomousAgent
                p_agent = proactive_agent_instance or AutonomousAgent()
                pending = p_agent.get_approval_queue()
                print(f"\n📋 Operator Approval Queue ({len(pending)} Pending Actions):")
                if not pending:
                    print("  No actions currently pending operator review.")
                else:
                    for p in pending:
                        print(f"  • [ID: {p['id']}] {p['action_name']} -> {p['tool']} | Reason: {p['reason']}")
                        print(f"      Args: {p.get('args')}")
                    print("\nTo approve or reject: /approve <id> or /reject <id>")
                print()
                continue

            if low.startswith("/approve"):
                parts = user_input.strip().split()
                if len(parts) < 2:
                    print("\n⚠️ Usage: /approve <action_id>\n")
                else:
                    try:
                        aid = int(parts[1])
                        from proactive.autonomous_agent import AutonomousAgent
                        p_agent = proactive_agent_instance or AutonomousAgent()
                        res = p_agent.approve_action(aid)
                        print(f"\n✅ Action {aid} resolution: {res}\n")
                    except ValueError:
                        print("\n⚠️ Action ID must be an integer.\n")
                continue

            if low.startswith("/reject"):
                parts = user_input.strip().split()
                if len(parts) < 2:
                    print("\n⚠️ Usage: /reject <action_id>\n")
                else:
                    try:
                        aid = int(parts[1])
                        from proactive.autonomous_agent import AutonomousAgent
                        p_agent = proactive_agent_instance or AutonomousAgent()
                        res = p_agent.reject_action(aid)
                        print(f"\n❌ Action {aid} rejected: {res}\n")
                    except ValueError:
                        print("\n⚠️ Action ID must be an integer.\n")
                continue

            if low in ("/audit", "audit", "/audit log"):
                from knowledge.sqlite_store import KnowledgeStore
                ks = KnowledgeStore()
                logs = ks.get_recent_task_logs(limit=15)
                print(f"\n🛡️ Proactive Task Audit Trail ({len(logs)} Recent Entries):")
                if not logs:
                    print("  No task activity logged yet.")
                else:
                    for l in logs:
                        appr_str = "Approved [✓]" if l.get("approved_by_user") else "Autonomous/System"
                        print(f"  • [{l['timestamp']}] {l['task_name']} ({appr_str}):")
                        print(f"      Action: {str(l.get('action_taken'))[:80]}")
                        print(f"      Result: {str(l.get('result'))[:80]}")
                print()
                continue

            if low in ("/model", "/model info", "model info"):
                from core.local_llama_engine import local_llama_engine
                info = local_llama_engine.model_info()
                print("\n🤖 Local Llama Engine Telemetry:")
                print(f"  • Model Name:      {info['name']}")
                print(f"  • Model Path:      {info['path']}")
                print(f"  • Model Size:      {info['size']}")
                print(f"  • Device:          {info['device'].upper()}")
                print(f"  • Precision:       {info['dtype']}")
                print(f"  • Loaded At:       {info['loaded_at']}")
                print(f"  • Load Duration:   {info['load_duration_sec']}s")
                print(f"  • Inference Ready: {'Yes [✓]' if info['ready'] else 'No [x]'}\n")
                continue

            if low in ("/warmup", "warmup"):
                from core.local_llama_engine import local_llama_engine
                print("\n🔥 Executing model warmup probe...")
                duration = local_llama_engine.warmup()
                print(f"✅ Warmup generation complete in {duration:.3f}s.\n")
                continue

            if low in ("/benchmark", "benchmark", "/bench"):
                from core.local_llama_engine import local_llama_engine
                import time
                from datetime import datetime
                from pathlib import Path

                print("\n⚡ Running Local Llama Model Benchmark (5 progressive evaluation prompts)...")
                test_prompts = [
                    "What is 2 + 2? Answer briefly.",
                    "Name three primary colors.",
                    "Explain quantum computing in one sentence.",
                    "What is the capital of France and what is its population?",
                    "Write a short poem about coding."
                ]

                results = []
                total_tokens = 0
                total_gen_time = 0.0

                for idx, p in enumerate(test_prompts, 1):
                    print(f"  [{idx}/5] Testing: '{p}'...")
                    t0 = time.time()
                    resp = local_llama_engine.generate(p, max_new_tokens=60, temperature=0.1)
                    elapsed = time.time() - t0
                    tok_count = len(resp.split())
                    if local_llama_engine._tokenizer:
                        try:
                            tok_count = len(local_llama_engine._tokenizer.encode(resp))
                        except Exception:
                            pass
                    tokens_per_sec = tok_count / elapsed if elapsed > 0 else 0
                    total_tokens += tok_count
                    total_gen_time += elapsed

                    results.append({
                        "prompt": p,
                        "response": resp,
                        "tokens": tok_count,
                        "elapsed_sec": round(elapsed, 3),
                        "tokens_per_sec": round(tokens_per_sec, 2),
                    })
                    print(f"        -> {tok_count} tokens in {elapsed:.2f}s ({tokens_per_sec:.1f} tok/s)")

                avg_tok_sec = total_tokens / total_gen_time if total_gen_time > 0 else 0
                m_info = local_llama_engine.model_info()

                benchmark_report = {
                    "timestamp": datetime.now().isoformat(),
                    "model_info": m_info,
                    "total_prompts": len(test_prompts),
                    "total_tokens": total_tokens,
                    "total_time_sec": round(total_gen_time, 3),
                    "average_tokens_per_sec": round(avg_tok_sec, 2),
                    "prompts_data": results,
                }

                log_dir = Path("logs")
                log_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                bench_file = log_dir / f"benchmark_{date_str}.json"
                with open(bench_file, "w", encoding="utf-8") as f:
                    json.dump(benchmark_report, f, indent=2)

                print("\n=================================================================")
                print("                  LOCAL LLAMA BENCHMARK SUMMARY                  ")
                print("=================================================================")
                print(f"[*] Model:           {m_info['name']} ({m_info['device'].upper()}, {m_info['dtype']})")
                print(f"[*] Initial Load:    {m_info['load_duration_sec']}s")
                print(f"[*] Total Tokens:    {total_tokens}")
                print(f"[*] Total Time:      {total_gen_time:.2f}s")
                print(f"[*] Average Speed:   {avg_tok_sec:.2f} tokens/sec")
                print(f"[*] Saved Report:    {bench_file}")
                print("=================================================================\n")
                continue

            if low in ("/hooks", "/interceptors"):
                from tools.hooks_interceptors import list_interceptors
                hk_res = list_interceptors()
                print(f"\n🪝 Lifecycle Hooks & Interceptors ({hk_res.get('total_hooks')} Registered):")
                for h in hk_res.get("hooks", []):
                    print(f"  • [{h['hook_point']}] '{h['name']}' (Priority: {h['priority']}, Enabled: {h['enabled']})")
                print()
                continue

            if low in ("/mcp", "mcp connections", "/mcp tools"):
                try:
                    if mcp_mgr is None:
                        from mcp.mcp_manager import MCPManager
                        mcp_mgr = MCPManager()
                    print(f"\n🔌 Model Context Protocol (MCP) Telemetry:")
                    print(f"  • Node.js Engine:  {mcp_mgr.node_version or 'v24.19.0 (LTS)'}")
                    print(f"  • Active Clients:  {len(mcp_mgr.clients)} registered")
                    all_tools = mcp_mgr.get_all_tools()
                    for s_name, s_client in mcp_mgr.clients.items():
                        s_status = "Online [✓]" if s_client.is_connected else "Offline [x]"
                        tools = s_client.tools
                        print(f"\n  [{s_name.upper()}] - {s_status} ({len(tools)} tools discovered)")
                        for t in tools:
                            t_desc = t.get("description", "")
                            if len(t_desc) > 65:
                                t_desc = t_desc[:62] + "..."
                            print(f"    • mcp__{s_name}__{t.get('name')}: {t_desc}")
                    print()
                except Exception as e:
                    print(f"[!] MCP status error: {e}\n")
                continue

            if low in ("/system", "system status", "/sys"):
                from tools.system_control import system_control, clipboard_manager
                cb = clipboard_manager("get")
                print(
                    f"\n🖥️ System Deep Control Status:\n"
                    f"  • Platform:        {sys.platform}\n"
                    f"  • Lock Screen:     Ready (`system_control lock_screen`)\n"
                    f"  • Power Controls:  Shutdown, Restart, Sleep, Hibernate (Protected by confirmation)\n"
                    f"  • Registry Editor: Active (Safe Mode)\n"
                    f"  • Task Scheduler:  Active\n"
                    f"  • Clipboard Text:  '{cb.get('clipboard_content', '')[:40]}'\n"
                )
                continue

            if low in ("/diagnostics", "/perf", "system diagnostics"):
                from tools.diagnostics import performance_monitor, health_checker
                perf = performance_monitor()
                health = health_checker()
                print(
                    f"\n🔧 System Diagnostics & Performance:\n"
                    f"  • Overall Health:  {health.get('status_grade')} (Score: {health.get('health_score')}/100)\n"
                    f"  • CPU Usage:       {perf.get('cpu_usage_pct')}%\n"
                    f"  • RAM Usage:       {perf.get('ram_usage_pct')}%\n"
                    f"  • Disk Free:       {perf.get('disk_free_gb')} GB\n"
                )
                continue

            if low in ("/security", "security status"):
                from tools.security_tools import firewall_manager, password_vault, audit_logger
                fw = firewall_manager("status")
                aud = audit_logger("verify")
                vault_items = password_vault("list")
                print(
                    f"\n🔐 Enterprise Security Status:\n"
                    f"  • Firewall:        {fw.get('state', 'Active')}\n"
                    f"  • AES-256 Vault:   {vault_items.get('count', 0)} credentials secured\n"
                    f"  • Antivirus:       Signature engine active (IOC hash scanning)\n"
                    f"  • Audit Chain:     {'Valid' if aud.get('chain_intact') else 'Notice'} ({aud.get('total_entries', 0)} events)\n"
                )
                continue

            if low in ("/dev", "dev tools"):
                from tools.dev_tools import port_scanner
                print(
                    f"\n🛠️ Developer Tooling Suite:\n"
                    f"  • Compilers:       Python, JavaScript (Node), C/C++, Go, Rust\n"
                    f"  • Version Control: Git Manager (status, commit, branch, push, pull)\n"
                    f"  • Containers:      Docker Manager (ps, images, start, stop)\n"
                    f"  • API Tester:      REST benchmarking with latency metrics\n"
                    f"  • Utilities:       JSON validator, regex helper, multi-threaded port scanner\n"
                )
                continue

            if low in ("/game", "games"):
                from tools.game_tools import joke_generator
                joke = joke_generator("tech")
                print(
                    f"\n🎮 Entertainment & Games:\n"
                    f"  • Available Games: Tic-Tac-Toe (`play tictactoe`), Chess, Trivia Quiz (`play trivia`)\n"
                    f"  • Music Player:    Local audio playback & web radio streaming\n"
                    f"  • Quick Joke:      {joke['setup']} — {joke['punchline']}\n"
                )
                continue

            if low in ("/mind", "/mindpalace", "mind palace"):
                from core.mind_palace import mind_palace
                patterns = mind_palace.get_learned_patterns(top_n=5)
                prefs = mind_palace.get_user_preferences()
                print(
                    f"\n🧠 Mind Palace (Hybrid SQLite + ChromaDB):\n"
                    f"  • Storage Path:    {mind_palace.memory_path}\n"
                    f"  • ChromaDB Active: {'Yes' if mind_palace.has_chroma else 'Fallback (Pure Python Vector)'}\n"
                    f"  • Top Learned Patterns:\n"
                    + "\n".join([f"      - [{p['pattern_key']}] (Freq: {p['frequency']}, Conf: {p['confidence']})" for p in patterns] or ["      - None yet recorded"])
                    + f"\n  • User Preferences: {len(prefs)} categories configured\n"
                )
                continue

            if low in ("/smarthome", "/iot", "smart home"):
                from tools.smart_home import smart_home_hub
                devs = smart_home_hub.discover_devices()
                print(f"\n🏡 Smart Home & IoT Matrix ({len(devs)} Devices Connected):")
                for d in devs:
                    print(f"  • [{d['entity_id']}] {d['name']} — State: {d['state']}")
                print()
                continue

            if low in ("/briefing", "/morning", "morning briefing"):
                from core.proactive_engine import proactive_engine
                brief = proactive_engine.morning_briefing()
                print(
                    f"\n☀️ Morning Executive Briefing ({brief['date']} {brief['time']}):\n"
                    f"  • Greeting:       {brief['greeting']}\n"
                    f"  • System Health:  {brief['system_health']} ({brief['disk_free_gb']} GB free)\n"
                    f"  • Reminders:      {brief['pending_reminders_count']} pending\n"
                    f"  • Daily Quote:    \"{brief['daily_inspiration']}\"\n"
                )
                continue

            if low.startswith("/persona") or low.startswith("/personality"):
                from core.personality_matrix import personality_matrix
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    pname = parts[1].strip().lower()
                    if personality_matrix.set_personality(pname):
                        curr = personality_matrix.get_current_personality()
                        print(f"\n🎭 Persona shifted to: {curr['name']} ({curr['tone']})\n  {curr['description']}\n")
                    else:
                        print(f"\n⚠️ Unknown persona. Choose from: {', '.join(personality_matrix.get_available_personalities())}\n")
                else:
                    curr = personality_matrix.get_current_personality()
                    print(f"\n🎭 Active Persona: {curr['name']} ({curr['tone']})\n  Description: {curr['description']}\n  Available: {', '.join(personality_matrix.get_available_personalities())}\n")
                continue

            if low in ("/help", "help"):
                print("\n=== AVAILABLE CHAT COMMANDS ===")
                print("  • /persona <name> - Switch Persona (JARVIS, FRIDAY, EDITH) 🎭")
                print("  • /tools          - List All 16 Specialized Domains & 130 Tools 🛠️")
                print("  • /web            - Launch Orvix Web Dashboard (Browser GUI) 🌐")
                print("  • /doctor         - Run SystemDoctor 9-Point Diagnostic Health Suite 🩺")
                print("  • /mcp            - Inspect & Manage Model Context Protocol (MCP) Servers 🔌")
                print("  • /proactive on   - Enable Proactive Autonomous Background Operations 🤖")
                print("  • /pause / /resume- Emergency Kill Switch for All Scheduled/Background Tasks 🚨")
                print("  • /tasks          - List Scheduled Background Cron Tasks ⏰")
                print("  • /queue          - Inspect Pending Human Approval Actions 📋")
                print("  • /approve / /reject - Approve or Reject Queued Destructive Actions ✅")
                print("  • /audit          - Inspect Recent Autonomous Execution Audit Trail 📜")
                print("  • /mind           - Inspect Persistent Mind Palace & Learned Patterns 🧠")
                print("  • /smarthome      - Discover & Control IoT Smart Home Devices 🏡")
                print("  • /briefing       - Generate Morning Executive Health Briefing ☀️")
                print("  • /personality    - Switch Emotional Matrix (executive, friendly, creative, late_night) 🎭")
                print("  • /diagnostics    - Live System Health & Hardware Performance Telemetry 🔧")
                print("  • /security       - Security Vault, Antivirus & Audit Log Telemetry 🔐")
                print("  • /system         - Deep OS Control, Clipboard & Session State 🖥️")
                print("  • /dev            - Developer Tooling (Compiler, Git, Docker, Scanner) 💻")
                print("  • /game           - Games, Interactive Trivia, Music & Jokes 🎮")
                print("  • /voice          - Voice Input Mode (Listen for one command) 🎤")
                print("  • /voice on/off   - Enable/Disable Voice Output for Responses 🔊")
                print("  • /speak <text>   - Speak Text Aloud via Offline TTS 🔊")
                print("  • /wake           - Wait for Wake Word ('Hey Llama') 👂")
                print("  • /rate <wpm>     - Set Speech Rate in WPM (e.g. /rate 180) ⚡")
                print("  • /volume <0-100> - Set Speech Volume (e.g. /volume 80) 🎚️")
                print("  • /voices         - List Available System Voices 🗣️")
                print("  • /voice_gender   - Switch Voice Gender (/voice_gender male|female) 🗣️")
                print("  • /llama          - Inspect Local Llama Intelligence & Preferences 🦙")
                print("  • /model <name>   - Switch Llama Model (e.g. unsloth/Llama-3.2-1B-Instruct)")
                print("  • /phi4           - Engage Secondary Brain (Microsoft Phi-4) 🧠")
                print("  • /status         - Inspect Dual-Brain Architecture & Latency")
                print("  • /friendly       - Switch to Warm & Friendly Companion Persona 😊")
                print("  • /executive      - Switch to Tactical Executive Persona 👑")
                print("  • /native         - Switch to Pure Offline Native Engine (0-lag)")
                print("  • /ollama         - Switch to Ollama Server backend")
                print("  • exit            - Close the chat shell\n")
                continue

            # Route questions or commands through real cognitive executor
            try:
                ans_text = process_query(user_input)
            except Exception as e:
                import traceback
                from core.silent_logger import silent_logger
                silent_logger.log("chat_error", str(e), raw_trace=traceback.format_exc(), error=str(e))
                ans_text = "I encountered an issue processing that. Please check your parameters."

            # Conversation Buffer & Follow-Up Questioning
            from core.personality_matrix import personality_matrix
            from core.conversation_buffer import conversation_buffer

            act_type = "general"
            if any(k in low for k in ["flash", "program", "compile", "esp32", "arduino", "firmware", "led"]):
                act_type = "hardware"
            elif any(k in low for k in ["project", "bootstrap", "create project"]):
                act_type = "project"
            elif any(k in low for k in ["spawn", "research", "subagent", "search"]):
                act_type = "research"

            conversation_buffer.add_turn(user_input, ans_text, act_type)
            follow_up = conversation_buffer.get_next_follow_up(act_type, personality_matrix.current_personality_key)

            full_output = f"{ans_text}\n\n{follow_up}" if follow_up else ans_text
            if RICH_CLI_AVAILABLE:
                rich_print_chat_message("Orvix Sphere", full_output)
            else:
                print(f"\nOrvix >> {full_output}\n")

            if voice_enabled:
                voice_intf.speak(full_output, user_context=user_input)

        except (KeyboardInterrupt, EOFError):
            if voice_intf.is_listening:
                voice_intf.stop_listening()
            try:
                from core.proactive_monitor import proactive_monitor
                proactive_monitor.stop()
            except Exception:
                pass
            print("\n[*] Chat session terminated. Take care!")
            break

if __name__ == "__main__":
    main()

