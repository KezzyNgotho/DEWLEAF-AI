#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>
#include <RTClib.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>
#include <math.h>

#include "config.h"
#include "dewleaf_policy.h"

// Hardware clients
Adafruit_BME280 bme;
Adafruit_INA219 ina219;
RTC_DS3231 rtc;
OneWire oneWire(cfg::PIN_ONEWIRE);
DallasTemperature ds18b20(&oneWire);

static bool hasBME = false;
static bool hasINA = false;
static bool hasRTC = false;
static bool hasSD = false;
static bool hasDS = false;

enum class SystemState : uint8_t {
  IDLE_DAY = 0,
  PASSIVE_COOLING,
  NUCLEATION_ASSIST,
  PRE_DAWN_SHEDDING,
  FIRST_FLUSH_PURGE,
  ROOT_MICRO_DOSE,
  SAFETY_FAULT
};

struct SensorSnapshot {
  uint32_t ms = 0;
  String isoTime;
  float airTempC = NAN;
  float rhPct = NAN;
  float pressureHpa = NAN;
  float dewPointC = NAN;
  float spineTempC = NAN;
  float soilTempC = NAN;
  float soilA_pct = NAN;
  float soilB_pct = NAN;
  float busVoltageV = NAN;
  float currentMa = NAN;
  float powerMw = NAN;
  float whTotal = 0.0f;
  float flowLTotal = 0.0f;
  float flowLWindow = 0.0f;
};

struct ActuatorState {
  bool peltier = false;
  bool fan = false;
  bool vibA = false;
  bool vibB = false;
  bool valveFlush = false;
  bool valveDrip = false;
  uint16_t actionId = 0;
};

static SensorSnapshot sensors;
static ActuatorState act;
static SystemState state = SystemState::IDLE_DAY;
static String nightId = "night-unknown";

static volatile uint32_t flowPulses = 0;
static uint32_t lastFlowPulses = 0;
static uint32_t lastSensorMs = 0;
static uint32_t lastLogMs = 0;
static uint32_t lastEnergyMs = 0;
static uint32_t lastStateMs = 0;
static uint32_t lastShedMs = 0;
static uint32_t stateEnteredMs = 0;
static float energyWhAcc = 0.0f;
static uint32_t nightCounter = 0;

portMUX_TYPE flowMux = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR onFlowPulse() {
  portENTER_CRITICAL_ISR(&flowMux);
  flowPulses++;
  portEXIT_CRITICAL_ISR(&flowMux);
}

static float dewPointC(float tempC, float rh) {
  if (isnan(tempC) || isnan(rh) || rh <= 0.0f) return NAN;
  // Magnus formula
  constexpr float a = 17.62f;
  constexpr float b = 243.12f;
  float gamma = (a * tempC) / (b + tempC) + logf(rh / 100.0f);
  return (b * gamma) / (a - gamma);
}

