"""
Multimeter & Oscilloscope Measurement Interpreter for P.H.A.S.S Hardware Co-Pilot.
Parses benchtop electrical measurements and diagnoses physical circuit state,
fault conditions, and semiconductor operating points.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional


class MeasurementInterpreter:
    """
    Parses multimeter and scope readings and applies semiconductor physics rules.
    """

    def parse_readings(self, text: str) -> Dict[str, float]:
        """
        Extracts numerical readings from strings like:
        "Vcc = 5V, Vbe = 0.2V, Ic = 100mA" -> {'vcc': 5.0, 'vbe': 0.2, 'ic_ma': 100.0}
        """
        readings: Dict[str, float] = {}

        # Patterns for voltages: Vcc, Vbe, Vce, Vgs, Vds, Vin, Vout, Vd, etc.
        volt_matches = re.findall(
            r"\b(vcc|vbe|vce|vgs|vds|vin|vout|vref|v_drop|vbat)\s*[:=]\s*([0-9\.\-]+)\s*(?:v|volts?)?\b",
            text,
            re.IGNORECASE,
        )
        for key, val in volt_matches:
            try:
                readings[key.lower()] = float(val)
            except ValueError:
                pass

        # Patterns for currents: Ic, Ib, Id, Iout, Iin in mA or A
        curr_matches = re.findall(
            r"\b(ic|ib|id|iout|iin|is)\s*[:=]\s*([0-9\.\-]+)\s*(ma|ua|a|amps?|milliamps?)?\b",
            text,
            re.IGNORECASE,
        )
        for key, val, unit in curr_matches:
            try:
                numeric_val = float(val)
                u = unit.lower() if unit else "a"
                if "ma" in u or "milli" in u:
                    current_amp = numeric_val / 1000.0
                    current_ma = numeric_val
                elif "ua" in u or "micro" in u:
                    current_amp = numeric_val / 1e6
                    current_ma = numeric_val / 1000.0
                else:
                    current_amp = numeric_val
                    current_ma = numeric_val * 1000.0
                readings[f"{key.lower()}_ma"] = current_ma
                readings[f"{key.lower()}_a"] = current_amp
            except ValueError:
                pass

        # Patterns for resistances: R1, R2, Rb, Rc, Rd, Rs
        res_matches = re.findall(
            r"\b(r1|r2|rb|rc|rd|rs|rload)\s*[:=]\s*([0-9\.\-]+)\s*(k|kohm|kiloohm|m|meg|ohm|ohms?)?\b",
            text,
            re.IGNORECASE,
        )
        for key, val, unit in res_matches:
            try:
                num = float(val)
                u = unit.lower() if unit else ""
                if "k" in u:
                    ohms = num * 1000.0
                elif "m" in u or "meg" in u:
                    ohms = num * 1e6
                else:
                    ohms = num
                readings[key.lower()] = ohms
            except ValueError:
                pass

        return readings

    def interpret_readings(self, measurement_text: str) -> Dict[str, Any]:
        """
        Analyzes measured readings against physical circuit principles and generates diagnoses.
        """
        readings = self.parse_readings(measurement_text)
        diagnoses: List[str] = []
        warnings: List[str] = []

        vcc = readings.get("vcc")
        vbe = readings.get("vbe")
        vce = readings.get("vce")
        vgs = readings.get("vgs")
        vds = readings.get("vds")
        vin = readings.get("vin")
        vout = readings.get("vout")
        ic_ma = readings.get("ic_ma")

        # 1. BJT Transistor Base-Emitter Analysis
        if vbe is not None:
            if vbe < 0.5:
                warnings.append(
                    f"Warning: Vbe is too low ({vbe}V, should be ~0.7V). Your transistor is either dead, in cutoff, "
                    f"or the base resistor is too large. Increase base current or verify driving GPIO logic level."
                )
            elif 0.55 <= vbe <= 0.75:
                diagnoses.append(f"Vbe is normal ({vbe}V): Base-emitter PN junction is properly forward-biased (~0.7V).")
            elif vbe > 0.85:
                warnings.append(
                    f"Warning: Vbe is unusually high ({vbe}V). Silicon B-E junction normally clamps at ~0.65V-0.75V. "
                    f"A reading above 0.85V indicates excessive base current (Rb missing/too small) or damaged junction."
                )

        # 2. BJT Collector-Emitter Saturation vs Cutoff
        if vce is not None:
            if vce <= 0.35:
                diagnoses.append(f"Vce is low ({vce}V): Transistor is in SATURATION (Vce_sat ≈ 0.2V). Acting as an effective closed switch.")
            elif vcc is not None and vce >= (vcc * 0.8):
                diagnoses.append(f"Vce is high ({vce}V ≈ Vcc): Transistor is in CUTOFF (open switch). No significant collector current flowing.")
            elif vcc is not None and 0.5 < vce < (vcc * 0.8):
                diagnoses.append(f"Vce is intermediate ({vce}V): Transistor is operating in the ACTIVE LINEAR region. Sinks current with moderate power dissipation.")

        # 3. MOSFET Gate-Source Threshold Analysis
        if vgs is not None:
            if vgs < 1.5:
                warnings.append(
                    f"Warning: Vgs ({vgs}V) is below threshold voltage Vgs(th). The MOSFET channel is not formed and the switch remains OFF."
                )
            elif 1.8 <= vgs < 4.5:
                diagnoses.append(
                    f"Vgs is {vgs}V: Suitable for logic-level MOSFETs (e.g. IRLZ44N, AO3400). Standard MOSFETs (like IRFZ44N) require ~10V for full saturation."
                )
            elif vgs >= 4.5:
                diagnoses.append(f"Vgs is strong ({vgs}V): Gate is well-driven for low R_DS(on) conduction.")

        # 4. Voltage Divider Diagnostics
        if vin is not None and vout is not None:
            if vout == 0 and vin > 0:
                warnings.append("Vout is 0V with active Vin: R2 is shorted to ground, R1 is open, or an external load is clamping output.")
            elif abs(vout - vin) < 0.05 and vin > 0:
                warnings.append("Vout equals Vin: R2 is open-circuit / disconnected from ground, or R1 is shorted.")
            else:
                ratio = vout / vin if vin != 0 else 0
                diagnoses.append(f"Divider transfer ratio: Vout/Vin = {round(ratio, 3)} ({round(ratio*100, 1)}% of input voltage).")

        # Fallback if no specific condition matched
        if not diagnoses and not warnings:
            if readings:
                summary_items = [f"{k.upper()}: {v}" for k, v in readings.items()]
                result_text = f"Parsed Measurements: {', '.join(summary_items)}. Voltages and currents are within typical bounds."
            else:
                result_text = "No recognized voltage (Vcc, Vbe, Vce, Vin, Vout) or current measurements found in text."
        combined = []
        if warnings:
            combined.extend(warnings)
        if diagnoses:
            combined.extend(diagnoses)
        result_text = "\n\n".join(combined)

        return {
            "status": "SUCCESS",
            "parsed_values": readings,
            "warnings": warnings,
            "diagnoses": combined,
            "analysis": result_text,
        }


# Global singleton
measurement_interpreter = MeasurementInterpreter()

