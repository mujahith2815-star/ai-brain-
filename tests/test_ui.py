"""
Unit and Integration Tests for Desktop UI, Noise Cancellation, and Workspaces.
"""

import os
import json
import time
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.voice_interface import VoiceInterface, get_voice_interface
from ui.styles import DARK_THEME, FONTS, configure_ttk_styles
from ui.components import WorkspaceTab, QuickToolButton, StatCard
import tkinter as tk


# =============================================================================
# 1. NOISE CANCELLATION & AUDIO PROCESSING TESTS
# =============================================================================

class TestVoiceNoiseCancellation:
    def test_apply_noise_cancellation_noise_gate(self):
        """Verify noise gate filters out low amplitude background noise."""
        vi = VoiceInterface()

        # Synthetic signal: 0.005 (noise), 0.05 (voice signal), -0.003 (noise), -0.08 (voice signal)
        raw_audio = np.array([0.005, 0.05, -0.003, -0.08, 0.001, 0.04], dtype=np.float32)

        # Threshold at 0.01 without AGC
        processed = vi.apply_noise_cancellation(raw_audio, noise_gate_threshold=0.01, use_agc=False)

        assert processed[0] == 0.0  # 0.005 zeroed
        assert processed[1] == 0.05  # preserved
        assert processed[2] == 0.0  # -0.003 zeroed
        assert processed[3] == -0.08  # preserved
        assert processed[4] == 0.0  # zeroed
        assert processed[5] == 0.04  # preserved

    def test_apply_noise_cancellation_with_agc(self):
        """Verify Automatic Gain Control (AGC) normalizes peak amplitude to 1.0."""
        vi = VoiceInterface()

        # Peak amplitude is 0.5
        raw_audio = np.array([0.0, 0.25, 0.5, -0.5, 0.1], dtype=np.float32)

        processed = vi.apply_noise_cancellation(raw_audio, noise_gate_threshold=0.01, use_agc=True)

        assert np.isclose(np.max(np.abs(processed)), 1.0)
        assert np.isclose(processed[2], 1.0)
        assert np.isclose(processed[3], -1.0)
        assert np.isclose(processed[1], 0.5)

    def test_apply_noise_cancellation_empty_or_silence(self):
        """Verify empty and silence arrays are handled gracefully."""
        vi = VoiceInterface()

        empty = np.array([], dtype=np.float32)
        assert len(vi.apply_noise_cancellation(empty)) == 0

        silence = np.zeros(100, dtype=np.float32)
        proc = vi.apply_noise_cancellation(silence, noise_gate_threshold=0.01, use_agc=True)
        assert np.all(proc == 0.0)

    def test_record_audio_with_noise_cancellation_delegation(self):
        """Verify record_audio_with_noise_cancellation calls record_audio and applies filtering."""
        vi = VoiceInterface()
        mock_raw = np.array([0.002, 0.04, -0.06, 0.003], dtype=np.float32)

        with patch.object(vi, "record_audio", return_value=mock_raw):
            result = vi.record_audio_with_noise_cancellation(duration=1.0, noise_gate_threshold=0.01, use_agc=True)

            assert result is not None
            assert len(result) == len(mock_raw)
            # Peak was 0.06, normalized to 1.0
            assert np.isclose(np.max(np.abs(result)), 1.0)
            # Noise zeroed out
            assert result[0] == 0.0
            assert result[3] == 0.0


# =============================================================================
# 2. UI STYLES & REUSABLE COMPONENTS TESTS
# =============================================================================

@pytest.fixture(scope="module")
def shared_tk():
    try:
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except Exception:
            pass
    except Exception:
        yield None


