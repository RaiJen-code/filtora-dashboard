#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

// ============================================================
//  PIN MAPPING
// ============================================================
#define DHTPIN     33   // DHT11 data pin
#define DHTTYPE    DHT11

#define MQ135_PIN  34   // MQ135 – kualitas udara (CO2, NH3, NOx)
#define MQ2_PIN    35   // MQ2   – asap, LPG, CO
#define MQ5_PIN    32   // MQ5   – LPG, gas alam
#define GP2Y_PIN   36   // GP2Y1010 – debu (PM2.5 proxy)
#define GP2Y_LED    2   // LED infrared GP2Y1010

// ============================================================
//  ⚠️  GANTI DISINI: WiFi
// ============================================================
const char* ssid     = "NAMA_WIFI_ANDA";       // <-- ganti
const char* password = "PASSWORD_WIFI_ANDA";   // <-- ganti

// ============================================================
//  MQTT — EMQX Cloud
// ============================================================
const char* mqtt_broker   = "r10a6eff.ala.asia-southeast1.emqxsl.com";
const int   mqtt_port     = 8883;
const char* mqtt_username = "apaaja";
const char* mqtt_password = "123456789";
const char* mqtt_clientid = "esp32_filtora_01";

// Topics  (harus cocok dengan filtora_subscriber.py)
const char* TOPIC_MQ135  = "udara/sensor/mq135";
const char* TOPIC_MQ2    = "udara/sensor/mq2";
const char* TOPIC_MQ5    = "udara/sensor/mq5";
const char* TOPIC_PM25   = "udara/sensor/pm25";
const char* TOPIC_PM10   = "udara/sensor/pm10";
const char* TOPIC_TEMP   = "udara/sensor/temperature";
const char* TOPIC_HUMID  = "udara/sensor/humidity";
const char* TOPIC_COMBO  = "udara/sensor/combined";

// ============================================================
//  ROOT CA — DigiCert Global Root CA (EMQX Cloud)
// ============================================================
const char* root_ca = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDrzCCApegAwIBAgIQCDvgVpBCRrGhdWrJWZHHSjANBgkqhkiG9w0BAQUFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBD
QTAeFw0wNjExMTAwMDAwMDBaFw0zMTExMTAwMDAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IENBMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4jvhEXLeqKTTo1eqUKKPC3eQyaKl7hLOllsB
CSDMAZOnTjC3U/dDxGkAV53ijSLdhwZAAIEJzs4bg7/fzTtxRuLWZscFs3YnFo97
nh6Vfe63SKMI2tavegw5BmV/Sl0fvBf4q77uKNd0f3p4mVmFaG5cIzJLv07A6Fpt
43C/dxC//AH2hdmoRBBYMql1GNXRor5H4idq9Joz+EkIYIvUX7Q6hL+hqkpMfT7P
T19sdl6gSzeRntwi5m3OFBqOasv+zbMUZBfHWymeMr/y7vrTC0LUq7dBMtoM1O/4
gdW7jVg/tRvoSSiicNoxBN33shbyTApOB6jtSj1etX+jkMOvJwIDAQABo2MwYTAO
BgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUA95QNVbR
TLtm8KPiGxvDl7I90VUwHwYDVR0jBBgwFoAUA95QNVbRTLtm8KPiGxvDl7I90VUw
DQYJKoZIhvcNAQEFBQADggEBAMucN6pIExIK+t1EnE9SsPTfrgT1eXkIoyQY/Esr
hMAtudXH/vTBH1jLuG2cenTnmCmrEbXjcKChzUyImZOMkXDiqw8cvpOp/2PV5Adg
06O/nVsJ8dWO41P0jmP6P6fbtGbfYmbW0W5BjfIttep3Sp+dWOIrWcBAI+0tKIJF
PnlUkiaY4IBIqDfv8NZ5YBberOgOzW6sRBc4L0na4UU+Krk2U886UAb3LujEV0ls
YSEY1QSteDwsOoBrp+uvFRTp2InBuThs4pFsiv9kuXclVzDAGySj4dzp30d8tbQk
CAUw7C29C79Fv1C5qfPrmAESrciIxpg0X40KPMbp1ZWVbd4=
-----END CERTIFICATE-----
)EOF";

