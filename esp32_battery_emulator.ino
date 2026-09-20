/*
 * 🔋 ESP32 / Arduino SBS v1.1 Smart Battery Emulator
 * 
 * Emulates a Huawei Desay HB4593J6ECW Smart Battery on SMBus I2C Address 0x0B.
 * Connects directly to Laptop Battery Header (SDA, SCL, GND).
 *
 * Hardware Wiring:
 *  - ESP32 GPIO 21 (SDA)  --> Laptop Battery Header SDA (with 4.7k pull-up resistor to 3.3V)
 *  - ESP32 GPIO 22 (SCL)  --> Laptop Battery Header SCL (with 4.7k pull-up resistor to 3.3V)
 *  - ESP32 GND            --> Laptop Battery Header GND & 18650 Pack GND
 *  - ESP32 Vin / 5V       --> Laptop 5V Standby / USB / Buck Converter (3.3V - 5V)
 *  - ESP32 GPIO 34 (ADC)  --> Voltage Divider from 18650 Pack + (100k / 22k Divider)
 */

#include <Wire.h>

#define I2C_SLAVE_ADDR 0x0B  // Standard SBS v1.1 Smart Battery I2C Address (7-bit 0x0B)
#define ADC_PIN        34    // GPIO 34 for voltage sensing

// Global Battery Telemetry Variables
volatile uint16_t live_voltage_mv = 12500;  // Default 12.5V (12500 mV)
volatile uint16_t live_capacity_pct = 80;   // Default 80% Capacity
volatile uint16_t live_temp_k = 2962;       // Default 23.0°C (296.2 K)
volatile uint16_t full_cap_mah = 3610;       // Design Full Capacity (3610 mAh)
volatile uint16_t remaining_cap_mah = 2880;  // Remaining Capacity (2880 mAh)
volatile int16_t  live_current_ma = 0;       // Current (0 mA)

uint8_t current_reg = 0x00;

void setup() {
  Serial.begin(115200);
  Serial.println("Starting ESP32 Smart Battery SBS v1.1 Emulator...");

  // Configure ADC pin for 18650 Pack Voltage Sensing
  analogReadResolution(12); // 12-bit ADC (0 - 4095)
  pinMode(ADC_PIN, INPUT);

  // Initialize I2C in Slave Mode at Address 0x0B
  // GPIO 21 = SDA, GPIO 22 = SCL, 100 kHz Clock Speed
  Wire.begin(I2C_SLAVE_ADDR, 21, 22, 100000);
  Wire.onRequest(onRequestEvent);
  Wire.onReceive(onReceiveEvent);

  Serial.println("ESP32 listening on SMBus I2C Address 0x0B!");
}

void loop() {
  // Read physical 18650 cell voltage via Resistor Divider (100k / 22k)
  // Divider Ratio: (100k + 22k) / 22k = 5.545
  int raw_adc = analogRead(ADC_PIN);
  float measured_v = (raw_adc / 4095.0) * 3.3 * 5.545;
  
  if (measured_v > 6.0) { // Only update if valid battery connected
    live_voltage_mv = (uint16_t)(measured_v * 1000.0);
  } else {
    live_voltage_mv = 12500; // Fallback to 12.5V
  }

  delay(500); // Sample voltage twice per second
}

// Executed when Laptop EC sends a register command byte over SMBus
void onReceiveEvent(int bytesReceived) {
  if (Wire.available()) {
    current_reg = Wire.read(); // Store requested SBS Command Register
  }
}

// Executed when Laptop EC requests data response for the command byte
void onRequestEvent() {
  uint16_t response_word = 0x0000;

  switch (current_reg) {
    case 0x08: // Temperature() (0.1 K)
      response_word = live_temp_k;
      break;
    case 0x09: // Voltage() (mV)
      response_word = live_voltage_mv;
      break;
    case 0x0A: // Current() (mA)
      response_word = (uint16_t)live_current_ma;
      break;
    case 0x0D: // RelativeStateOfCharge() (%)
      response_word = live_capacity_pct;
      break;
    case 0x0F: // RemainingCapacity() (mAh)
      response_word = remaining_cap_mah;
      break;
    case 0x10: // FullChargeCapacity() (mAh)
      response_word = full_cap_mah;
      break;
    case 0x18: // DesignCapacity() (mAh)
      response_word = full_cap_mah;
      break;
    case 0x19: // DesignVoltage() (mV)
      response_word = 11400; // 11.4 V
      break;
    case 0x1A: // SpecificationInfo()
      response_word = 0x0031; // SBS v1.1 compliance
      break;
    default:
      response_word = 0x0000;
      break;
  }

  // Send 16-bit Little-Endian Word Response over SMBus
  Wire.write((uint8_t)(response_word & 0xFF));
  Wire.write((uint8_t)((response_word >> 8) & 0xFF));
}
