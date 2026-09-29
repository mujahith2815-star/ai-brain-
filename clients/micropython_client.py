"""
MicroPython Client Skeleton for ESP32 / Raspberry Pi Pico W nodes.
Communicates with P.H.A.S.S Network Broker via lightweight TCP / MQTT socket.
"""

import time
try:
    import network
except ImportError:
    network = None
import socket
import json

WIFI_SSID = "HomeNetwork_2.4G"
WIFI_PASS = "secure_wifi_password"
BROKER_IP = "192.168.1.100"
BROKER_PORT = 1883
AUTH_TOKEN = "phass_omni_secret_token_2026"
CLIENT_ID = "esp32_sensor_node"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Wi-Fi connected:", wlan.ifconfig())


def run_client():
    connect_wifi()
    s = socket.socket()
    s.connect((BROKER_IP, BROKER_PORT))
    
    # Handshake
    auth_msg = {
        "type": "auth",
        "token": AUTH_TOKEN,
        "client_id": CLIENT_ID,
        "client_type": "esp32",
        "signal_strength": -48
    }
    s.send((json.dumps(auth_msg) + "\n").encode())
    print("Connected to P.H.A.S.S Broker.")

    while True:
        # Telemetry loop
        telemetry = {
            "type": "telemetry",
            "client_id": CLIENT_ID,
            "data": {
                "temp_c": 26.5,
                "free_mem": 112000,
                "status": "online"
            }
        }
        s.send((json.dumps(telemetry) + "\n").encode())
        time.sleep(5)


if __name__ == "__main__":
    run_client()
