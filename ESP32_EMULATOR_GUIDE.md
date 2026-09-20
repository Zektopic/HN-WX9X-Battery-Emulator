# ⚡ ESP32 Hardware Smart Battery Emulator Guide

This guide details how to build and flash an **ESP32 Microcontroller Smart Battery Emulator** to emulate a Huawei Desay `HB4593J6ECW` battery over SMBus (I2C Address `0x0B`).

---

## 🛠️ Complete Hardware Wiring Diagram

```text
 ┌───────────────────────────────────────┐             ┌─────────────────────────────┐
 │       ESP32 MICROCONTROLLER           │             │   LAPTOP BATTERY HEADER     │
 │                                       │             │                             │
 │ • GPIO 21 (SDA) ──────[4.7k Resistor]─┼─────────────┼───► Pin 3: SMBus SDA        │
 │ • GPIO 22 (SCL) ──────[4.7k Resistor]─┼─────────────┼───► Pin 4: SMBus SCL        │
 │ • GND           ──────────────────────┼─────────────┼───► Pin 6/7: GND            │
 │ • Vin / 5V      ──────────────────────┼─────────────┼───► 5V Standby / USB 5V     │
 │                                       │             │                             │
 │ • GPIO 34 (ADC) ◄───┐                 │             │                             │
 └─────────────────────┼─────────────────┘             └─────────────────────────────┘
                       │
             ┌─────────┴─────────┐
             │  VOLTAGE DIVIDER  │
             │                   │
             │   18650 Pack (+)  │
             │         │         │
             │     [100k Ω]      │
             │         │         │
             ├─────────┴──► GPIO 34
             │         │         │
             │      [22k Ω]      │
             │         │         │
             │   18650 Pack (-)  │
             └───────────────────┘
```

---

## 📌 Pinout & Component List

### 1. Component List:
1. **ESP32 Development Board** (NodeMCU-32S, ESP32-WROOM-32, or ESP32-C3).
2. **Two Pull-Up Resistors:** `4.7k Ω` (Connected between SDA ➔ 3.3V and SCL ➔ 3.3V).
3. **Voltage Divider Resistors for 12.5V Sensing:**
   * $R_1 = 100\text{k }\Omega$ (Connected to 18650 Positive)
   * $R_2 = 22\text{k }\Omega$ (Connected to GND)
   * **Divider Ratio:** $\frac{100\text{k} + 22\text{k}}{22\text{k}} = 5.545$ (Safely scales 12.5V down to 2.25V for ESP32 ADC).

---

## 💻 How to Flash the ESP32

1. Install **Arduino IDE** (or VS Code + PlatformIO).
2. Add ESP32 Board Support:
   * Go to `File ➔ Preferences ➔ Additional Boards Manager URLs`.
   * Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Open [`esp32_battery_emulator.ino`](file:///home/manupa/18650_battery_mod/esp32_battery_emulator.ino).
4. Select `Board: ESP32 Dev Module` and select your USB COM port.
5. Click **Upload**.

---

## ⚡ How It Unlocks 50W Hybrid Boost

1. **Hardware Power Rail:** Your 3S 18650 battery cells physically supply **12.5 V DC** to the motherboard `P+` and `P-` power pins.
2. **Hardware SMBus Communication:** The ESP32 listens on I2C address `0x0B` and responds to the laptop Embedded Controller with valid SBS v1.1 battery registers (`Voltage = 12.5 V`, `Capacity = 80%`, `Temp = 23 °C`).
3. **Cross-OS Compatibility:** Works 100% in hardware on Linux, Windows, macOS, and in the BIOS without any OS software scripts or kernel patchers!
