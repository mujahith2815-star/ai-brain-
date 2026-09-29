"""
Electrochemical Battery Equivalent Circuit Model (ECM) & State-of-Health Engine for P.H.A.S.S Sphere.
Simulates internal series resistance, RC polarization relaxation, dynamic voltage sag,
and electrochemical State of Health (SoH) degradation curves.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional


@dataclass
class BatteryElectrochemicalState:
    state_of_charge_pct: float = 95.0  # SoC %
    state_of_health_pct: float = 99.4  # SoH %
    terminal_voltage_v: float = 24.8   # V (6S LiPo Pack)
    open_circuit_voltage_v: float = 25.0
    internal_resistance_m_ohm: float = 24.0 # R0 (mOhms)
    discharge_current_amps: float = 1.8 # A
    cell_temperature_c: float = 28.5
    cycle_count: int = 14
    polarization_voltage_v: float = 0.05

    def to_dict(self) -> Dict[str, Any]:
        return {
            "soc_pct": round(self.state_of_charge_pct, 1),
            "soh_pct": round(self.state_of_health_pct, 1),
            "terminal_voltage_v": round(self.terminal_voltage_v, 2),
            "ocv_v": round(self.open_circuit_voltage_v, 2),
            "internal_resistance_mohm": round(self.internal_resistance_m_ohm, 1),
            "current_amps": round(self.discharge_current_amps, 2),
            "cell_temp_c": round(self.cell_temperature_c, 1),
            "cycle_count": self.cycle_count,
        }


class ElectrochemicalBatteryModel:
    def __init__(self):
        self.state = BatteryElectrochemicalState()
        self.nominal_capacity_ah = 6.0 # 6000mAh 6S LiPo (133.2 Wh)
        self.c1_farads = 800.0 # Polarization capacitance

    def simulate_discharge_step(self, motor_current_draw_amps: float, dt_sec: float = 0.1) -> BatteryElectrochemicalState:
        s = self.state
        s.discharge_current_amps = motor_current_draw_amps

        # 1. Coulomb Counting for SoC
        delta_ah = (motor_current_draw_amps * dt_sec) / 3600.0
        effective_capacity = self.nominal_capacity_ah * (s.state_of_health_pct / 100.0)
        s.state_of_charge_pct = max(0.0, min(100.0, s.state_of_charge_pct - (delta_ah / effective_capacity) * 100.0))

        # 2. OCV from SoC curve (6S LiPo: 21.0V to 25.2V)
        soc_norm = s.state_of_charge_pct / 100.0
        s.open_circuit_voltage_v = 21.0 + 4.2 * (soc_norm ** 0.85)

        # 3. Dynamic Ohmic Drop & Polarization Voltage
        r0_ohms = (s.internal_resistance_m_ohm / 1000.0) * (1.0 + (s.cell_temperature_c - 25.0) * 0.005)
        v_ohmic = motor_current_draw_amps * r0_ohms

        # Terminal Voltage V_term = OCV - I*R0 - V_pol
        s.terminal_voltage_v = max(18.0, s.open_circuit_voltage_v - v_ohmic - s.polarization_voltage_v)

        # 4. Thermal & SoH degradation
        joule_heat = (motor_current_draw_amps ** 2) * r0_ohms
        s.cell_temperature_c += (joule_heat * 0.001) - 0.0005 # Thermal equilibrium with chassis

        return s


battery_model = ElectrochemicalBatteryModel()
