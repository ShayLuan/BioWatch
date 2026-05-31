/*
 * BioWatch ESP32 — sensor node
 *
 * Wiring
 * ──────
 * DS18B20 (temp)    DATA → GPIO 4  (breakout board has pull-up built in)
 * Turbidity sensor  AOUT → GPIO 34 (ADC1_CH6, input-only pin)
 *                   VCC  → 5 V   (sensor requires 5 V; ESP32 ADC clips at 3.3 V)
 *
 * Required libraries (Arduino Library Manager)
 * ─────────────────────────────────────────────
 *  WebSockets         by Markus Sattler  ≥ 2.4.0
 *  ArduinoJson        by Benoit Blanchon ≥ 7
 *  OneWire            by Paul Stoffregen
 *  DallasTemperature  by Miles Burton
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ── Network config ──────────────────────────────────────────────────────────
static const char* WIFI_SSID  = "FBI Surveillance Van";
static const char* WIFI_PASS  = "8c21ab92";
static const char* PI_HOST    = "192.168.43.119";
static const int   PI_PORT    = 8000;
static const char* DEVICE_ID  = "sink_01";

// ── Pins ────────────────────────────────────────────────────────────────────
#define ONE_WIRE_BUS   4    // DS18B20 data — breakout pull-up is sufficient
#define TURBIDITY_PIN  34   // Turbidity sensor analog out

// ── Timing ──────────────────────────────────────────────────────────────────
static const unsigned long SEND_INTERVAL_MS = 200;     // 5 Hz
static const unsigned long WIFI_RETRY_MS    = 5000;

// ── Globals ──────────────────────────────────────────────────────────────────
OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);
WebSocketsClient  wsClient;

static bool          wsConnected = false;
static unsigned long lastSend    = 0;

// ── Turbidity: average 10 samples then convert to NTU ───────────────────────
// Sensor VCC = 5 V. Formula: DFRobot SEN0189 / TS-300B wiki.
// ESP32 ADC caps at 3.3 V, so we map raw directly to the 5 V scale.
float readTurbidityNTU() {
    long sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += analogRead(TURBIDITY_PIN);
        delay(5);
    }
    float v = (sum / 10.0f) * (5.0f / 4095.0f);  // raw → 5 V scale

    if (v >= 4.2f) return 0.0f;     // clean water (sensor near max output)
    if (v <= 2.5f) return 3000.0f;  // beyond formula range

    float ntu = -1120.4f * v * v + 5742.3f * v - 4352.9f;
    return constrain(ntu, 0.0f, 3000.0f);
}

// ── WebSocket events ─────────────────────────────────────────────────────────
void wsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            wsConnected = true;
            Serial.printf("[WS] Connected to ws://%s:%d/ws/%s\n",
                          PI_HOST, PI_PORT, DEVICE_ID);
            break;

        case WStype_DISCONNECTED:
            wsConnected = false;
            Serial.printf("[WS] Disconnected (code %u) — retrying\n", (unsigned)length);
            break;

        case WStype_TEXT: {
            JsonDocument ack;
            if (deserializeJson(ack, payload) == DeserializationError::Ok) {
                const char* band  = ack["risk"]["band"]      | "?";
                int         score = ack["risk"]["risk_score"] | -1;
                Serial.printf("[ACK] risk=%d (%s)\n", score, band);
            }
            break;
        }

        case WStype_ERROR:
            Serial.printf("[WS] Error: %s\n", payload ? (char*)payload : "unknown");
            break;

        default: break;
    }
}

// ── setup ────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    analogReadResolution(12);
    analogSetPinAttenuation(TURBIDITY_PIN, ADC_11db); // extend ADC range to 0–3.3 V
    tempSensor.begin();

    int found = tempSensor.getDeviceCount();
    Serial.printf("DS18B20 found: %d\n", found);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("Connecting to %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nWiFi OK — %s\n", WiFi.localIP().toString().c_str());

    String path = String("/ws/") + DEVICE_ID;
    wsClient.begin(PI_HOST, PI_PORT, path.c_str());
    wsClient.onEvent(wsEvent);
    wsClient.setReconnectInterval(3000);
    wsClient.enableHeartbeat(15000, 3000, 2);
}

// ── loop ─────────────────────────────────────────────────────────────────────
void loop() {
    wsClient.loop();

    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastRetry = 0;
        if (millis() - lastRetry > WIFI_RETRY_MS) {
            lastRetry = millis();
            Serial.println("WiFi lost — reconnecting");
            WiFi.reconnect();
        }
        return;
    }

    if (!wsConnected || millis() - lastSend < SEND_INTERVAL_MS)
        return;
    lastSend = millis();

    tempSensor.requestTemperatures();
    float tempC = tempSensor.getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C) {
        Serial.println("[WARN] DS18B20 read failed");
        return;
    }

    float ntu = readTurbidityNTU();

    JsonDocument doc;
    doc["device_id"]     = DEVICE_ID;
    doc["ts"]            = millis();
    doc["temp_c"]        = tempC;
    doc["turbidity_ntu"] = ntu;

    char buf[128];
    serializeJson(doc, buf);
    wsClient.sendTXT(buf);

    Serial.printf("[SEND] temp=%.2f°C  turb=%.2f NTU\n", tempC, ntu);
}