// ============================================================
//  GLOBAL
// ============================================================
WiFiClientSecure wifiClient;
PubSubClient     mqttClient(wifiClient);
DHT              dht(DHTPIN, DHTTYPE);

unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL = 5000; // ms

// ============================================================
//  WiFi
// ============================================================
void connectWiFi() {
  Serial.printf("\n[WiFi] Menghubungkan ke '%s'", ssid);
  WiFi.begin(ssid, password);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++tries > 40) {         // timeout 20 detik
      Serial.println("\n[WiFi] Gagal! Restart...");
      ESP.restart();
    }
  }
  Serial.printf("\n[WiFi] OK  IP: %s\n", WiFi.localIP().toString().c_str());
}

// ============================================================
//  NTP — tunggu sampai waktu valid
// ============================================================
void syncNTP() {
  configTime(7 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("[NTP] Sinkronisasi waktu");
  struct tm timeinfo;
  int tries = 0;
  while (!getLocalTime(&timeinfo) || timeinfo.tm_year < (2024 - 1900)) {
    delay(1000);
    Serial.print(".");
    if (++tries > 30) {         // timeout 30 detik
      Serial.println("\n[NTP] Gagal sync, lanjut tanpa waktu akurat.");
      return;
    }
  }
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
  Serial.printf("\n[NTP] OK  Waktu: %s WIB\n", buf);
}

// ============================================================
//  MQTT
// ============================================================
void connectMQTT() {
  mqttClient.setServer(mqtt_broker, mqtt_port);
  mqttClient.setKeepAlive(60);
  // Gunakan setCACert untuk verifikasi TLS.
  // Jika gagal koneksi, ganti dengan wifiClient.setInsecure();
  wifiClient.setCACert(root_ca);

  Serial.printf("[MQTT] Menghubungkan ke %s:%d ...\n", mqtt_broker, mqtt_port);
  int tries = 0;
  while (!mqttClient.connected()) {
    if (mqttClient.connect(mqtt_clientid, mqtt_username, mqtt_password)) {
      Serial.println("[MQTT] Terhubung!");
    } else {
      Serial.printf("[MQTT] Gagal (state=%d), coba lagi...\n", mqttClient.state());
      delay(3000);
      if (++tries > 10) {
        Serial.println("[MQTT] Tidak bisa konek setelah 10x. Restart...");
        ESP.restart();
      }
    }
  }
}

// ============================================================
//  TIMESTAMP
//  Format: YYYY-MM-DDTHH-MM-SS_millis
//  Kompatibel dengan firebase.js formatTimestamp()
//  dan filtora_subscriber.py timestamp_key
// ============================================================
String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo) || timeinfo.tm_year < (2024 - 1900)) {
    // NTP belum sync — gunakan uptime sebagai fallback key unik
    unsigned long ms = millis();
    return "2000-01-01T00-00-00_" + String(ms);
  }
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H-%M-%S", &timeinfo);
  // Tambahkan millis() % 10000 agar unik jika >1 pembacaan per detik
  return String(buf) + "_" + String(millis() % 10000);
}

// ============================================================
//  SENSOR BACA
// ============================================================
float readMQ(int pin) {
  int   adc = analogRead(pin);
  return (adc / 4095.0f) * 1000.0f;   // 0–1000 ppm skala kasar
}

float readPM25() {
  // GP2Y1010AU0F  — LED ON → baca ADC → LED OFF
  digitalWrite(GP2Y_LED, LOW);
  delayMicroseconds(280);
  int raw = analogRead(GP2Y_PIN);
  delayMicroseconds(40);
  digitalWrite(GP2Y_LED, HIGH);
  delayMicroseconds(9680);

  float volt    = raw * (3.3f / 4095.0f);
  float density = (0.17f * volt - 0.1f) * 1000.0f;  // µg/m³
  return max(density, 0.0f);
}

