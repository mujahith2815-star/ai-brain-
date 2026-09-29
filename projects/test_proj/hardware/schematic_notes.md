# Hardware Schematic & Wiring Notes: test_proj

## 1. Power Distribution Network (PDN)
- **Primary Input**: 5V DC (USB or external supply).
- **Regulated Rails**: 
  - +5.0V Rail: Main power bus.
  - +3.3V Rail: Clean digital logic and sensor bus.
- **Decoupling Strategy**: 
  - 100nF (0.1µF) ceramic capacitors placed within 5mm of every IC power pin.
  - 47µF bulk electrolytic capacitor across power entry.

## 2. Pinout & GPIO Allocation Table
| Subsystem / Peripheral | Controller Pin | Function / Mode | Active State | Notes |
|------------------------|----------------|-----------------|--------------|-------|
| Status LED             | GPIO 2 / Pin 13| OUTPUT (PWM)    | Active HIGH  | 220Ω current limiting resistor |
| System Reset           | /RESET         | INPUT_PULLUP    | Active LOW   | 10kΩ pull-up to Vcc |

## 3. Circuit Safety & Protection
- Reverse polarity protection diode (1N4007 or Schottky 1N5819) at DC input.
- Flyback suppression diode across all inductive actuators (relays, solenoids, motors).
- Pull-down resistors (10kΩ) on all MOSFET gate drive lines to prevent floating gate conduction.
