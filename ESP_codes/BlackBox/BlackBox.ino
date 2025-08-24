#include <SoftwareSerial.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Arduino.h>
#include <Update.h>
#include <iarduino_OLED_txt.h>
#include <iarduino_I2C_SHT.h>
#include <iarduino_I2C_DSL.h>  //   Подключаем библиотеку для работы с датчиком освещённости I2C-flash (Digital Sensor Light).
#include <iarduino_I2C_pH.h>   //   Подключаем библиотеку для работы с pH-метром I2C-flash.
#include <iarduino_I2C_TDS.h>  // Подключаем библиотеку для работы с TDS/EC-метром I2C-flash.
iarduino_I2C_TDS tds(0x5D);
iarduino_I2C_pH sensor(0x6A);
iarduino_I2C_DSL dsl;
extern const uint8_t SmallFont[];
iarduino_I2C_SHT sht;
iarduino_OLED_txt myOLED(0x3C);   // Адрес дисплея
SoftwareSerial mySerial(14, 12);  // RX, TX
#define TURBIDITY_PIN 33
// Пины реле
const int relayTempPin = 15;
const int relayHumPin = 16;
const int relayCyclePin = 13;
const char* ssid = "";
const char* password = "";
const char* updateServerUrl = "http://10.1.10.144:5000/update";
const char* firmwareUrl = "http://10.1.10.144:5000/firmware1";
const char* statusUrl = "http://10.1.10.144:5000/firmware/status";
const char* serverUrl = "http://10.1.10.144:5000/sensor/data";

float val_t = 25.0;
float TDS = 0;
float EC = 0;
// Пины ёмкостных датчиков
const int soilPins[5] = { 36, 39, 32, 35, 34 };
// Показания влажности почвы
int soilMoisture[5];
// Переменные для цикличного реле
// unsigned long previousMillis = 0;
bool relayCycleState = false;

unsigned long previousMillis = 0;
const long interval = 60000;
unsigned long previousMillisData = 0;
const long intervalData = 600000;  // Интервал отправки данных

unsigned long rebootInterval = 30UL * 60UL * 1000UL; // 30 минут в миллисекундах
unsigned long lastRebootTime = 0;


void setup() {

  delay(500);
  Serial.begin(9600);
  mySerial.begin(9600);
  while (!Serial) { ; }  // * Ждём завершения инициализации шины UART.
  dsl.begin(&Wire);      //   Инициируем работу с датчиком освещённости, указав ссылку на объект для работы с шиной I2C на которой находится модуль (по умолчанию &Wire).
  // Инициализация дисплея и датчика
  sht.begin(&Wire);
  tds.begin(&Wire);
  myOLED.begin(&Wire);
  myOLED.setFont(SmallFont);
  myOLED.clrScr();
  sensor.begin(&Wire);
  // Инициализация пинов реле
  pinMode(relayTempPin, OUTPUT);
  pinMode(relayHumPin, OUTPUT);
  pinMode(relayCyclePin, OUTPUT);
  pinMode(TURBIDITY_PIN, INPUT);

  digitalWrite(relayTempPin, LOW);
  digitalWrite(relayHumPin, LOW);
  digitalWrite(relayCyclePin, LOW);

  for (int i = 0; i < 5; i++) {
    pinMode(soilPins[i], INPUT);
  }
  /// Подключение к WiFi
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWi-Fi connection failed.");
  }
  if (checkForUpdates()) {
    if (performUpdate()) {
      sendUpdateStatus(true);
    } else {
      sendUpdateStatus(false);
    }
  } else {
    Serial.println("No updates available.");
  }
  lastRebootTime = millis();
}