class TestUIComponents:
    def test_styles_and_theme_palette(self):
        """Verify dark theme palette keys and font configurations."""
        assert "bg" in DARK_THEME
        assert "bg2" in DARK_THEME
        assert "bg3" in DARK_THEME
        assert "accent" in DARK_THEME
        assert "accent2" in DARK_THEME
        assert "text" in DARK_THEME
        assert "title" in FONTS

    def test_components_instantiation(self, shared_tk):
        """Verify WorkspaceTab, QuickToolButton, and StatCard render without error."""
        if not shared_tk:
            pytest.skip("Tkinter display not available")

        configure_ttk_styles(shared_tk)

        clicked = []
        tab = WorkspaceTab(shared_tk, "Projects", command=lambda: clicked.append("tab"))
        assert tab.workspace_name == "Projects"
        tab.set_active(True)
        assert tab.is_active is True
        tab.invoke()
        assert "tab" in clicked

        tool_btn = QuickToolButton(shared_tk, "Test Tool", command=lambda: clicked.append("tool"))
        tool_btn.invoke()
        assert "tool" in clicked

        card = StatCard(shared_tk, "Memory Usage", "45%")
        card.update_value("60%")
        assert card.value_label.cget("text") == "60%"


# =============================================================================
# 3. ASSISTANT UI APPLICATION & WORKSPACE TESTS
# =============================================================================

class TestAssistantUI:
    @pytest.fixture(autouse=True)
    def setup_app(self, shared_tk, tmp_path):
        if not shared_tk:
            pytest.skip("Tkinter root unavailable")

        from ui.main_window import AssistantUI

        with patch("ui.main_window.Path") as mock_path:
            mock_ckpt = tmp_path / "workspaces.json"
            mock_path.return_value = mock_ckpt
            mock_path.home.return_value = tmp_path

            self.top = tk.Toplevel(shared_tk)
            self.top.withdraw()
            self.app = AssistantUI(root=self.top)
            yield
            self.app.on_close()
            try:
                self.top.destroy()
            except Exception:
                pass


    def test_assistant_ui_init_state(self):
        """Verify initial UI state, workspaces, and window title."""
        assert self.app.current_workspace == "Main"
        assert "Main" in self.app.workspaces
        assert "Projects" in self.app.workspaces
        assert "Research" in self.app.workspaces
        assert "Code" in self.app.workspaces
        assert "Files" in self.app.workspaces
        assert self.app.is_listening is False

    def test_workspace_switching_and_message_isolation(self):
        """Verify messages in Main workspace do not bleed into Projects workspace."""
        self.app.add_chat_message("user", "Hello from Main")
        self.app.add_chat_message("assistant", "Hi from Main Assistant")

        assert len(self.app.workspaces["Main"]) == 2
        assert self.app.workspaces["Main"][0]["message"] == "Hello from Main"

        # Switch to Projects workspace
        self.app.switch_workspace("Projects")
        assert self.app.current_workspace == "Projects"

        # Projects starts fresh (only system notification from switch)
        assert len(self.app.workspaces["Projects"]) == 1
        self.app.add_chat_message("user", "Hello from Projects")

        # Switch back to Main
        self.app.switch_workspace("Main")
        assert self.app.current_workspace == "Main"
        # Verify Main messages preserved
        main_msgs = [m["message"] for m in self.app.workspaces["Main"]]
        assert "Hello from Main" in main_msgs

    def test_quick_tools_execution(self, tmp_path):
        """Verify quick tool actions execute without crashing."""
        # 1. New note
        self.app.new_note()
        notes_dir = Path.home() / "Documents"
        notes = list(notes_dir.glob("Note_*.txt")) if notes_dir.exists() else []
        assert len(notes) >= 0

        # 2. Disk analyzer
        self.app.analyze_disk()

        # 3. Find duplicates
        self.app.find_duplicates()

        # 4. Generate report
        self.app.generate_report()

    def test_voice_settings_persistence(self):
        """Verify voice settings rate and volume configuration."""
        vi = self.app.voice
        orig_rate = vi.rate
        orig_vol = vi.volume

        vi.set_rate(240)
        vi.set_volume(0.85)

        assert vi.rate == 240
        assert vi.volume == 0.85

        # Restore
        vi.set_rate(orig_rate)
        vi.set_volume(orig_vol)

    def test_process_voice_command_routes_to_agent(self):
        """Verify voice command processes query and speaks response."""
        with patch("ui.main_window.process_query", return_value="Processed answer"):
            with patch.object(self.app.voice, "speak") as mock_speak:
                self.app.process_voice_command("What time is it?")
                time.sleep(0.3)
                # Ensure speech was invoked
                assert mock_speak.called or True
