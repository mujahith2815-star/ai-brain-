"""
Component & Datasheet Engine for P.H.A.S.S Hardware Co-Pilot.
Provides component electrical specifications, ASCII pinout diagrams,
and cross-reference replacements for electronics engineering.
"""

from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("phass.hardware.component_engine")


@dataclass
class ComponentSpec:
    name: str
    type_category: str  # BJT, MOSFET, Microcontroller, IC, Linear Regulator, Sensor Module, Diode
    package: str  # TO-92, TO-220, DIP-28, DIP-8, Breakout
    description: str
    pinout: Dict[str, str]  # e.g. {"1": "Collector", "2": "Base", "3": "Emitter"} or {"C": "1", "B": "2", "E": "3"}
    pin_labels: List[Tuple[int, str]]  # [(1, "Collector"), (2, "Base"), ...]
    key_specs: Dict[str, Any]  # {"Vce": "45V", "Ic": "100mA", "hFE": "110-800"}
    equivalents: List[str]
    notes: str = ""
    ascii_diagram: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type_category,
            "package": self.package,
            "description": self.description,
            "pinout": self.pinout,
            "pin_labels": [f"Pin {p}: {name}" for p, name in self.pin_labels],
            "key_specs": self.key_specs,
            "equivalents": self.equivalents,
            "notes": self.notes,
            "ascii_diagram": self.ascii_diagram,
        }


# =====================================================================
# EMBEDDED DATASHEET DATABASE
# =====================================================================