void loop() {
  
  myOLED.clrScr();
  if (millis() - lastRebootTime >= rebootInterval) {
    ESP.restart(); // Перезагрузка ESP32
  }
  // ----- Чтение CO2 -----
  byte cmd[9] = { 0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79 };
  mySerial.write(cmd, 9);
  int CO2 = 0;
  if (mySerial.available()) {
    byte response[9];
    mySerial.readBytes(response, 9);
    if (response[0] == 0xFF && response[1] == 0x86) {
      CO2 = (response[2] << 8) + response[3];
    }
  }

  // ----- Чтение температуры и влажности -----
  float temperature = sht.getTem();
  float humidity = sht.getHum();
  val_t = temperature;
  /*
    // ----- Управление реле по температуре -----
    if (temperature >25) {
        digitalWrite(relayTempPin, LOW);
        myOLED.setCursor(0, 4);
      myOLED.print("Heat: OFF");
    } else if (temperature < 23) {
        digitalWrite(relayTempPin, HIGH);
        myOLED.setCursor(0, 4);
      myOLED.print("Heat: ON");
    }
*/
  // ----- Управление реле по влажности -----
  if (temperature < 24) {
    digitalWrite(relayHumPin, LOW);
    /*myOLED.setCursor(0, 5);
        myOLED.print("Vent: OFF");*/
  } else if (temperature > 25) {
    digitalWrite(relayHumPin, HIGH);
    /* myOLED.setCursor(0, 5);
        myOLED.print("Vent: ON");*/
  }

  // ----- Цикличное реле -----
  /*unsigned long currentMillis = millis();
    if (relayCycleState && currentMillis - previousMillis >= 300000) { // 1 минута включено
        digitalWrite(relayCyclePin, LOW);
        relayCycleState = false;
        previousMillis = currentMillis;
    } else if (!relayCycleState && currentMillis - previousMillis >= 3600000) { // 3 минуты выключено
        digitalWrite(relayCyclePin, HIGH);
        relayCycleState = true;
        previousMillis = currentMillis;
    }
      */
  ////Water pH
  Serial.print("Кислотность = ");   //
  Serial.print(sensor.getPH(), 1);  //   Выводим водородный показатель жидкости с 1 знаком после запятой.
  Serial.print(" pH.\r\n");
  /////TDS EC
  tds.set_t(val_t);                                          // Указываем текущую температуру жидкости.
  Serial.print((String) "EC=" + tds.getEC() + "мСм/см, ");   // Выводим удельную электропроводность жидкости приведённую к опорной температуре.
  Serial.print((String) "TDS=" + tds.getTDS() + "ppm\r\n");  // Выводим количество растворённых твёрдых веществ в жидкости.
  TDS = tds.getTDS();
  EC = tds.getEC();

  /////Soil MOsiture
  Serial.println("Soil Moisture Levels:");
  for (int i = 0; i < 5; i++) {
    int raw = analogRead(soilPins[i]);
    soilMoisture[i] = map(raw, 3800, 2200, 0, 100);        // Больше влажность — меньше сигнал map(raw, MIN, MAX, 0, 100)
    soilMoisture[i] = constrain(soilMoisture[i], 0, 100);  // Ограничение от 0 до 100
    Serial.print("Sensor ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(soilMoisture[i]);
    Serial.println(" %");
  }

  //Мутность воды
  int rawValue = analogRead(TURBIDITY_PIN);  // Значение от 0 до 4095 (у ESP32 12-битный ADC)
  float voltage = rawValue * (5 / 4095.0);   // Преобразуем в напряжение (если используешь делитель, умножь на 2)
                                             // Примерная калибровка — настроить под свой датчик:
  float turbidityNTU = (voltage < 2.5) ? (3000 - (voltage * 1200)) : 0;

  Serial.print("Raw: ");
  Serial.print(rawValue);
  Serial.print(" | Voltage: ");
  Serial.print(voltage, 2);
  Serial.print(" V | Turbidity: ");
  Serial.print(turbidityNTU, 1);
  Serial.println(" NTU");


  // ----- OLED дисплей -----
  myOLED.setCursor(0, 3);
  if (WiFi.status() == WL_CONNECTED) {
    myOLED.print("Wi-Fi: OK ");
    myOLED.print(WiFi.RSSI());
    myOLED.print(" dBm");
  } else {
    myOLED.print("Wi-Fi: FAIL");
  }
  myOLED.setCursor(0, 0);
  myOLED.print("T:");
  myOLED.print(temperature);
  myOLED.print(" C");

  myOLED.setCursor(60, 0);
  myOLED.print("Humi:");
  myOLED.print(humidity);
  myOLED.print(" %");
  myOLED.setCursor(0, 1);
  myOLED.print("Turbid:");
  myOLED.print(turbidityNTU);
  myOLED.print(" NTU");

  myOLED.setCursor(0, 2);
  myOLED.print("CO2: ");
  myOLED.print((int16_t )CO2);
  myOLED.print(" ppm");
  /*if(relayCycleState==false)
    {myOLED.setCursor(0, 4);
    myOLED.print("Light: OFF");}
    else if(relayCycleState==true)
    {myOLED.setCursor(0, 4);
        myOLED.print("Light: ON");}*/

  myOLED.setCursor(0, 4);
  myOLED.print("S1: ");
  myOLED.print((int8_t)soilMoisture[0]);
  myOLED.setCursor(45, 4);
  myOLED.print("S2: ");
  myOLED.print((int8_t)soilMoisture[1]);
  myOLED.setCursor(80, 4);
  myOLED.print("S3: ");
  myOLED.print((int8_t)soilMoisture[2]);
  myOLED.setCursor(0, 5);
  myOLED.print("S4: ");
  myOLED.print((int8_t)soilMoisture[3]);
  myOLED.setCursor(40, 5);
  myOLED.print("S5: ");
  myOLED.print((int8_t)soilMoisture[4]);
  myOLED.setCursor(0, 6);
  myOLED.print("Water pH: ");
  myOLED.print(sensor.getPH());
  myOLED.setCursor(0, 7);
  myOLED.print("TDS: ");
  myOLED.print(TDS);
  myOLED.setCursor(65, 7);
  myOLED.print("EC: ");
  myOLED.print(EC);

  unsigned long currentMillisdata = millis();
  if (currentMillisdata - previousMillisData >= intervalData) {
    previousMillisData = currentMillisdata;
    ESP.restart();
    Serial.println(ESP.getFreeHeap());
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Reconnecting...");
    WiFi.begin(ssid, password);
    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 10000) {
      delay(500);
      Serial.print(".");
    }
    Serial.println();
  }


  if (WiFi.status() == WL_CONNECTED) {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;

      // Проверка наличия обновлений
      if (checkForUpdates()) {
        if (performUpdate()) {
          sendUpdateStatus(true);
        } else {
          sendUpdateStatus(false);
        }
      } else {
        Serial.println("No updates available.");
      }
    }
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    for (int i = 0; i < 5; i++) {
      int raw = analogRead(soilPins[i]);
      soilMoisture[i] = map(raw, 3800, 2200, 0, 100);        // Больше влажность — меньше сигнал map(raw, MIN, MAX, 0, 100)
      soilMoisture[i] = constrain(soilMoisture[i], 0, 100);  // Ограничение от 0 до 100
    }
    // Создаем JSON
    StaticJsonDocument<200> jsonDoc;
    jsonDoc["device_id"] = "esp1";  // Идентификатор устройства
    jsonDoc["soil1"] = soilMoisture[0];
    jsonDoc["soil2"] = soilMoisture[1];
    jsonDoc["soil3"] = soilMoisture[2];
    jsonDoc["soil4"] = soilMoisture[3];
    jsonDoc["soil5"] = soilMoisture[4];
    jsonDoc["ph_level"] = (sensor.getPH(), 1);
    jsonDoc["ec"] = tds.getEC();
    jsonDoc["tds"] = tds.getTDS();
    jsonDoc["turbidity"] = turbidityNTU;
    jsonDoc["co2"] = CO2;
    jsonDoc["temperature"] = temperature;
    jsonDoc["humidity"] = humidity;
    jsonDoc["light_level"] = dsl.getLux();



    String jsonString;
    serializeJson(jsonDoc, jsonString);
    Serial.println(jsonString);

    int httpResponseCode = http.POST(jsonString);
    Serial.println(httpResponseCode);
    if (httpResponseCode <= 0) {
      Serial.println("HTTP error, restarting...");
      delay(1000);
      ESP.restart();
    }

    http.end();
  }
  delay(5000);
}

