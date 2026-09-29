/*
 * Smart_Sensor - Arduino / C++ Firmware Entrypoint
 */

const int LED_PIN = 13; // Status LED

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("[Smart_Sensor] System Boot Complete.");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);
}
