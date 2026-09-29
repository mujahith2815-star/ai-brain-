import os
import json
import shutil
import time
from pathlib import Path
import pytest
import psutil

from core.llama_tool_agent import process_query
from core.execution_orchestrator import execution_orchestrator
from hardware.component_engine import component_engine
from hardware.debug_oracle import debug_oracle
from core.daily_routine import get_daily_routine
from core.mobile_interface import get_mobile_interface
from core.self_improvement import get_self_improvement
from ui.holographic_theme import HOLO_PALETTE, get_hud_font


class TestHolographicHybridEngine:

    def setup_method(self):
        self.desktop_test_proj = Path(os.path.expanduser('~/Desktop/Smart_Sensor'))

    def teardown_method(self):
        if self.desktop_test_proj.exists():
            shutil.rmtree(self.desktop_test_proj, ignore_errors=True)

    # 1. Strict Execution Orchestrator
    def test_module1_execution_orchestrator_pipeline(self):
        test_file = 'checkpoints/module1_test_file.txt'
        plan = {
            'actions': [
                {'tool': 'write_file', 'args': {'file_path': test_file, 'content': 'verified_content'}},
                {'tool': 'advanced_calculator', 'args': {'expression': '100 / 4'}}
            ]
        }
        res = execution_orchestrator.execute_plan(plan)
        assert res['status'] == 'SUCCESS'
        assert res['actions_executed'] == 2
        assert os.path.exists(test_file)
        with open(test_file, 'r', encoding='utf-8') as f:
            assert f.read() == 'verified_content'
        assert '25' in res['summary'] or 'calculated' in res['summary'].lower() or 'successfully executed' in res['summary'].lower()
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_module1_execution_logging(self):
        log_file = Path('checkpoints/execution_log.json')
        assert log_file.exists()
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        assert isinstance(logs, list)
        assert len(logs) > 0
        latest = logs[-1]
        assert 'tool' in latest
        assert 'status' in latest
        assert 'timestamp' in latest

    # 2. Hardware Engineering Co-Pilot
    def test_module2_bc547_pinout_query(self):
        ans = process_query('What is the pinout of the BC547 transistor?')
        ans_lower = ans.lower()
        assert 'bc547' in ans_lower
        assert 'collector' in ans_lower and 'base' in ans_lower and 'emitter' in ans_lower
        assert '1' in ans and '2' in ans and '3' in ans

    def test_module2_led_multimeter_troubleshooting(self):
        ans = process_query('My LED is not turning on, help me debug it')
        ans_lower = ans.lower()
        assert 'vcc' in ans_lower or 'power' in ans_lower
        assert 'polarity' in ans_lower or 'anode' in ans_lower
        assert 'resistor' in ans_lower or 'ohms' in ans_lower
        assert 'forward' in ans_lower or 'drop' in ans_lower or 'multimeter' in ans_lower

    def test_module2_desktop_project_bootstrap(self):
        if self.desktop_test_proj.exists():
            shutil.rmtree(self.desktop_test_proj, ignore_errors=True)

        ans = process_query('Start a new project called Smart_Sensor')
        assert 'smart_sensor' in ans.lower()
        assert 'created successfully' in ans.lower() or 'firmware' in ans.lower()

        assert self.desktop_test_proj.exists()
        assert self.desktop_test_proj.is_dir()
        fw_dir = self.desktop_test_proj / 'firmware'
        hw_dir = self.desktop_test_proj / 'hardware'
        assert fw_dir.exists() and fw_dir.is_dir()
        assert hw_dir.exists() and hw_dir.is_dir()
        assert (fw_dir / 'main.ino').exists()
        assert (hw_dir / 'schematic_notes.md').exists()
        assert (hw_dir / 'BOM.csv').exists()
        assert (self.desktop_test_proj / 'README.md').exists()

    # 3. Holographic HUD Palette & Fonts
    def test_module3_holographic_theme(self):
        assert HOLO_PALETTE['bg'] == '#0a0a1a'
        assert HOLO_PALETTE['border_cyan'] == '#00f0ff'
        assert HOLO_PALETTE['accent_purple'] == '#7b2ffc'
        font_title = get_hud_font('title', 14)
        assert font_title is not None

    # 4. Autonomous Daily Operations
    def test_module4_schedule_daily_backup(self):
        ans = process_query('Schedule a daily backup at 2 AM')
        assert 'schedule confirmed' in ans.lower()
        assert 'daily backup' in ans.lower()

        from tools.scheduler import list_scheduled_tasks
        task_list = list_scheduled_tasks()
        assert task_list['status'] == 'SUCCESS'
        tasks = task_list['scheduled_tasks']
        matching = [t for t in tasks if 'Daily Backup' in t.get('name', '') or '0 2 * * *' in t.get('schedule_expr', '')]
        assert len(matching) > 0
        assert matching[0]['schedule_expr'] == '0 2 * * *'

    def test_module4_morning_briefing_and_inbox(self):
        routine = get_daily_routine()
        briefing = routine.run_morning_briefing()
        assert 'briefing' in briefing
        assert 'Good morning' in briefing['briefing']
        assert 'disk_free_gb' in briefing

        unprocessed = routine.get_unprocessed_emails()
        classified = routine.classify_inbox(unprocessed)
        assert len(classified) > 0
        categories = {c['category'] for c in classified}
        assert 'Urgent' in categories or 'Work' in categories

    # 5. Mobile & Remote Access
    def test_module5_mobile_messaging_and_alerts(self):
        mobile = get_mobile_interface()
        alert_res = mobile.send_emergency_alert('Thermal warning: GPU load high')
        assert alert_res['status'] == 'SUCCESS'
        assert alert_res['enqueued'] is True

        reply = mobile.process_incoming_command('2+2')
        assert '4' in reply

        notifs = mobile.get_pending_notifications()
        assert len(notifs) > 0
        latest_alert = [n for n in notifs if n.get('type') == 'EMERGENCY_ALERT']
        assert len(latest_alert) > 0

    # 6. Self-Improvement & Skills
    def test_module6_skill_compilation_after_3_runs(self):
        engine = get_self_improvement()
        steps = [
            {'tool': 'clean_downloads', 'args': {}},
            {'tool': 'backup_documents', 'args': {}}
        ]
        wf_name = 'daily_maintenance_routine'
        r1 = engine.record_workflow_execution(wf_name, steps)
        r2 = engine.record_workflow_execution(wf_name, steps)
        r3 = engine.record_workflow_execution(wf_name, steps)

        assert r1['status'] == 'RECORDED'
        assert r2['status'] == 'RECORDED'
        assert r3['status'] == 'PROMOTED_TO_SKILL'

        skills_path = Path('checkpoints/skills.json')
        assert skills_path.exists()
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills = json.load(f)
        assert wf_name in skills
        assert len(skills[wf_name]['steps']) == 2

    def test_module6_system_auto_tuning(self):
        engine = get_self_improvement()
        high_load = engine.auto_tune_resources(cpu_percent=92.0, memory_percent=85.0)
        assert high_load['is_overloaded'] is True
        assert high_load['action'] == 'throttled'

        normal_load = engine.auto_tune_resources(cpu_percent=25.0, memory_percent=40.0)
        assert normal_load['is_overloaded'] is False
        assert normal_load['action'] == 'optimized'

    def test_module6_error_correlation(self):
        engine = get_self_improvement()
        diag = engine.correlate_execution_errors()
        assert diag['status'] == 'ANALYZED'
        assert 'total_errors' in diag
        assert 'patterns' in diag