// ============================================================
//  PUBLISH HELPER
// ============================================================
void publishSensor(const char* topic, const char* sensorType,
                   float value, const String& ts) {
  StaticJsonDocument<256> doc;
  doc["device_id"]   = "esp32_filtora";
  doc["location"]    = "Lab FILTORA";
  doc["timestamp"]   = ts;
  doc["sensor_type"] = sensorType;
  doc["value"]       = round(value * 100.0f) / 100.0f;  // 2 desimal

  char buf[256];
  serializeJson(doc, buf);
  bool ok = mqttClient.publish(topic, buf, /*retained=*/false);
  Serial.printf("  [%s] %.2f %s\n", sensorType, value, ok ? "✓" : "✗ GAGAL");
}

void publishCombined(float mq135, float mq2, float mq5,
                     float pm25, float pm10, float temp, float hum,
                     const String& ts) {
  StaticJsonDocument<512> doc;
  doc["device_id"] = "esp32_filtora";
  doc["location"]  = "Lab FILTORA";
  doc["timestamp"] = ts;

  JsonObject s = doc.createNestedObject("sensors");
  s["mq135"]       = round(mq135 * 100) / 100.0f;
  s["mq2"]         = round(mq2   * 100) / 100.0f;
  s["mq5"]         = round(mq5   * 100) / 100.0f;
  s["pm25"]        = round(pm25  * 100) / 100.0f;
  s["pm10"]        = round(pm10  * 100) / 100.0f;
  s["temperature"] = round(temp  * 100) / 100.0f;
  s["humidity"]    = round(hum   * 100) / 100.0f;

  char buf[512];
  serializeJson(doc, buf);
  bool ok = mqttClient.publish(TOPIC_COMBO, buf, false);
  Serial.printf("  [combined] %s\n", ok ? "✓ terkirim" : "✗ GAGAL");
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n==============================");
  Serial.println("  FILTORA — ESP32 Air Monitor");
  Serial.println("==============================");

  pinMode(GP2Y_LED, OUTPUT);
  digitalWrite(GP2Y_LED, HIGH);   // LED infrared OFF (active-low)
  dht.begin();

  connectWiFi();
  syncNTP();       // Tunggu waktu valid sebelum mulai publish
  connectMQTT();

  Serial.println("\n[READY] Mulai baca sensor setiap 5 detik...\n");
}

// ============================================================
//  LOOP
// ============================================================
void loop() {
  // Reconnect WiFi jika putus
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Terputus, reconnect...");
    connectWiFi();
  }

  // Reconnect MQTT jika putus
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  // Publish setiap PUBLISH_INTERVAL ms
  if (millis() - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = millis();

    // -- Baca semua sensor --
    float mq135 = readMQ(MQ135_PIN);
    float mq2   = readMQ(MQ2_PIN) - 300.0f;  // offset kalibrasi MQ2
    if (mq2 < 0) mq2 = 0;
    float mq5   = readMQ(MQ5_PIN);
    float pm25  = readPM25();
    float pm10  = pm25 * 1.6f;               // estimasi PM10 dari PM2.5
    float temp  = dht.readTemperature();
    float hum   = dht.readHumidity();

    // Validasi DHT — jika NaN, pakai nilai default aman
    if (isnan(temp)) { temp = 25.0f; Serial.println("[WARN] DHT temp NaN, pakai 25°C"); }
    if (isnan(hum))  { hum  = 50.0f; Serial.println("[WARN] DHT hum NaN, pakai 50%"); }

    String ts = getTimestamp();

    Serial.printf("\n[DATA] %s\n", ts.c_str());

    // Publish individual topics
    publishSensor(TOPIC_MQ135, "mq135",       mq135, ts);
    publishSensor(TOPIC_MQ2,   "mq2",         mq2,   ts);
    publishSensor(TOPIC_MQ5,   "mq5",         mq5,   ts);
    publishSensor(TOPIC_PM25,  "pm25",        pm25,  ts);
    publishSensor(TOPIC_PM10,  "pm10",        pm10,  ts);
    publishSensor(TOPIC_TEMP,  "temperature", temp,  ts);
    publishSensor(TOPIC_HUMID, "humidity",    hum,   ts);

    // Publish combined (satu pesan berisi semua sensor)
    publishCombined(mq135, mq2, mq5, pm25, pm10, temp, hum, ts);

    Serial.println("------------------------------");
  }
}