bool checkForUpdates() {
  HTTPClient http;
  http.begin(updateServerUrl);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(200);
    deserializeJson(doc, payload);

    if (doc.containsKey("update_available") && doc["update_available"] == true) {
      Serial.println("Update is available.");
      http.end();
      return true;
    }
  }
  http.end();
  return false;
}

bool performUpdate() {
  HTTPClient http;
  http.begin(firmwareUrl);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    int contentLength = http.getSize();
    if (contentLength <= 0) {
      Serial.println("Invalid content length.");
      http.end();
      return false;
    }

    bool canBegin = Update.begin(contentLength);
    if (!canBegin) {
      Serial.println("Not enough space to begin OTA.");
      http.end();
      return false;
    }

    WiFiClient* stream = http.getStreamPtr();
    int written = Update.writeStream(*stream);

    if (written == contentLength) {
      Serial.println("Written : " + String(written) + " successfully");
    } else {
      Serial.println("Written only : " + String(written) + "/" + String(contentLength) + ". Retry?");
      http.end();
      return false;
    }

    if (Update.end()) {
      Serial.println("OTA done!");
      if (Update.isFinished()) {
        Serial.println("Update successfully completed. Rebooting.");
        ESP.restart();
      } else {
        Serial.println("Update not finished? Something went wrong!");
      }
    } else {
      Serial.println("Error Occurred. Error #: " + String(Update.getError()));
      http.end();
      return false;
    }
  } else {
    Serial.println("Firmware download failed.");
    http.end();
    return false;
  }
  http.end();
  return true;
}

void sendUpdateStatus(bool success) {
  HTTPClient http;
  http.begin(statusUrl);
  http.addHeader("Content-Type", "application/json");

  String statusMessage = success ? "{\"status\":\"success\"}" : "{\"status\":\"failure\"}";
  int httpCode = http.POST(statusMessage);

  if (httpCode == HTTP_CODE_OK) {
    Serial.println("Update status sent successfully.");
  } else {
    Serial.println("Failed to send update status.");
  }
  http.end();
}