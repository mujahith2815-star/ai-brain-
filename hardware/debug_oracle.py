"""
Circuit Debugging & Simulation Oracle for P.H.A.S.S Hardware Co-Pilot.
Provides structured physical troubleshooting workflows ("Path of Solution"),
multimeter test procedures, and lightweight numpy-based circuit simulations.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple


class CircuitDebugOracle:
    """
    Physical troubleshooting oracle and circuit calculator.
    Guides the user through rigorous physical diagnostics instead of software workarounds.
    """

    def troubleshoot_circuit(self, issue: str) -> Dict[str, Any]:
        """
        Produces a strict step-by-step physical diagnostic guide for electronics issues.
        """
        iss_low = issue.lower()

        # 1. Transistor / BJT Circuit Diagnostic
        # 0. LED Diagnostic Workflow (Power, Ground, Resistor, Polarity, Multimeter)
        if any(k in iss_low for k in ["led", "light", "diode", "led not turning on", "led isn't turning on", "led not working"]):
            steps = [
                "Step 1: Check Power (Vcc) with Multimeter: Set multimeter to DC Volts (20V range). Place black probe on system Ground and red probe on the power rail feeding your circuit. Confirm stable Vcc (e.g. +5.0V or +3.3V) is reaching the breadboard or circuit trace.",
                "Step 2: Check Ground (GND) Continuity: Turn circuit power OFF. Switch multimeter to Continuity / Resistance (Ohms) mode. Probe from the LED's cathode connection to the power supply GND. Confirm a clean 0 Ohm continuity beep. A floating ground is the most common reason an LED fails to illuminate.",
                "Step 3: Check Current-Limiting Resistor Value: With power OFF, measure the series resistor with your multimeter on Ohms mode. Confirm it reads between 220 Ohms and 1k Ohms (standard for 5V is 220-330 Ohms, formula: R = (Vcc - V_F) / 0.02A). If the multimeter reads 'OL' (infinite resistance), the resistor is burned open and must be replaced.",
                "Step 4: Verify LED Polarity (Anode vs. Cathode): Inspect the physical LED. The longer lead is the Anode (+) and must face toward Vcc/GPIO. The shorter lead and flat edge on the plastic rim is the Cathode (-) and must face Ground. If installed backward, the diode blocks all current.",
                "Step 5: Measure Diode Forward Voltage Drop (V_F): Power the circuit ON. Place the red probe on the Anode and black probe on the Cathode. A functioning forward-biased LED must drop ~1.8V to 2.2V (Red/Yellow/Green) or ~3.0V to 3.4V (Blue/White). If you measure 0V, current is blocked upstream (check GPIO state); if you measure full Vcc across the LED, the diode is burned out open-circuit.",
            ]
            return {
                "status": "SUCCESS",
                "target": "LED Indicator / Semiconductor Diode",
                "summary": "Physical step-by-step diagnostic workflow for LED not turning on.",
                "steps": steps,
            }

        # 0.5 Strict Physical Diagnostic Sequence for Circuit Not Working
        if any(k in iss_low for k in ["circuit isn't working", "circuit not working", "circuit is not working", "my circuit", "breadboard not working"]):
            steps = [
                "Step 1: Check Power (Vcc): Set multimeter to DC Voltage mode. Measure directly at the power supply rails and at each IC/component Vcc pin. Confirm stable Vcc without voltage droop under load.",
                "Step 2: Check Ground (GND): Use multimeter continuity / resistance mode to ensure all Ground pins share a common zero-ohm return path to the power supply negative terminal.",
                "Step 3: Check Signal & Continuity: Verify signal integrity and jumper wire continuity from driver pins (MCU GPIOs) to target component inputs. Inspect for cold solder joints or loose breadboard springs.",
                "Step 4: Measure Specific In-Circuit Voltages: For silicon transistors, verify Base-Emitter voltage Vbe is ~0.7V when driven ON. For MOSFETs, verify Gate-Source voltage Vgs exceeds threshold Vgs(th). For ICs, verify /RESET is pulled HIGH.",
            ]
            return {
                "status": "SUCCESS",
                "target": "Physical Circuit Diagnostics",
                "summary": "Strict Physical Diagnostic Sequence (Power -> Ground -> Signal -> Bias Voltages)",
                "steps": steps,
            }

        if any(k in iss_low for k in ["transistor", "bjt", "2n2222", "bc547", "switching circuit"]):
            steps = [
                "Step 1: Check Power Supply & Vcc: Connect multimeter in DC Voltage mode between Vcc rail and GND. Confirm expected voltage (e.g. +5V or +12V) is stable under load.",
                "Step 2: Measure Base-Emitter Voltage (Vbe): Place red probe on Base and black probe on Emitter. A forward-biased silicon BJT must read ~0.6V to 0.7V. If 0V, check if your microcontroller GPIO is set to OUTPUT HIGH and that the base resistor is not open-circuit.",
                "Step 3: Measure Collector-Emitter Voltage (Vce): Place red probe on Collector and black probe on Emitter. If Vce ≈ 0.2V (Vce_sat), the transistor is fully saturated (acting as a closed switch). If Vce ≈ Vcc, the transistor is in CUTOFF (not conducting).",
                "Step 4: Check Base Resistor Sizing: Base current must be Ib >= Ic / 10 to ensure hard saturation. Calculate Rb = (V_gpio - 0.7V) / Ib.",
                "Step 5: Inductive Load Protection: If switching a relay, solenoid, or motor, ensure a flyback diode (e.g. 1N4007) is connected in reverse-parallel across the load to quench inductive back-EMF spikes.",
            ]
            return {
                "status": "SUCCESS",
                "target": "BJT Transistor Circuit",
                "summary": "Physical step-by-step diagnostic workflow for BJT switching circuit.",
                "steps": steps,
            }

        # 2. IR Sensor Obstacle Detector Diagnostic
        if any(k in iss_low for k in ["ir sensor", "obstacle sensor", "infrared", "tcrt5000"]):
            steps = [
                "Step 1: Verify Power Rails with Multimeter: Set multimeter to DC Volts mode. Measure across VCC and GND pins directly at the sensor header. Confirm stable 3.3V or 5.0V is present. If missing, check breadboard power rails and jumper wire continuity.",
                "Step 2: Optical Inspection of IR Transmitter: Point your smartphone camera at the clear/purple IR emitter LED while powered. Most digital camera CMOS sensors detect 940nm infrared light as a soft violet or purple glow. If dark, the IR emitter is unpowered or burned out.",
                "Step 3: Signal Pin (OUT) Multimeter Measurement: Place black probe on GND and red probe on the OUT pin. Wave a white piece of paper 3cm to 5cm in front of the sensor. The voltage should toggle clearly between HIGH (~Vcc) and LOW (0V). Most modules are ACTIVE-LOW (0V on detection).",
                "Step 4: Calibrate Sensitivity Potentiometer: Use a small flathead screwdriver to turn the onboard blue trim-pot. Turn clockwise to increase sensitivity, counter-clockwise to decrease until the onboard detection LED triggers only when an obstacle is present.",
                "Step 5: Ambient Light Immunity: Strong sunlight or incandescent halogen bulbs emit heavy infrared noise that can saturate the phototransistor. Shield the sensor from direct sunlight.",
            ]
            return {
                "status": "SUCCESS",
                "target": "IR Obstacle Sensor Module",
                "summary": "Physical step-by-step diagnostic workflow for IR sensor detection failure.",
                "steps": steps,
            }

        # 3. MOSFET Circuit Diagnostic
        if any(k in iss_low for k in ["mosfet", "fet", "irfz44n", "2n7000", "motor driver"]):
            steps = [
                "Step 1: Check Gate-to-Source Voltage (Vgs): Measure DC voltage between Gate and Source. For a standard IRFZ44N, Vgs must be 8V-10V for full saturation. If driven directly by a 3.3V/5V MCU, use a logic-level MOSFET (e.g., IRLZ44N, AO3400) or a transistor gate driver.",
                "Step 2: Gate Pull-Down Resistor: Confirm a 10kΩ pull-down resistor is connected between Gate and Source. Without it, the high gate impedance will pick up stray electrostatic charges and keep the MOSFET partially ON.",
                "Step 3: Drain-to-Source Voltage (Vds): When Gate is HIGH, Vds should drop to millivolts (I_d * R_DS(on)). If Vds stays high or the MOSFET gets blazing hot, it is operating in the linear active region instead of full saturation.",
                "Step 4: Flyback Diode Check: For inductive loads (motors/solenoids), verify a fast-recovery diode across the load.",
            ]
            return {
                "status": "SUCCESS",
                "target": "MOSFET Power Switch",
                "summary": "Physical step-by-step diagnostic workflow for MOSFET switching.",
                "steps": steps,
            }

        # 4. Microcontroller Flashing / Reset / Power Diagnostic
        if any(k in iss_low for k in ["microcontroller", "mcu", "arduino", "esp32", "atmega", "not booting", "upload failed", "flashing"]):
            steps = [
                "Step 1: Measure Vcc at the IC Pin: Measure directly between VCC (Pin 7 on ATmega328, 3V3 on ESP32) and GND. Confirm no brownout dip occurs when plugging in peripherals.",
                "Step 2: Check 0.1uF Decoupling Capacitors: Ensure a 100nF (0.1µF) ceramic capacitor is connected between Vcc and GND as close as physically possible to the microcontroller pins.",
                "Step 3: Reset Line Voltage: Measure voltage on the /RESET pin. It should be pulled HIGH (to Vcc) via a 10kΩ resistor. If it reads 0V, the MCU is held in permanent hardware reset.",
                "Step 4: UART Serial Connections: Ensure TX on programmer connects to RX on MCU, and RX connects to TX (crossover wiring). Ensure GND is shared between programmer and target board.",
                "Step 5: ESP32 Boot Strapping: GPIO0 must be pulled LOW to enter bootloader mode, and GPIO2 must not be pulled HIGH during boot.",
            ]
            return {
                "status": "SUCCESS",
                "target": "Microcontroller Circuit",
                "summary": "Physical hardware diagnostic for microcontroller boot & serial communication.",
                "steps": steps,
            }

        # 5. Generic Electronics Diagnostic
        steps = [
            "Step 1: Check Power Rail Continuity & Voltage: Set multimeter to DC Voltage mode. Verify supply voltage at the component pins under load.",
            "Step 2: Inspect for Thermal Hotspots: Feel components with a finger or thermal camera for excessive heat. Smoking or hot components indicate shorts or reverse polarity.",
            "Step 3: Ground Continuity: Set multimeter to Continuity / Beep mode. Probe all GND pins to confirm zero-ohm return path to the power supply negative terminal.",
            "Step 4: Measure in-circuit junction voltages (Diode mode) with power turned OFF.",
        ]
        return {
            "status": "SUCCESS",
            "target": "General Circuit",
            "summary": "Physical hardware diagnostic steps for electrical troubleshooting.",
            "steps": steps,
        }

    def get_test_procedure(self, component_name: str) -> Dict[str, Any]:
        """
        Returns precise multimeter bench test instructions for verifying component health.
        """
        c_low = component_name.lower()

        # BJT Transistor Test
        if any(k in c_low for k in ["bjt", "transistor", "bc547", "2n2222", "2n3904", "2n3906", "npn", "pnp"]):
            is_pnp = any(k in c_low for k in ["pnp", "bc557", "2n3906"])
            if is_pnp:
                instructions = (
                    "Here is the test procedure for PNP BJT:\n"
                    "1. Set your multimeter to Diode Test mode (symbol: ->|-).\n"
                    "2. Place the BLACK probe on the Base (Pin 2 on BC557).\n"
                    "3. Place the RED probe on the Emitter: Expected reading: 0.6V - 0.7V forward drop.\n"
                    "4. Move RED probe to Collector: Expected reading: 0.6V - 0.7V forward drop.\n"
                    "5. Reverse probes (RED on Base, BLACK on E/C): Expected reading: OL (Over Limit / Open Circuit).\n"
                    "6. Measure Collector to Emitter in both directions: Both must read OL. If 0.00V, the transistor is shorted."
                )
            else:
                instructions = (
                    "Here is the test procedure for NPN BJT (e.g. BC547, 2N2222):\n"
                    "1. Set your multimeter to Diode Test mode (symbol: ->|-).\n"
                    "2. Place the RED probe on the Base (Pin 2 on BC547, Pin 2 on 2N2222).\n"
                    "3. Place the BLACK probe on the Emitter: Expected reading: 0.60V - 0.70V forward voltage drop.\n"
                    "4. Move the BLACK probe to the Collector: Expected reading: 0.60V - 0.70V forward voltage drop.\n"
                    "5. Reverse the probes (BLACK on Base, RED on Emitter & Collector): Expected reading: OL (Open Circuit / No conduction).\n"
                    "6. Measure Collector to Emitter in both directions: Both must read OL. Any low resistance or 0V drop indicates a blown/shorted transistor."
                )
            return {"status": "SUCCESS", "component": component_name, "procedure": instructions}

        # MOSFET Test
        if any(k in c_low for k in ["mosfet", "fet", "irfz44n", "2n7000"]):
            instructions = (
                "Here is the test procedure for N-Channel MOSFET (e.g. IRFZ44N, 2N7000):\n"
                "1. Set your multimeter to Diode Test mode.\n"
                "2. Discharge the gate: Touch a metallic screwdriver or your finger across Gate and Source pins.\n"
                "3. Body Diode Check: Place BLACK probe on Drain, RED probe on Source: Expected reading: ~0.45V - 0.55V (internal body diode forward drop).\n"
                "4. Reverse probes (RED on Drain, BLACK on Source): Expected reading: OL (Channel is closed).\n"
                "5. Charge the Gate: Place RED probe on Gate, BLACK probe on Source for 2 seconds (charges gate capacitance).\n"
                "6. Verify Channel Activation: Move RED probe to Drain (keep BLACK on Source): Expected reading: Near 0.00V (Channel conducted and turned ON!).\n"
                "7. Discharge & Turn OFF: Touch Gate to Source pins together. Measure Drain-Source again: Reading should return to OL."
            )
            return {"status": "SUCCESS", "component": component_name, "procedure": instructions}

        # Diode / LED Test
        if any(k in c_low for k in ["diode", "led", "1n4007", "1n4148"]):
            instructions = (
                "Here is the test procedure for Diodes / LEDs:\n"
                "1. Set your multimeter to Diode Test mode.\n"
                "2. Forward Bias: Place RED probe on Anode (long leg / non-stripe), BLACK probe on Cathode (stripe side).\n"
                "   - Standard Silicon Diode (1N4007): Expected reading: 0.55V - 0.70V.\n"
                "   - Schottky Diode (1N5819): Expected reading: 0.20V - 0.35V.\n"
                "   - Red/Green LED: LED should faintly glow; expected reading: 1.8V - 2.2V.\n"
                "   - Blue/White LED: Expected reading: 2.8V - 3.3V.\n"
                "3. Reverse Bias: Place BLACK probe on Anode, RED probe on Cathode.\n"
                "   - Expected reading: OL (no leakage). If it reads near 0V, diode is shorted."
            )
            return {"status": "SUCCESS", "component": component_name, "procedure": instructions}

        # General Component
        instructions = (
            f"Here is the general bench test procedure for {component_name}:\n"
            "1. Disconnect all power from the circuit before taking resistance or diode measurements.\n"
            "2. Set multimeter to Continuity / Resistance or Diode test mode.\n"
            "3. Measure input to ground and output to ground to rule out direct shorts (0.00 Ohms).\n"
            "4. Power the circuit with current-limited power supply (set current limit to 100mA initially) and measure DC rail voltages."
        )
        return {"status": "SUCCESS", "component": component_name, "procedure": instructions}

    # =================================================================
    # LIGHTWEIGHT PYTHON CIRCUIT SIMULATOR / CALCULATOR
    # =================================================================

    def calculate_voltage_divider(
        self,
        r1: Optional[float] = None,
        r2: Optional[float] = None,
        vin: Optional[float] = None,
        r1_ohms: Optional[float] = None,
        r2_ohms: Optional[float] = None,
        vin_volts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates output voltage, current, and power dissipation for a 2-resistor voltage divider.
        Formula: Vout = Vin * (R2 / (R1 + R2))
        """
        r1_val = r1 if r1 is not None else (r1_ohms if r1_ohms is not None else 0.0)
        r2_val = r2 if r2 is not None else (r2_ohms if r2_ohms is not None else 0.0)
        vin_val = vin if vin is not None else (vin_volts if vin_volts is not None else 0.0)

        if r1_val + r2_val <= 0:
            return {"status": "FAILED", "error": "Total resistance R1 + R2 must be greater than zero."}

        vout = vin_val * (r2_val / (r1_val + r2_val))
        total_r = r1_val + r2_val
        current = vin_val / total_r  # Amperes
        current_ma = current * 1000.0  # mA
        p_r1 = (current**2) * r1_val  # Watts
        p_r2 = (current**2) * r2_val  # Watts
        total_power = vin_val * current

        # Determine standard resistor power rating recommendation
        rec_rating = "1/4W (250mW)" if max(p_r1, p_r2) < 0.125 else ("1/2W (500mW)" if max(p_r1, p_r2) < 0.25 else "1W+ power resistor")

        summary = (
            f"Voltage Divider Calculation Result:\n"
            f"- Input Voltage (Vin): {vin_val} V\n"
            f"- Output Voltage (Vout): {round(vout, 3)} V\n"
            f"- Total Resistance: {total_r:,.1f} Ohms\n"
            f"- Divider Current: {round(current_ma, 3)} mA\n"
            f"- Power Dissipation in R1: {round(p_r1 * 1000, 2)} mW\n"
            f"- Power Dissipation in R2: {round(p_r2 * 1000, 2)} mW\n"
            f"- Recommended Resistor Rating: {rec_rating}\n"
            f"- Note: Ensure load impedance connected to Vout is at least 10x larger than R2 ({round(r2_val * 10, 1)} Ohms) to prevent loading voltage sag."
        )

        return {
            "status": "SUCCESS",
            "vin": vin_val,
            "vout": round(vout, 4),
            "vout_volts": round(vout, 4),
            "formula": "Vout = Vin * (R2 / (R1 + R2))",
            "r1": r1_val,
            "r2": r2_val,
            "current_amps": current,
            "current_ma": round(current_ma, 3),
            "p_r1_mw": round(p_r1 * 1000, 2),
            "p_r2_mw": round(p_r2 * 1000, 2),
            "summary": summary,
        }

    def calculate_rc_time_constant(
        self,
        r: Optional[float] = None,
        c: Optional[float] = None,
        resistance_ohms: Optional[float] = None,
        capacitance_farads: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates RC time constant tau = R * C, cutoff frequency fc = 1 / (2*pi*R*C),
        and transient charging times.
        r: resistance in Ohms
        c: capacitance in Farads (e.g. 0.000001 for 1uF)
        """
        r_val = r if r is not None else (resistance_ohms if resistance_ohms is not None else 0.0)
        c_val = c if c is not None else (capacitance_farads if capacitance_farads is not None else 0.0)

        if r_val <= 0 or c_val <= 0:
            return {"status": "FAILED", "error": "R and C must be positive non-zero values."}

        tau = r_val * c_val  # seconds
        tau_ms = tau * 1000.0  # ms
        cutoff_freq = 1.0 / (2.0 * math.pi * r_val * c_val)  # Hz
        time_99 = 5.0 * tau  # 5 time constants = 99.3% charged

        summary = (
            f"RC Time Constant Calculation:\n"
            f"- Resistance (R): {r_val:,.1f} Ohms\n"
            f"- Capacitance (C): {c_val * 1e6:,.2f} uF ({c_val:,.2e} F)\n"
            f"- Time Constant (tau = R x C): {round(tau_ms, 3)} ms ({round(tau, 6)} s)\n"
            f"- 63.2% Charge Time (1tau): {round(tau_ms, 3)} ms\n"
            f"- 99.3% Full Charge Time (5tau): {round(time_99 * 1000, 3)} ms\n"
            f"- -3dB Low-Pass / High-Pass Cutoff Frequency (fc): {round(cutoff_freq, 2)} Hz"
        )

        return {
            "status": "SUCCESS",
            "tau_sec": round(tau, 6),
            "tau_seconds": round(tau, 6),
            "tau_ms": round(tau_ms, 3),
            "cutoff_hz": round(cutoff_freq, 2),
            "t_99_ms": round(time_99 * 1000, 3),
            "summary": summary,
        }

    def calculate_led_resistor(self, v_supply: float, v_forward: float = 2.0, i_forward_ma: float = 20.0) -> Dict[str, Any]:
        """
        Calculates current-limiting resistor for LED.
        R = (V_supply - V_forward) / I_forward
        """
        if v_supply <= v_forward:
            return {"status": "FAILED", "error": f"Supply voltage ({v_supply}V) must exceed LED forward voltage ({v_forward}V)."}

        i_amp = i_forward_ma / 1000.0
        v_drop = v_supply - v_forward
        r_exact = v_drop / i_amp
        p_res = (i_amp**2) * r_exact

        # Nearest E24 standard resistor
        e24 = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]
        decade = 10 ** math.floor(math.log10(r_exact))
        norm = r_exact / decade
        standard_r = min(e24, key=lambda x: abs(x - norm * 10)) * (decade / 10)

        summary = (
            f"LED Current-Limiting Resistor Calculation:\n"
            f"• Supply Voltage: {v_supply} V\n"
            f"• LED Forward Voltage (Vf): {v_forward} V\n"
            f"• Target Forward Current: {i_forward_ma} mA\n"
            f"• Voltage Dropped across Resistor: {round(v_drop, 2)} V\n"
            f"• Calculated Exact Resistance: {round(r_exact, 1)} Ω\n"
            f"• Recommended Standard E24 Resistor: {int(standard_r)} Ω (1/4 Watt)\n"
            f"• Resistor Power Dissipation: {round(p_res * 1000, 2)} mW"
        )

        return {
            "status": "SUCCESS",
            "exact_resistor_ohms": round(r_exact, 1),
            "standard_resistor_ohms": int(standard_r),
            "power_mw": round(p_res * 1000, 2),
            "summary": summary,
        }


# Global singleton
debug_oracle = CircuitDebugOracle()


def calculate_voltage_divider_tool(args: Any = None, **kwargs) -> Dict[str, Any]:
    """
    Accepts a single dictionary argument or kwargs.
    Extracts r1 = args.get('r1'), r2 = args.get('r2'), vin = args.get('vin').
    """
    if args is None:
        args = kwargs
    elif not isinstance(args, dict):
        args = {"r1": args, **kwargs}
    else:
        if "args" in args and isinstance(args["args"], dict):
            args = args["args"]
        elif kwargs:
            combined = dict(args)
            combined.update(kwargs)
            args = combined

    r1 = args.get("r1")
    if r1 is None:
        r1 = args.get("r1_ohms", 10000.0)
    r2 = args.get("r2")
    if r2 is None:
        r2 = args.get("r2_ohms", 10000.0)
    vin = args.get("vin")
    if vin is None:
        vin = args.get("vin_volts", 5.0)

    return debug_oracle.calculate_voltage_divider(float(r1), float(r2), float(vin))