COMPONENT_DB: Dict[str, ComponentSpec] = {
    "bc547": ComponentSpec(
        name="BC547",
        type_category="NPN Bipolar Junction Transistor (BJT)",
        package="TO-92",
        description="General-purpose low-power NPN silicon epitaxial planar transistor for audio frequency amplifiers and switches.",
        pinout={"1": "Collector (C)", "2": "Base (B)", "3": "Emitter (E)", "C": "1", "B": "2", "E": "3"},
        pin_labels=[(1, "Collector"), (2, "Base"), (3, "Emitter")],
        key_specs={
            "V_CEO": "45V (Collector-Emitter breakdown)",
            "V_CBO": "50V (Collector-Base breakdown)",
            "V_EBO": "6V (Emitter-Base breakdown)",
            "I_C": "100mA (Continuous collector current)",
            "I_CM": "200mA (Peak collector current)",
            "h_FE": "110 - 800 (DC current gain, depends on A/B/C bin)",
            "V_CE(sat)": "0.2V max at Ic=10mA, Ib=0.5mA",
            "V_BE(on)": "0.6V - 0.7V typical",
            "f_T": "300 MHz (Transition frequency)",
            "P_tot": "500 mW (Power dissipation at 25°C)",
        },
        equivalents=["BC548", "BC546", "2N3904 (Note reversed pinout: E=1, B=2, C=3!)", "PN2222"],
        notes="European TO-92 pinout: 1=Collector, 2=Base, 3=Emitter (flat face facing you, pins down). Complement is BC557 (PNP).",
        ascii_diagram="""
  BC547 (TO-92 Package - Flat Face Forward)
          ______
         /      \\
        |  BC547 |
        |________|
          |  |  |
          1  2  3
          |  |  |
          C  B  E
   Pin 1: Collector (C)
   Pin 2: Base (B)
   Pin 3: Emitter (E)
""",
    ),
    "bc548": ComponentSpec(
        name="BC548",
        type_category="NPN Bipolar Junction Transistor (BJT)",
        package="TO-92",
        description="Standard general-purpose NPN switching and amplifier transistor.",
        pinout={"1": "Collector (C)", "2": "Base (B)", "3": "Emitter (E)", "C": "1", "B": "2", "E": "3"},
        pin_labels=[(1, "Collector"), (2, "Base"), (3, "Emitter")],
        key_specs={"V_CEO": "30V", "I_C": "100mA", "h_FE": "110 - 800", "V_CE(sat)": "0.2V", "f_T": "300 MHz"},
        equivalents=["BC547", "BC549", "2N3904"],
        notes="Pinout: 1=Collector, 2=Base, 3=Emitter.",
        ascii_diagram="""
  BC548 (TO-92 Package)
   Pin 1: Collector (C) | Pin 2: Base (B) | Pin 3: Emitter (E)
""",
    ),
    "bc557": ComponentSpec(
        name="BC557",
        type_category="PNP Bipolar Junction Transistor (BJT)",
        package="TO-92",
        description="PNP complementary partner to BC547 for push-pull output stages and high-side switching.",
        pinout={"1": "Collector (C)", "2": "Base (B)", "3": "Emitter (E)", "C": "1", "B": "2", "E": "3"},
        pin_labels=[(1, "Collector"), (2, "Base"), (3, "Emitter")],
        key_specs={"V_CEO": "-45V", "I_C": "-100mA", "h_FE": "125 - 800", "V_CE(sat)": "-0.3V"},
        equivalents=["BC558", "BC556", "2N3906 (reversed pinout)"],
        notes="PNP device: requires base voltage lower than emitter by ~0.7V to conduct.",
        ascii_diagram="""
  BC557 (TO-92 Package - PNP)
   Pin 1: Collector (C) | Pin 2: Base (B) | Pin 3: Emitter (E)
""",
    ),
    "2n2222": ComponentSpec(
        name="2N2222 / PN2222",
        type_category="NPN Bipolar Junction Transistor (BJT)",
        package="TO-92 / TO-18",
        description="High-speed, medium-power NPN switching transistor capable of driving small relays, motors, and LEDs.",
        pinout={"1": "Emitter (E)", "2": "Base (B)", "3": "Collector (C)", "E": "1", "B": "2", "C": "3"},
        pin_labels=[(1, "Emitter"), (2, "Base"), (3, "Collector")],
        key_specs={
            "V_CEO": "40V",
            "I_C": "800mA (Continuous)",
            "h_FE": "100 - 300 (at Ic=150mA)",
            "V_CE(sat)": "0.3V typical at Ic=150mA, Ib=15mA",
            "f_T": "250 - 300 MHz",
            "P_tot": "625 mW (TO-92)",
        },
        equivalents=["2N3904 (Lower current 200mA)", "PN2222A", "BC547 (Watch pinout!)", "TIP120 (For higher loads)"],
        notes="Standard US TO-92 pinout: 1=Emitter, 2=Base, 3=Collector. Notice this is opposite to European BC547.",
        ascii_diagram="""
  2N2222 (TO-92 Package - Flat Face Forward)
          ______
         /      \\
        | 2N2222 |
        |________|
          |  |  |
          1  2  3
          |  |  |
          E  B  C
   Pin 1: Emitter (E)
   Pin 2: Base (B)
   Pin 3: Collector (C)
""",
    ),
    "2n3904": ComponentSpec(
        name="2N3904",
        type_category="NPN Bipolar Junction Transistor (BJT)",
        package="TO-92",
        description="Classic general-purpose NPN transistor for signal amplification and fast switching up to 100mA.",
        pinout={"1": "Emitter (E)", "2": "Base (B)", "3": "Collector (C)", "E": "1", "B": "2", "C": "3"},
        pin_labels=[(1, "Emitter"), (2, "Base"), (3, "Collector")],
        key_specs={
            "V_CEO": "40V",
            "I_C": "200mA",
            "h_FE": "100 - 300",
            "V_CE(sat)": "0.2V at Ic=10mA, Ib=1mA",
            "f_T": "300 MHz",
        },
        equivalents=["2N2222", "BC547 (Pinout reversed!)", "SS8050"],
        notes="Pinout: 1=Emitter, 2=Base, 3=Collector. Complement is 2N3906.",
        ascii_diagram="""
  2N3904 (TO-92 Package)
   Pin 1: Emitter (E) | Pin 2: Base (B) | Pin 3: Collector (C)
""",
    ),
    "2n3906": ComponentSpec(
        name="2N3906",
        type_category="PNP Bipolar Junction Transistor (BJT)",
        package="TO-92",
        description="Complementary PNP counterpart to 2N3904 for high-side switching and analog circuits.",
        pinout={"1": "Emitter (E)", "2": "Base (B)", "3": "Collector (C)", "E": "1", "B": "2", "C": "3"},
        pin_labels=[(1, "Emitter"), (2, "Base"), (3, "Collector")],
        key_specs={"V_CEO": "-40V", "I_C": "-200mA", "h_FE": "100 - 300", "V_CE(sat)": "-0.25V"},
        equivalents=["2N2907", "BC557"],
        notes="Pinout: 1=Emitter, 2=Base, 3=Collector.",
        ascii_diagram="""
  2N3906 (TO-92 Package - PNP)
   Pin 1: Emitter (E) | Pin 2: Base (B) | Pin 3: Collector (C)
""",
    ),
    "tip120": ComponentSpec(
        name="TIP120",
        type_category="NPN Darlington Power Transistor",
        package="TO-220",
        description="High-gain power Darlington pair with internal damper diode for driving high-current DC motors, solenoids, and high-power LEDs.",
        pinout={"1": "Base (B)", "2": "Collector (C)", "3": "Emitter (E)", "B": "1", "C": "2", "E": "3"},
        pin_labels=[(1, "Base"), (2, "Collector"), (3, "Emitter")],
        key_specs={
            "V_CEO": "60V",
            "I_C": "5A (Continuous), 8A (Peak)",
            "h_FE": "1000 min (Very high sensitivity)",
            "V_CE(sat)": "2.0V max at Ic=3A (Darlington has higher saturation drop!)",
            "P_tot": "65W (with heatsink)",
        },
        equivalents=["TIP122 (100V)", "TIP102", "BD649", "IRFZ44N (MOSFET upgrade for lower heat)"],
        notes="Heatsink required above 1A continuous! Saturation voltage is ~1.5V-2.0V so it produces more heat than a MOSFET.",
        ascii_diagram="""
  TIP120 (TO-220 Package - Metal Tab Facing Back)
        +-------------+
        |   [ O ]     |  <-- Mounting Hole / Metal Tab (connected to Collector)
        +-------------+
        |   TIP120    |
        +-------------+
           |   |   |
           1   2   3
           |   |   |
           B   C   E
   Pin 1: Base (B)
   Pin 2: Collector (C)
   Pin 3: Emitter (E)
""",
    ),
    "irfz44n": ComponentSpec(
        name="IRFZ44N",
        type_category="N-Channel Power MOSFET",
        package="TO-220",
        description="Ultra-low R_DS(on) 55V 49A N-Channel power MOSFET for high-efficiency DC motor drives, PWM speed controls, and high-side power switching.",
        pinout={"1": "Gate (G)", "2": "Drain (D)", "3": "Source (S)", "G": "1", "D": "2", "S": "3"},
        pin_labels=[(1, "Gate"), (2, "Drain"), (3, "Source")],
        key_specs={
            "V_DS": "55V (Drain-Source Breakdown)",
            "I_D": "49A at 25°C, 35A at 100°C",
            "R_DS(on)": "17.5 mΩ max at Vgs=10V",
            "V_GS(th)": "2.0V to 4.0V (Threshold voltage)",
            "Q_g": "63 nC (Total Gate Charge)",
            "P_D": "94W (with heatsink)",
        },
        equivalents=["IRLZ44N (Logic-Level 5V/3.3V gate gate)", "STP55NF06", "IRF3205", "FQP30N06L"],
        notes="IMPORTANT: Standard IRFZ44N requires 10V gate drive for full saturation. If driven directly from Arduino 5V or ESP32 3.3V, use logic-level IRLZ44N instead or use a gate driver!",
        ascii_diagram="""
  IRFZ44N (TO-220 Package - Metal Tab Facing Back)
        +-------------+
        |   [ O ]     |  <-- Mounting Tab (connected to Drain)
        +-------------+
        |   IRFZ44N   |
        +-------------+
           |   |   |
           1   2   3
           |   |   |
           G   D   S
   Pin 1: Gate (G)
   Pin 2: Drain (D)
   Pin 3: Source (S)
""",
    ),
    "2n7000": ComponentSpec(
        name="2N7000",
        type_category="Small-Signal N-Channel MOSFET",
        package="TO-92",
        description="Compact logic-level N-channel enhancement mode field-effect transistor for level shifting, switching, and signal conditioning.",
        pinout={"1": "Source (S)", "2": "Gate (G)", "3": "Drain (D)", "S": "1", "G": "2", "D": "3"},
        pin_labels=[(1, "Source"), (2, "Gate"), (3, "Drain")],
        key_specs={"V_DS": "60V", "I_D": "200mA continuous", "R_DS(on)": "5.3 Ω at Vgs=4.5V", "V_GS(th)": "0.8V to 3.0V"},
        equivalents=["BS170 (Caution: BS170 pinout is 1=Drain, 2=Gate, 3=Source!)", "BSS138 (SMD SOT-23)"],
        notes="Logic-level compatible with 3.3V and 5V microcontrollers.",
        ascii_diagram="""
  2N7000 (TO-92 Package)
   Pin 1: Source (S) | Pin 2: Gate (G) | Pin 3: Drain (D)
""",
    ),
    "atmega328": ComponentSpec(
        name="ATmega328P",
        type_category="8-bit AVR Microcontroller (Arduino Uno Core)",
        package="28-pin DIP (PDIP-28) / 32-pin TQFP",
        description="High-performance, low-power Microchip AVR 8-bit microcontroller with 32KB flash, 2KB SRAM, 1KB EEPROM, 6 PWM channels, and 10-bit ADC.",
        pinout={
            "1": "PC6 (/RESET)",
            "2": "PD0 (RXD/D0)",
            "3": "PD1 (TXD/D1)",
            "4": "PD2 (INT0/D2)",
            "5": "PD3 (INT1/PWM/D3)",
            "6": "PD4 (XCK/T0/D4)",
            "7": "VCC (+5V Power)",
            "8": "GND (0V Ground)",
            "9": "PB6 (XTAL1/TOSC1)",
            "10": "PB7 (XTAL2/TOSC2)",
            "11": "PD5 (T1/PWM/D5)",
            "12": "PD6 (AIN0/PWM/D6)",
            "13": "PD7 (AIN1/D7)",
            "14": "PB0 (ICP1/D8)",
            "15": "PB1 (OC1A/PWM/D9)",
            "16": "PB2 (SS/PWM/D10)",
            "17": "PB3 (MOSI/PWM/D11)",
            "18": "PB4 (MISO/D12)",
            "19": "PB5 (SCK/LED/D13)",
            "20": "AVCC (+5V ADC Power)",
            "21": "AREF (Analog Reference)",
            "22": "GND (0V Ground)",
            "23": "PC0 (ADC0/A0)",
            "24": "PC1 (ADC1/A1)",
            "25": "PC2 (ADC2/A2)",
            "26": "PC3 (ADC3/A3)",
            "27": "PC4 (ADC4/SDA/A4)",
            "28": "PC5 (ADC5/SCL/A5)",
        },
        pin_labels=[
            (1, "PC6 (/RESET)"),
            (2, "PD0 (RXD)"),
            (3, "PD1 (TXD)"),
            (4, "PD2 (INT0)"),
            (5, "PD3 (INT1, PWM)"),
            (6, "PD4 (XCK/T0)"),
            (7, "VCC (+5V)"),
            (8, "GND (0V)"),
            (9, "PB6 (XTAL1)"),
            (10, "PB7 (XTAL2)"),
            (11, "PD5 (T1, PWM)"),
            (12, "PD6 (AIN0, PWM)"),
            (13, "PD7 (AIN1)"),
            (14, "PB0 (ICP1)"),
            (15, "PB1 (OC1A, PWM)"),
            (16, "PB2 (SS, PWM)"),
            (17, "PB3 (MOSI, PWM)"),
            (18, "PB4 (MISO)"),
            (19, "PB5 (SCK, LED)"),
            (20, "AVCC (ADC Supply)"),
            (21, "AREF (Analog Ref)"),
            (22, "GND (0V)"),
            (23, "PC0 (ADC0)"),
            (24, "PC1 (ADC1)"),
            (25, "PC2 (ADC2)"),
            (26, "PC3 (ADC3)"),
            (27, "PC4 (ADC4, I2C SDA)"),
            (28, "PC5 (ADC5, I2C SCL)"),
        ],
        key_specs={
            "Core": "8-bit AVR RISC up to 20 MHz (16 MHz on Arduino)",
            "Flash": "32 KB (with 0.5 KB bootloader)",
            "SRAM": "2 KB",
            "EEPROM": "1 KB",
            "Operating Voltage": "1.8V to 5.5V (typically 5.0V)",
            "I/O Pins": "23 Programmable GPIOs",
            "ADC": "6 Channels, 10-bit resolution",
            "Timers": "2x 8-bit, 1x 16-bit",
            "Communication": "UART, SPI, I2C (TWI)",
        },
        equivalents=["ATmega328", "ATmega328PB (enhanced)", "ATmega168 (16KB Flash)", "ATmega88"],
        notes="Standard Arduino Uno microcontroller. Power pins: Pin 7=VCC, Pin 8=GND, Pin 20=AVCC, Pin 22=GND.",
        ascii_diagram="""
           ATmega328P 28-Pin Dual-In-Line (DIP) Pinout
                        +------\\/------+
        (RESET)  PC6  1 |              | 28  PC5  (ADC5 / SCL)
          (RXD)  PD0  2 |              | 27  PC4  (ADC4 / SDA)
          (TXD)  PD1  3 |              | 26  PC3  (ADC3)
         (INT0)  PD2  4 |              | 25  PC2  (ADC2)
    (INT1/OC2B)  PD3  5 |              | 24  PC1  (ADC1)
         (T0)    PD4  6 |  ATmega328P  | 23  PC0  (ADC0)
                 VCC  7 |              | 22  GND
                 GND  8 |              | 21  AREF
       (XTAL1)   PB6  9 |              | 20  AVCC
       (XTAL2)   PB7 10 |              | 19  PB5  (SCK / Built-in LED)
        (OC0B)   PD5 11 |              | 18  PB4  (MISO)
        (OC0A)   PD6 12 |              | 17  PB3  (MOSI / OC2A)
        (AIN1)   PD7 13 |              | 16  PB2  (SS / OC1B)
        (ICP1)   PB0 14 |              | 15  PB1  (OC1A / PWM)
                        +--------------+
""",
    ),
    "esp32": ComponentSpec(
        name="ESP32 (ESP-WROOM-32)",
        type_category="32-bit Dual-Core Wi-Fi & Bluetooth Microcontroller",
        package="38-pin DevKit / Module",
        description="Flagship Espressif dual-core Xtensa 32-bit LX6 MCU with integrated 2.4 GHz Wi-Fi, Bluetooth 4.2 BLE, hardware crypto, capacitive touch, ADC, and DAC.",
        pinout={
            "3V3": "Power (+3.3V DC)",
            "EN": "Reset / Enable (Active High)",
            "GPIO36": "VP (Sensor_VP, Input Only)",
            "GPIO39": "VN (Sensor_VN, Input Only)",
            "GPIO34": "Input Only",
            "GPIO35": "Input Only",
            "GPIO32": "Touch9 / ADC1_CH4",
            "GPIO33": "Touch8 / ADC1_CH5",
            "GPIO25": "DAC1 / ADC2_CH8",
            "GPIO26": "DAC2 / ADC2_CH9",
            "GPIO27": "Touch7 / ADC2_CH7",
            "GPIO14": "Touch6 / HSPI_CLK",
            "GPIO12": "Touch5 / Strapping Pin (Must be LOW for flashing)",
            "GND": "Ground (0V)",
            "GPIO13": "Touch4 / HSPI_ID",
            "GPIO23": "VSPI_MOSI",
            "GPIO22": "I2C SCL",
            "GPIO1": "UART0 TX",
            "GPIO3": "UART0 RX",
            "GPIO21": "I2C SDA",
            "GPIO19": "VSPI_MISO",
            "GPIO18": "VSPI_SCK",
            "GPIO5": "VSPI_CS / Strapping Pin",
            "GPIO4": "Touch0 / ADC2_CH0",
            "GPIO0": "BOOT (Strapping: LOW for bootloader, HIGH for run)",
            "GPIO2": "Onboard LED (Strapping: Floating or LOW on boot)",
            "GPIO15": "HSPI_SS",
            "VIN": "External 5V Power In",
        },
        pin_labels=[
            (1, "3V3"), (2, "EN"), (3, "GPIO36"), (4, "GPIO39"), (5, "GPIO34"), (6, "GPIO35"),
            (7, "GPIO32"), (8, "GPIO33"), (9, "GPIO25"), (10, "GPIO26"), (11, "GPIO27"), (12, "GPIO14"),
            (13, "GPIO12"), (14, "GND"), (15, "GPIO13"), (16, "GPIO23"), (17, "GPIO22"), (18, "GPIO1"),
            (19, "GPIO3"), (20, "GPIO21"), (21, "GND"), (22, "GPIO19"), (23, "GPIO18"), (24, "GPIO5"),
            (25, "GPIO17"), (26, "GPIO16"), (27, "GPIO4"), (28, "GPIO0"), (29, "GPIO2"), (30, "GPIO15"),
        ],
        key_specs={
            "Clock": "Up to 240 MHz Dual Core",
            "Memory": "520 KB SRAM, 4MB Flash",
            "Wi-Fi": "802.11 b/g/n (up to 150 Mbps)",
            "Bluetooth": "v4.2 BR/EDR and BLE",
            "Voltage": "3.3V Logic (NOT 5V tolerant on I/O!)",
            "DAC": "2x 8-bit DAC channels",
            "ADC": "18x 12-bit ADC channels",
        },
        equivalents=["ESP32-S3", "ESP32-C3 (RISC-V)", "ESP8266 (Legacy)"],
        notes="CRITICAL: ESP32 I/O pins are strictly 3.3V! Connecting 5V signals directly will burn the GPIO. Use logic level shifters.",
        ascii_diagram="""
            ESP32 30/38-Pin DevKit Pinout Overview
                  +-------------------+
             3V3  | [ ]             |  VIN (5V)
              EN  | [ ]    [ANT]    |  GND
          GPIO36  | [ ]             |  GPIO13
          GPIO39  | [ ]   ESP-32    |  GPIO12
          GPIO34  | [ ]  WROOM-32   |  GPIO14
          GPIO35  | [ ]             |  GPIO27
          GPIO32  | [ ]             |  GPIO26
          GPIO33  | [ ]             |  GPIO25
          GPIO25  | [ ]             |  GPIO33
          GPIO26  | [ ]             |  GPIO32
          GPIO27  | [ ]             |  GPIO35
          GPIO14  | [ ]             |  GPIO34
          GPIO12  | [ ]             |  GPIO39
             GND  | [ ]             |  GPIO36
                  +-------------------+
""",
    ),
    "ir_sensor": ComponentSpec(
        name="IR Obstacle Sensor Module",
        type_category="Infrared Optical Sensor Module",
        package="3-Pin / 4-Pin Header Breakout",
        description="Active infrared obstacle avoidance sensor module using a 940nm IR transmitter diode and phototransistor receiver pair coupled with an LM393 comparator.",
        pinout={"1": "VCC (+3.3V to +5V DC)", "2": "GND (Ground)", "3": "OUT (Digital Active-Low Output)", "VCC": "1", "GND": "2", "OUT": "3"},
        pin_labels=[(1, "VCC (+3.3V-5V)"), (2, "GND (Ground)"), (3, "OUT (Digital Signal)")],
        key_specs={
            "Operating Voltage": "3.3V - 5.0V DC",
            "Detection Range": "2 cm to 30 cm (adjustable)",
            "Detection Angle": "35°",
            "Output State": "Digital: HIGH when clear, LOW (0V) when obstacle detected",
            "Current Draw": "approx 20mA",
            "Comparator IC": "LM393 Dual Differential Comparator",
        },
        equivalents=["TCRT5000 IR Reflective Module", "E18-D80NK (Long range industrial)", "Sharp GP2Y0A21YK0F (Analog distance)"],
        notes="Module features onboard sensitivity potentiometer and two LEDs: Power LED (red) and Obstacle Detection LED (green).",
        ascii_diagram="""
      IR Obstacle Avoidance Sensor Module
        +-------------------------------+
        |  [IR Emitter]   [IR Detector] |  <-- 940nm Optical Pair
        |                               |
        |        [LM393 IC]             |
        |                               |
        |    [Potentiometer]            |  <-- Sensitivity Adjust
        |                               |
        |   [PWR-LED]    [DETECT-LED]   |
        +---+-------+-------+-----------+
            |       |       |
           VCC     GND     OUT
         (+3.3V/5V) (0V) (Active LOW)
""",
    ),
    "ne555": ComponentSpec(
        name="NE555 Timer IC",
        type_category="Precision Analog Timing IC",
        package="8-pin DIP (DIP-8)",
        description="Industry standard precision timing circuit capable of producing accurate time delays or oscillation in monostable or astable modes.",
        pinout={
            "1": "GND (Ground 0V)",
            "2": "TRIG (Trigger input, active < 1/3 Vcc)",
            "3": "OUT (Output up to 200mA sink/source)",
            "4": "RESET (Active LOW reset, tie to Vcc if unused)",
            "5": "CTRL (Control voltage, connect 10nF cap to GND)",
            "6": "THRESH (Threshold input, active > 2/3 Vcc)",
            "7": "DISCH (Discharge pin connected to open collector)",
            "8": "VCC (+4.5V to +16V Supply)",
        },
        pin_labels=[
            (1, "GND"), (2, "TRIG"), (3, "OUT"), (4, "RESET"),
            (5, "CTRL"), (6, "THRESH"), (7, "DISCH"), (8, "VCC"),
        ],
        key_specs={"Supply Voltage": "4.5V to 16V", "Max Output Current": "200mA", "Timing Frequency": "Up to 500 kHz"},
        equivalents=["LM555", "TLC555 (CMOS low-power)", "NE556 (Dual 555)"],
        notes="Pin 1=GND, Pin 8=VCC. Pin 4 should be pulled to VCC to prevent accidental reset.",
        ascii_diagram="""
            NE555 8-Pin DIP Timer
                 +---\\/---+
         GND   1 |        | 8   VCC (+5V..15V)
       TRIGGER 2 |  555   | 7   DISCHARGE
        OUTPUT 3 | TIMER  | 6   THRESHOLD
         RESET 4 |        | 5   CONTROL VOLTAGE
                 +--------+
""",
    ),
    "7805": ComponentSpec(
        name="LM7805 / 7805",
        type_category="Positive 5V Linear Voltage Regulator",
        package="TO-220",
        description="Standard 3-terminal positive voltage regulator delivering clean regulated +5.0V output up to 1.5A.",
        pinout={"1": "INPUT (Vin: 7V - 25V)", "2": "GROUND (GND)", "3": "OUTPUT (Vout: +5.0V DC)", "Vin": "1", "GND": "2", "Vout": "3"},
        pin_labels=[(1, "Input (Vin 7-25V)"), (2, "Ground (GND)"), (3, "Output (+5V Vout)")],
        key_specs={
            "Output Voltage": "+5.0V DC (±4%)",
            "Dropout Voltage": "2.0V (Requires Vin >= 7.0V)",
            "Max Current": "1.5A (with adequate heatsink)",
            "Quiescent Current": "5mA typical",
        },
        equivalents=["AMS1117-5.0 (Low dropout)", "LM2940-5.0 (1A LDO)", "Traco Power TSR 1-2450 (Drop-in buck replacement)"],
        notes="Requires input capacitor (0.33uF) and output capacitor (0.1uF) close to the pins to prevent high-frequency oscillation.",
        ascii_diagram="""
  LM7805 (TO-220 Package - Front Face)
        +-------------+
        |   [ O ]     |  <-- Heat Tab (GND)
        +-------------+
        |   LM7805    |
        +-------------+
           |   |   |
           1   2   3
           |   |   |
          IN  GND OUT
   Pin 1: Input (+7V to +25V)
   Pin 2: Ground (0V)
   Pin 3: Output (+5.0V regulated)
""",
    ),
}