static float soilPctFromAdc(uint16_t raw) {
  // Calibrate these in D0.1. Default maps dry=2800, wet=1200.
  constexpr float dry = 2800.0f;
  constexpr float wet = 1200.0f;
  float pct = (dry - static_cast<float>(raw)) / (dry - wet) * 100.0f;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

static String isoNow() {
  if (hasRTC) {
    DateTime now = rtc.now();
    char buf[32];
    snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d",
             now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
    return String(buf);
  }
  unsigned long s = millis() / 1000;
  char buf[24];
  snprintf(buf, sizeof(buf), "uptime-%lu", s);
  return String(buf);
}

static int currentHour() {
  if (hasRTC) return rtc.now().hour();
  return static_cast<int>((millis() / 3600000UL) % 24UL);
}

static void setActuator(uint8_t pin, bool on) {
  digitalWrite(pin, on ? HIGH : LOW);
}

static void applyActuators() {
  // Safety interlock: never run peltier without fan.
  if (act.peltier && !act.fan) act.fan = true;

  setActuator(cfg::PIN_CH_PELTIER, act.peltier);
  setActuator(cfg::PIN_CH_FAN, act.fan);
  setActuator(cfg::PIN_CH_VIB_A, act.vibA);
  setActuator(cfg::PIN_CH_VIB_B, act.vibB);
  setActuator(cfg::PIN_CH_VALVE_FLUSH, act.valveFlush);
  setActuator(cfg::PIN_CH_VALVE_DRIP, act.valveDrip);
}

static void allActuatorsOff() {
  act = {};
  applyActuators();
}

static void ensureSdHeader() {
  if (!hasSD) return;
  if (SD.exists(cfg::LOG_PATH)) return;
  File f = SD.open(cfg::LOG_PATH, FILE_WRITE);
  if (!f) return;
  f.println("timestamp_ms,iso_time,night_id,state,action_id,air_temp_c,rh_pct,pressure_hpa,dew_point_c,spine_temp_c,soil_temp_c,soil_a_pct,soil_b_pct,bus_v,current_ma,power_mw,wh_total,flow_l_total,flow_l_window,peltier,fan,vib_a,vib_b,valve_flush,valve_drip");
  f.close();
}

static void logCsv() {
  const char* stateName =
      state == SystemState::IDLE_DAY ? "IDLE_DAY" :
      state == SystemState::PASSIVE_COOLING ? "PASSIVE_COOLING" :
      state == SystemState::NUCLEATION_ASSIST ? "NUCLEATION_ASSIST" :
      state == SystemState::PRE_DAWN_SHEDDING ? "PRE_DAWN_SHEDDING" :
      state == SystemState::FIRST_FLUSH_PURGE ? "FIRST_FLUSH_PURGE" :
      state == SystemState::ROOT_MICRO_DOSE ? "ROOT_MICRO_DOSE" : "SAFETY_FAULT";

  char line[512];
  snprintf(line, sizeof(line),
           "%lu,%s,%s,%s,%u,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.2f,%.2f,%.6f,%.4f,%.4f,%d,%d,%d,%d,%d,%d",
           static_cast<unsigned long>(sensors.ms),
           sensors.isoTime.c_str(),
           nightId.c_str(),
           stateName,
           act.actionId,
           sensors.airTempC, sensors.rhPct, sensors.pressureHpa, sensors.dewPointC,
           sensors.spineTempC, sensors.soilTempC, sensors.soilA_pct, sensors.soilB_pct,
           sensors.busVoltageV, sensors.currentMa, sensors.powerMw, sensors.whTotal,
           sensors.flowLTotal, sensors.flowLWindow,
           act.peltier, act.fan, act.vibA, act.vibB, act.valveFlush, act.valveDrip);

  Serial.println(line);
  if (hasSD) {
    File f = SD.open(cfg::LOG_PATH, FILE_APPEND);
    if (f) {
      f.println(line);
      f.close();
    }
  }
}

static void emitJsonLog() {
  StaticJsonDocument<512> doc;
  doc["device_id"] = cfg::DEVICE_ID;
  doc["fw"] = cfg::FIRMWARE_VERSION;
  doc["ts_ms"] = sensors.ms;
  doc["iso_time"] = sensors.isoTime;
  doc["night_id"] = nightId;
  doc["state"] = static_cast<int>(state);
  doc["action_id"] = act.actionId;
  doc["air_temp_c"] = sensors.airTempC;
  doc["rh_pct"] = sensors.rhPct;
  doc["dew_point_c"] = sensors.dewPointC;
  doc["spine_temp_c"] = sensors.spineTempC;
  doc["soil_a_pct"] = sensors.soilA_pct;
  doc["soil_b_pct"] = sensors.soilB_pct;
  doc["wh_total"] = sensors.whTotal;
  doc["flow_l_total"] = sensors.flowLTotal;
  doc["flow_l_window"] = sensors.flowLWindow;
  serializeJson(doc, Serial);
  Serial.println();
}

static void readSensors() {
  sensors.ms = millis();
  sensors.isoTime = isoNow();

  if (hasBME) {
    sensors.airTempC = bme.readTemperature();
    sensors.rhPct = bme.readHumidity();
    sensors.pressureHpa = bme.readPressure() / 100.0f;
    sensors.dewPointC = dewPointC(sensors.airTempC, sensors.rhPct);
  }

  if (hasDS) {
    ds18b20.requestTemperatures();
    float t0 = ds18b20.getTempCByIndex(0);
    float t1 = ds18b20.getTempCByIndex(1);
    if (t0 > -100 && t0 < 125) sensors.spineTempC = t0;
    if (t1 > -100 && t1 < 125) sensors.soilTempC = t1;
  }

  // ADC1-only pins by config.
  sensors.soilA_pct = soilPctFromAdc(analogRead(cfg::PIN_SOIL_A));
  sensors.soilB_pct = soilPctFromAdc(analogRead(cfg::PIN_SOIL_B));

  if (hasINA) {
    sensors.busVoltageV = ina219.getBusVoltage_V();
    sensors.currentMa = ina219.getCurrent_mA();
    sensors.powerMw = ina219.getPower_mW();
  }

  uint32_t pulses;
  portENTER_CRITICAL(&flowMux);
  pulses = flowPulses;
  portEXIT_CRITICAL(&flowMux);
  uint32_t delta = pulses - lastFlowPulses;
  lastFlowPulses = pulses;
  sensors.flowLWindow = static_cast<float>(delta) / cfg::FLOW_PULSES_PER_LITER;
  sensors.flowLTotal = static_cast<float>(pulses) / cfg::FLOW_PULSES_PER_LITER;
}

static void updateEnergy() {
  uint32_t now = millis();
  if (lastEnergyMs == 0) { lastEnergyMs = now; return; }
  uint32_t dt = now - lastEnergyMs;
  lastEnergyMs = now;
  if (isnan(sensors.powerMw)) return;
  energyWhAcc += (sensors.powerMw / 1000.0f) * (static_cast<float>(dt) / 3600000.0f);
  sensors.whTotal = energyWhAcc;
}

static void enterState(SystemState next, uint16_t actionId) {
  if (state == next && act.actionId == actionId) return;
  state = next;
  act.actionId = actionId;
  stateEnteredMs = millis();
}

static bool isNightWindow(int hour) {
  return (hour >= 18 || hour < 7);
}

static bool isPreDawnWindow(int hour) {
  return (hour >= 4 && hour < 7); // tune with RTC/seasonal schedule
}

static void runStateMachine() {
  int hour = currentHour();
  float avgSoil = NAN;
  if (!isnan(sensors.soilA_pct) && !isnan(sensors.soilB_pct)) avgSoil = (sensors.soilA_pct + sensors.soilB_pct) / 2.0f;
  else avgSoil = sensors.soilA_pct;

  // Frost guard: protect spine and stop nucleation assist.
  if (!isnan(sensors.spineTempC) && sensors.spineTempC <= cfg::FROST_GUARD_C) {
    act.peltier = false;
    act.fan = false;
  }

  // Peltier nightly energy cap.
  bool peltierAllowed = sensors.whTotal < 1000000.0f; // placeholder total; nightly cap enforced by action policy in Phase 0 logger.

  if (!isnan(sensors.spineTempC) && sensors.spineTempC < -2.0f) {
    enterState(SystemState::SAFETY_FAULT, 900);
    allActuatorsOff();
    return;
  }

  DewContext dctx = {
    isnan(sensors.airTempC)?20:sensors.airTempC, isnan(sensors.rhPct)?70:sensors.rhPct,
    isnan(sensors.pressureHpa)?1012:sensors.pressureHpa, isnan(sensors.dewPointC)?15:sensors.dewPointC,
    isnan(sensors.spineTempC)?18:sensors.spineTempC,
    isnan(sensors.soilA_pct)?60:sensors.soilA_pct, isnan(sensors.soilB_pct)?60:sensors.soilB_pct,
    isnan(sensors.busVoltageV)?12.4f:sensors.busVoltageV,
    0.0f, 50.0f, 0.0f, 0.0f, // wind/cloud/vpd/et0 - wire in if available
    sinf(2*PI*hour/24.0f), cosf(2*PI*hour/24.0f), isPreDawnWindow(hour)?1.0f:0.0f
  };
  uint16_t rec = dew_select_action(dctx, 100);
  bool explore = cfg::ENABLE_EPSILON_GREEDY && (random(100) < static_cast<int>(cfg::EPSILON * 100));
  if (explore) rec = (random(2)==0) ? 301 : 200;

  if (isPreDawnWindow(hour)) {
    enterState(SystemState::PRE_DAWN_SHEDDING, rec);
    act.valveFlush = false; act.valveDrip = false; act.peltier = false; act.fan = false;
    if (millis() - lastShedMs >= cfg::SHED_INTERVAL_MS) lastShedMs = millis();
    bool shedding = (millis() - lastShedMs) < cfg::SHED_BURST_MS;
    act.vibA = shedding && (rec==300||rec==302||rec==310||rec==301);
    act.vibB = shedding && (rec==300||rec==302||rec==310);
    if (rec==310) { act.peltier = peltierAllowed; act.fan = act.peltier; }
    applyActuators();
    return;
  }

  if (isNightWindow(hour)) {
    float deltaT = (!isnan(sensors.airTempC) && !isnan(sensors.dewPointC)) ? (sensors.airTempC - sensors.dewPointC) : NAN;
    bool nearDewPoint = !isnan(deltaT) && deltaT <= cfg::NUCLEATION_DELTA_T_C;
    bool wantNuc = (rec==200||rec==201||rec==310) && nearDewPoint && peltierAllowed;
    if (wantNuc) { enterState(SystemState::NUCLEATION_ASSIST, rec); act.peltier=true; act.fan=true; }
    else { enterState(SystemState::PASSIVE_COOLING, 100); act.peltier=false; act.fan=false; }
    act.vibA=false; act.vibB=false; act.valveFlush=false; act.valveDrip=false;
    applyActuators();
    return;
  }

  // Daytime: first flush after sunrise window, then micro-dose if dry.
  if (hour >= 7 && hour < 9) {
    enterState(SystemState::FIRST_FLUSH_PURGE, 400);
    bool flushing = (millis() - stateEnteredMs) < cfg::FIRST_FLUSH_MS;
    act.valveFlush = flushing;
    act.valveDrip = false;
    act.peltier = false; act.fan = false; act.vibA = false; act.vibB = false;
    applyActuators();
    return;
  }

  if (!isnan(avgSoil) && avgSoil < cfg::SOIL_TARGET_MIN_PCT) {
    enterState(SystemState::ROOT_MICRO_DOSE, 500);
    bool dosing = (millis() - stateEnteredMs) < cfg::DRIP_PULSE_MS;
    act.valveDrip = dosing;
    act.valveFlush = false;
    act.peltier = false; act.fan = false; act.vibA = false; act.vibB = false;
    applyActuators();
    return;
  }

  enterState(SystemState::IDLE_DAY, 0);
  allActuatorsOff();
}

static void updateNightId() {
  int hour = currentHour();
  static int lastHour = -1;
  if (lastHour == -1) lastHour = hour;
  if (lastHour < 18 && hour >= 18) {
    nightCounter++;
  }
  lastHour = hour;
  if (hasRTC) {
    DateTime now = rtc.now();
    char buf[24];
    snprintf(buf, sizeof(buf), "%04d%02d%02d", now.year(), now.month(), now.day());
    nightId = String("night-") + buf;
  } else {
    nightId = String("night-") + String(nightCounter);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(cfg::PIN_CH_PELTIER, OUTPUT);
  pinMode(cfg::PIN_CH_FAN, OUTPUT);
  pinMode(cfg::PIN_CH_VIB_A, OUTPUT);
  pinMode(cfg::PIN_CH_VIB_B, OUTPUT);
  pinMode(cfg::PIN_CH_VALVE_FLUSH, OUTPUT);
  pinMode(cfg::PIN_CH_VALVE_DRIP, OUTPUT);
  pinMode(cfg::PIN_STATUS_LED, OUTPUT);
  allActuatorsOff();

  analogReadResolution(12);

  Wire.begin(cfg::PIN_I2C_SDA, cfg::PIN_I2C_SCL);
  hasBME = bme.begin(0x76) || bme.begin(0x77);
  hasINA = ina219.begin();
  hasRTC = rtc.begin();
  if (hasRTC && rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  ds18b20.begin();
  hasDS = ds18b20.getDeviceCount() > 0;

  SPI.begin(cfg::PIN_SD_SCK, cfg::PIN_SD_MISO, cfg::PIN_SD_MOSI, cfg::PIN_SD_CS);
  hasSD = SD.begin(cfg::PIN_SD_CS);
  ensureSdHeader();

  pinMode(cfg::PIN_FLOW_PULSE, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(cfg::PIN_FLOW_PULSE), onFlowPulse, RISING);

  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = cfg::WDT_TIMEOUT_S * 1000,
    .idle_core_mask = (1 << portNUM_PROCESSORS) - 1,
    .trigger_panic = true,
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);

  randomSeed(esp_random());
  stateEnteredMs = millis();
  Serial.println("timestamp_ms,iso_time,night_id,state,action_id,air_temp_c,rh_pct,pressure_hpa,dew_point_c,spine_temp_c,soil_temp_c,soil_a_pct,soil_b_pct,bus_v,current_ma,power_mw,wh_total,flow_l_total,flow_l_window,peltier,fan,vib_a,vib_b,valve_flush,valve_drip");
}

void loop() {
  esp_task_wdt_reset();
  uint32_t now = millis();

  if (now - lastSensorMs >= cfg::SENSOR_PERIOD_MS) {
    lastSensorMs = now;
    readSensors();
    updateNightId();
  }
  if (now - lastEnergyMs >= cfg::ENERGY_PERIOD_MS) {
    updateEnergy();
  }
  if (now - lastStateMs >= cfg::STATE_PERIOD_MS) {
    lastStateMs = now;
    runStateMachine();
  }
  if (now - lastLogMs >= cfg::LOG_PERIOD_MS) {
    lastLogMs = now;
    logCsv();
  }
}
