import os
import shutil
import pytest
from hardware.component_engine import component_engine
from hardware.debug_oracle import debug_oracle
from hardware.vibe_project_bootstrap import vibe_project_bootstrap
from hardware.measurement_interpreter import measurement_interpreter
from core.llama_tool_agent import llama_tool_agent
from tools.builtin_tools import tool_registry


def test_datasheet_fetch_bc547():
    """Verify datasheet fetch for BC547 returns correct European pinout (C=1, B=2, E=3)."""
    spec = component_engine.get_component_spec("BC547")
    assert spec is not None
    assert spec.name == "BC547"
    assert spec.package == "TO-92"
    assert "NPN" in spec.type_category
    assert spec.pinout["1"] == "Collector (C)"
    assert spec.pinout["2"] == "Base (B)"
    assert spec.pinout["3"] == "Emitter (E)"
    assert spec.pinout["C"] == "1"
    assert spec.pinout["B"] == "2"
    assert spec.pinout["E"] == "3"
    assert "V_CEO" in spec.key_specs
    assert "h_FE" in spec.key_specs


def test_datasheet_fetch_2n2222():
    """Verify 2N2222 has US TO-92 pinout (E=1, B=2, C=3) and warning."""
    spec = component_engine.get_component_spec("2N2222")
    assert spec is not None
    assert spec.pinout["1"] == "Emitter (E)"
    assert spec.pinout["2"] == "Base (B)"
    assert spec.pinout["3"] == "Collector (C)"


def test_voltage_divider():
    """Verify voltage divider calculator: R1=10, R2=10, Vin=5 -> Vout=2.5V."""
    calc = debug_oracle.calculate_voltage_divider(r1_ohms=10.0, r2_ohms=10.0, vin_volts=5.0)
    assert calc["vout_volts"] == 2.5
    assert calc["formula"] == "Vout = Vin * (R2 / (R1 + R2))"
    assert calc["current_amps"] == pytest.approx(0.25)


def test_rc_time_constant():
    """Verify RC time constant calculator: R=1000, C=1uF -> tau = 1ms."""
    rc = debug_oracle.calculate_rc_time_constant(resistance_ohms=1000.0, capacitance_farads=0.000001)
    assert rc["tau_seconds"] == pytest.approx(0.001)
    assert rc["tau_ms"] == pytest.approx(1.0)


def test_project_structure_led_blink(tmp_path):
    """Verify bootstrap creates dual firmware/ and hardware/ directories and notes."""
    proj_name = "LED_Blink_Test"
    base_dir = str(tmp_path)
    res = vibe_project_bootstrap.bootstrap_project(proj_name, base_dir=base_dir)
    assert res["status"] == "SUCCESS"
    proj_dir = res["project_dir"]

    firmware_dir = os.path.join(proj_dir, "firmware")
    hardware_dir = os.path.join(proj_dir, "hardware")

    assert os.path.isdir(firmware_dir)
    assert os.path.isdir(hardware_dir)
    assert os.path.isfile(os.path.join(hardware_dir, "schematic_notes.md"))
    assert os.path.isfile(os.path.join(hardware_dir, "BOM.csv"))
    assert os.path.isfile(os.path.join(proj_dir, "README.md"))
    assert os.path.isfile(os.path.join(firmware_dir, "main.ino"))
    assert os.path.isfile(os.path.join(firmware_dir, "main.py"))


def test_atmega328_pinout():
    """Verify ATmega328 pinout diagram is generated and includes power/GND pins."""
    diagram = component_engine.get_pinout_diagram("ATmega328")
    assert diagram is not None
    assert "ATmega328P" in diagram or "ATmega328" in diagram
    assert "VCC" in diagram
    assert "GND" in diagram
    assert "PB0" in diagram or "Pin 1" in diagram


def test_ir_sensor_debug():
    """Verify IR sensor troubleshooting contains physical diagnostic steps."""
    res = debug_oracle.troubleshoot_circuit("My IR sensor isn't detecting anything")
    assert "summary" in res
    assert len(res["steps"]) >= 4
    all_text = " ".join(res["steps"])
    assert "VCC" in all_text or "voltage" in all_text.lower()
    assert "multimeter" in all_text.lower() or "potentiometer" in all_text.lower()


def test_measurement_interpreter_vbe_fault():
    """Verify measurement interpreter detects Vbe too low (0.2V instead of ~0.7V)."""
    analysis = measurement_interpreter.interpret_readings("Vcc = 5V, Vbe = 0.2V, Ic = 100mA")
    assert len(analysis["diagnoses"]) > 0
    all_diag = " ".join(analysis["diagnoses"])
    assert "Vbe is too low" in all_diag
    assert "0.2V" in all_diag


def test_bootstrap_drone_esc():
    """Verify Drone_ESC project can be bootstrapped in projects/."""
    res = vibe_project_bootstrap.bootstrap_project("Drone_ESC_UnitTest")
    assert res["status"] == "SUCCESS"
    proj_dir = res["project_dir"]
    try:
        assert os.path.exists(os.path.join(proj_dir, "firmware"))
        assert os.path.exists(os.path.join(proj_dir, "hardware"))
    finally:
        # cleanup
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir, ignore_errors=True)


def test_llama_agent_pinout_query():
    """Verify live query for ATmega328 pinout via llama_tool_agent."""
    resp = llama_tool_agent.process_query("What is the pinout of the ATmega328?")
    assert "ATmega328" in resp
    assert "VCC" in resp
    assert "GND" in resp


def test_llama_agent_ir_sensor_debug_query():
    """Verify live query for IR sensor debugging via llama_tool_agent."""
    resp = llama_tool_agent.process_query("My IR sensor isn't detecting anything. Help me debug it.")
    assert "Physical Diagnostic" in resp or "IR Obstacle" in resp or "Step 1" in resp
    assert "voltage" in resp.lower() or "vcc" in resp.lower() or "potentiometer" in resp.lower()


def test_llama_agent_start_project_query():
    """Verify live query for starting a project called Drone_ESC via llama_tool_agent."""
    resp = llama_tool_agent.process_query("Start a project called Drone_ESC")
    assert "Drone_ESC" in resp
    assert "firmware/" in resp and "hardware/" in resp
    assert os.path.isdir("projects/Drone_ESC/firmware")
    assert os.path.isdir("projects/Drone_ESC/hardware")