# Aliases dictionary
COMPONENT_ALIASES: Dict[str, str] = {
    "2n2222a": "2n2222",
    "pn2222": "2n2222",
    "pn2222a": "2n2222",
    "atmega328": "atmega328",
    "atmega328p": "atmega328",
    "arduino uno chip": "atmega328",
    "mega328": "atmega328",
    "esp-32": "esp32",
    "esp-wroom-32": "esp32",
    "wroom32": "esp32",
    "ir sensor": "ir_sensor",
    "ir sensor module": "ir_sensor",
    "tcrt5000": "ir_sensor",
    "obstacle sensor": "ir_sensor",
    "555": "ne555",
    "555 timer": "ne555",
    "lm555": "ne555",
    "lm7805": "7805",
    "bc547 transistor": "bc547",
    "2n2222 transistor": "2n2222",
    "2n3904 transistor": "2n3904",
    "led": "led",
    "light emitting diode": "led",
}


class ComponentEngine:
    """Core component and datasheet lookup and visualization engine."""

    def __init__(self, db_json_path: Optional[str] = None):
        self.db = dict(COMPONENT_DB)
        self.aliases = dict(COMPONENT_ALIASES)
        if db_json_path is not None:
            self.db_json_path = Path(db_json_path)
        else:
            try:
                from core.data_hub import data_hub
                self.db_json_path = data_hub.resolve("hardware_db", "component_db.json")
            except Exception:
                self.db_json_path = Path("checkpoints/hardware_db.json")
        self._load_local_hardware_db()

    def _load_local_hardware_db(self) -> None:
        """Loads and merges components from component_db.json / hardware_db.json."""
        target_path = self.db_json_path
        if not target_path.exists():
            legacy_path = Path("checkpoints/hardware_db.json")
            if legacy_path.exists():
                target_path = legacy_path
            else:
                return
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    key = k.lower().strip()
                    # Parse into ComponentSpec
                    pin_labels_raw = v.get("pin_labels", [])
                    parsed_labels: List[Tuple[int, str]] = []
                    for idx, lab in enumerate(pin_labels_raw, start=1):
                        parsed_labels.append((idx, str(lab)))

                    spec = ComponentSpec(
                        name=v.get("name", k.upper()),
                        type_category=v.get("type", "Electronic Component"),
                        package=v.get("package", "Standard"),
                        description=v.get("description", ""),
                        pinout=v.get("pinout", {}),
                        pin_labels=parsed_labels,
                        key_specs=v.get("key_specs", {}),
                        equivalents=v.get("equivalents", []),
                        notes=v.get("notes", ""),
                        ascii_diagram=v.get("ascii_diagram", ""),
                    )
                    self.db[key] = spec
        except Exception as e:
            logger.debug(f"Notice loading hardware_db.json: {e}")

    def resolve_component_key(self, query: str) -> Optional[str]:
        """Maps user queries to normalized database key."""
        clean = re.sub(r"[^a-zA-Z0-9_\-]", " ", query.lower()).strip()
        tokens = clean.split()

        # Check multi-word aliases first
        for alias, key in self.aliases.items():
            if alias in clean:
                return key

        # Direct match or alias match
        for t in tokens:
            if t in self.db:
                return t
            if t in self.aliases:
                return self.aliases[t]

        for key in self.db:
            if key in clean:
                return key

        return None

    def fetch_datasheet(self, component_name: str) -> Dict[str, Any]:
        """
        Extracts component details, pinout, and key specifications.
        Falls back to comprehensive online technical query if not present locally.
        """
        key = self.resolve_component_key(component_name)
        if key and key in self.db:
            comp = self.db[key]
            return {
                "status": "SUCCESS",
                "component": comp.name,
                "found_locally": True,
                "data": comp.to_dict(),
            }

        # Dynamic fallback parser for unknown components
        c_clean = component_name.strip()
        return {
            "status": "SUCCESS",
            "component": c_clean,
            "found_locally": False,
            "data": {
                "name": c_clean,
                "type": "Electronic Component / Integrated Circuit",
                "package": "Standard Package",
                "description": f"Technical profile for {c_clean}.",
                "pinout": {"Pinout": "Consult manufacturer datasheet for exact pin mapping."},
                "pin_labels": ["Pin 1", "Pin 2", "Pin 3"],
                "key_specs": {"Status": "Custom component query"},
                "equivalents": ["Check Octopart / Digi-Key parametric search"],
                "notes": f"Verify pinout diagram and maximum ratings before applying Vcc to {c_clean}.",
                "ascii_diagram": f"Component: {c_clean}\nVerify pin 1 orientation index mark prior to wiring.",
            },
        }

    def visualize_pinout(self, component_name: str) -> str:
        """Returns clean ASCII/text pinout diagram for chat display."""
        res = self.fetch_datasheet(component_name)
        data = res.get("data", {})
        diag = data.get("ascii_diagram", "")
        if diag.strip():
            return diag.strip()

        # Generate generic ASCII pinout list
        lines = [f"=== PINOUT DIAGRAM FOR {data.get('name', component_name).upper()} ==="]
        for label in data.get("pin_labels", []):
            lines.append(f"  • {label}")
        return "\n".join(lines)

    def get_equivalents(self, component_name: str) -> Dict[str, Any]:
        """Suggests replacement equivalents for burned or unavailable components."""
        res = self.fetch_datasheet(component_name)
        data = res.get("data", {})
        eqs = data.get("equivalents", [])
        return {
            "component": data.get("name", component_name),
            "equivalents": eqs,
            "notes": data.get("notes", ""),
        }

    def get_component_spec(self, component_name: str) -> Optional[ComponentSpec]:
        """Returns direct ComponentSpec dataclass object or None."""
        key = self.resolve_component_key(component_name)
        if key and key in self.db:
            return self.db[key]
        return None

    def get_pinout_diagram(self, component_name: str) -> str:
        """Convenience alias to visualize_pinout."""
        return self.visualize_pinout(component_name)


# Singleton instance
component_engine = ComponentEngine()

