"""
test_proj - Main Firmware Entrypoint (MicroPython / CircuitPython)
Hardware Co-Pilot generated template
"""
import time

LED_PIN = 2  # Default status LED pin

def setup():
    print("[test_proj] Hardware initialized.")
    # On MicroPython:
    # from machine import Pin
    # led = Pin(LED_PIN, Pin.OUT)

def loop():
    print("[test_proj] System loop ticking...")
    time.sleep(1)

if __name__ == '__main__':
    setup()
    while True:
        loop()
