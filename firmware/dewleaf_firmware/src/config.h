#pragma once

#include <Arduino.h>

namespace cfg {

// Identity
constexpr const char* DEVICE_ID = "dewleaf-node1-bench";
constexpr const char* FIRMWARE_VERSION = "0.3.0-phase0";

// I2C
constexpr uint8_t PIN_I2C_SDA = 8;
constexpr uint8_t PIN_I2C_SCL = 9;

// 1-Wire DS18B20 bus
constexpr uint8_t PIN_ONEWIRE = 4;

// ADC1-only soil probes
constexpr uint8_t PIN_SOIL_A = 1;
constexpr uint8_t PIN_SOIL_B = 2;

// Flow meter
constexpr uint8_t PIN_FLOW_PULSE = 5;
constexpr float FLOW_PULSES_PER_LITER = 450.0f; // calibrate per D0.1

// MOSFET channels (low-side)
constexpr uint8_t PIN_CH_PELTIER = 10;
constexpr uint8_t PIN_CH_FAN = 11;
constexpr uint8_t PIN_CH_VIB_A = 12;
constexpr uint8_t PIN_CH_VIB_B = 13;
constexpr uint8_t PIN_CH_VALVE_FLUSH = 14;
constexpr uint8_t PIN_CH_VALVE_DRIP = 21;

// SD SPI
constexpr uint8_t PIN_SD_CS = 41;
constexpr uint8_t PIN_SD_MOSI = 40;
constexpr uint8_t PIN_SD_SCK = 39;
constexpr uint8_t PIN_SD_MISO = 38;

// Optional status LED
constexpr uint8_t PIN_STATUS_LED = 48;

// Safety / physics guardrails
constexpr float FROST_GUARD_C = 1.5f;
constexpr float NUCLEATION_DELTA_T_C = 0.8f;
constexpr float SOIL_TARGET_MIN_PCT = 60.0f;
constexpr float SOIL_TARGET_MAX_PCT = 72.0f;
constexpr float MAX_PELTIER_WH_PER_NIGHT = 25.0f;

// Timing
constexpr uint32_t SENSOR_PERIOD_MS = 10000;
constexpr uint32_t LOG_PERIOD_MS = 10000;
constexpr uint32_t ENERGY_PERIOD_MS = 5000;
constexpr uint32_t STATE_PERIOD_MS = 1000;
constexpr uint32_t WDT_TIMEOUT_S = 30;

// Exploration (Phase 0 only)
constexpr bool ENABLE_EPSILON_GREEDY = true;
constexpr float EPSILON = 0.20f;

// First flush / shedding defaults
constexpr uint32_t FIRST_FLUSH_MS = 4000;
constexpr uint32_t SHED_BURST_MS = 2500;
constexpr uint32_t SHED_INTERVAL_MS = 45000;
constexpr uint32_t DRIP_PULSE_MS = 3000;

// Paths
constexpr const char* LOG_PATH = "/dewleaf_log.csv";

}  // namespace cfg
