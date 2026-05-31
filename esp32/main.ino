/*
 * BioWatch ESP32 — sensor node
 *
 * Wiring
 * ──────
 * DS18B20 (temp)    DATA → GPIO 4, with 4.7 kΩ pull-up to 3.3 V
 * Turbidity sensor  AOUT → GPIO 34 (ADC1_CH6, input-only)
 *                   VCC  → 3.3 V  (SEN0189 works at 3.3 V)
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

// ── Network config — fill in your values ───────────────────────────────────
static const char* WIFI_SSID  = "YOUR_HOTSPOT_SSID";
static const char* WIFI_PASS  = "YOUR_HOTSPOT_PASSWORD";
// Pi Zero W IP on the shared network.
// Find it with:  hostname -I   on the Pi, or check your router DHCP table.
// Tip: set a static IP on the Pi so this never changes.
static const char* PI_HOST    = "192.168.137.XXX";
static const int   PI_PORT    = 8000;
static const char* DEVICE_ID  = "sink_01";

// ── Pins ───────────────────────────────────────────────────────────────────
#define ONE_WIRE_BUS   4     // DS18B20 signal pin
#define TURBIDITY_PIN  34    // Analog turbidity output

// ── Timing ─────────────────────────────────────────────────────────────────
static const unsigned long SEND_INTERVAL_MS = 1000;   // 1 Hz
static const unsigned long WIFI_RETRY_MS    = 5000;

// ── Globals ────────────────────────────────────────────────────────────────
OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);
WebSocketsClient  wsClient;

static bool          wsConnected = false;
static unsigned long lastSend    = 0;

// ── Turbidity ADC → NTU conversion ─────────────────────────────────────────
// SEN0189 at 3.3 V: cleaner water → higher voltage (inverse relationship).
// Linear model — calibrate against known NTU standards for your sensor batch.
//   ~3.0 V → 0 NTU   (clean)
//   ~0.0 V → 100 NTU (very turbid)
float adcToNtu(int raw12bit) {
    float v = raw12bit * 3.3f / 4095.0f;
    float ntu = (3.0f - v) / 3.0f * 100.0f;
    return max(0.0f, ntu);
}

// ── WebSocket event handler ─────────────────────────────────────────────────
void wsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_CONNECTED:
            wsConnected = true;
            Serial.printf("[WS] Connected to ws://%s:%d/ws/%s\n",
                          PI_HOST, PI_PORT, DEVICE_ID);
            break;

        case WStype_DISCONNECTED:
            wsConnected = false;
            Serial.println("[WS] Disconnected — auto-retry enabled");
            break;

        case WStype_TEXT: {
            // Server sends back an ACK with the AMR risk score.
            StaticJsonDocument<256> ack;
            if (deserializeJson(ack, payload) == DeserializationError::Ok) {
                const char* band  = ack["risk"]["band"]       | "?";
                int         score = ack["risk"]["risk_score"]  | -1;
                Serial.printf("[ACK] risk=%d (%s)\n", score, band);
            }
            break;
        }

        default:
            break;
    }
}

// ── setup ───────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    analogReadResolution(12);   // 12-bit ADC on ESP32
    tempSensor.begin();

    // Connect to WiFi
    Serial.printf("Connecting to %s ", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nWiFi OK — IP %s\n", WiFi.localIP().toString().c_str());

    // Start WebSocket client
    String path = String("/ws/") + DEVICE_ID;
    wsClient.begin(PI_HOST, PI_PORT, path.c_str());
    wsClient.onEvent(wsEvent);
    wsClient.setReconnectInterval(3000);
}

// ── loop ────────────────────────────────────────────────────────────────────
void loop() {
    // Keep WebSocket alive (handles ping/pong and reconnection internally)
    wsClient.loop();

    // Reconnect WiFi if it drops
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastRetry = 0;
        if (millis() - lastRetry > WIFI_RETRY_MS) {
            lastRetry = millis();
            Serial.println("WiFi lost — reconnecting...");
            WiFi.reconnect();
        }
        return;
    }

    if (!wsConnected || millis() - lastSend < SEND_INTERVAL_MS)
        return;
    lastSend = millis();

    // Read sensors
    tempSensor.requestTemperatures();
    float tempC = tempSensor.getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C) {
        Serial.println("[WARN] DS18B20 not found — skipping");
        return;
    }
    int   rawAdc = analogRead(TURBIDITY_PIN);
    float ntu    = adcToNtu(rawAdc);

    // Build JSON payload matching the server contract
    StaticJsonDocument<128> doc;
    doc["device_id"]     = DEVICE_ID;
    doc["ts"]            = millis();    // ms since boot; server accepts any epoch ms
    doc["temp_c"]        = serialized(String(tempC, 2));
    doc["turbidity_ntu"] = serialized(String(ntu,   2));

    char buf[128];
    serializeJson(doc, buf);
    wsClient.sendTXT(buf);

    Serial.printf("[SEND] temp=%.2f°C  turb=%.2f NTU  raw=%d\n",
                  tempC, ntu, rawAdc);
}
