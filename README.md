# 🔋 3S 18650 Laptop Battery Mod Guide & Fast PPT (3.0+ GHz) Automation Toolkit

This toolkit contains all scripts, microcontroller firmware, ACPI DSDT research, and system automation required for the **3S 18650 Battery Mod & 45W Fast PPT (3.0+ GHz) Power Boost** on Huawei MateBook laptops (AMD Ryzen Picasso platform).

---

## 📁 Files Included

| File | Description |
| :--- | :--- |
| **`docs/ARCHITECTURE_AND_THEORY.md`** | 🧠 **Deep Technical Whitepaper:** Precision Boost 2 architecture, BD PROCHOT electrical pin behavior, DSDT ASL reverse-engineering, and anti-400MHz theory. |
| **`docs/THERMAL_AND_POWER_TUNING.md`** | 🌡️ **Tuning Guide:** Power profiles, thermal caps, cooler modding reality, and live SMU telemetry commands. |
| **`ec_voltage_patcher.py`** | ⚡ High-speed daemon that injects exact DSDT offsets into EC RAM (50ms / 20 Hz loop, zero IRQ 9 waste), locks C-states, and continuously locks the **35W/38W Fast PPT & 70A VRM** limits to sustain **3.0+ GHz** on all cores. |
| **`install_service.sh`** | 🛠️ One-click persistent installer: configures `/etc/modules-load.d/ec_sys.conf`, `/etc/modprobe.d/ec_sys.conf`, and registers `ec-voltage-patcher.service` in systemd to **persist across reboots**. |
| **`uninstall_service.sh`**| 🛑 One-click uninstaller to stop, disable, and clean up the service and kernel configurations. |
| **`monitor_battery.sh`** | 📊 Real-time terminal dashboard displaying battery voltage, capacity, core clock speeds (with 3.0G+ badges), Ryzen SMU power state, and GPU load. |
| **`esp32_battery_emulator.ino`** | 🔌 **ESP32 Arduino C++ Sketch:** Hardware Smart Battery Emulator over SMBus (I2C `0x0B`) with real-time ADC 18650 voltage sensing. |
| **`ESP32_EMULATOR_GUIDE.md`** | 📖 Complete hardware wiring diagram, resistor divider calculations, and flashing instructions. |

---

## 🔍 ACPI DSDT & Embedded Controller (EC) Architecture

Through disassembly of the laptop's ACPI DSDT table (`/sys/firmware/acpi/tables/DSDT`), the exact field layout of the Embedded Controller (`EC0`) battery interface was identified:

### 1. Exact EC RAM Offset Mapping:
```text
Offset   Field   Size    Description
─────────────────────────────────────────────────────────────────────────────
0x80     ACST    1 bit   Bit 0: AC Connected (1 = Mains power online)
         BST1    1 bit   Bit 1: Battery 1 Present (1 = Battery slot active)
0x84     BTDC    16-bit  Battery Design Capacity (3610 mAh)
0x86     BTDV    16-bit  Battery Design Voltage (11400 mV)
0x88     BTFC    16-bit  Battery Full Charge Capacity (3610 mAh)
0x90     BAPV    16-bit  Battery Present Voltage (12500 mV / 12.5 V)
0x92     BARC    16-bit  Battery Remaining Capacity (2888 mAh / 80%)
0x94     BFCC    16-bit  Battery Current Capacity (3610 mAh)
0x9A     BTEM    16-bit  Battery Temperature (2980 = 25.0 °C / 298.15 K)
```

### 2. Why Earlier Patchers Failed & How to Restore `capacity` in BTOP:
In the DSDT, the ACPI Battery Extended Info method (`_BIX`) explicitly evaluates:
```asl
If (((BTDV && BTFC) && BTDC))
```
If `BTDC` (0x84) or `BTDV` (0x86) are zero at boot, `_BIX` fails. The Linux kernel switches to `energy_battery_full_cap_broken_props`, omitting `energy_full` and `capacity`. Because `capacity` is missing, `btop` sets `has_battery = false` and hides the battery widget.

Once the patcher daemon is actively writing the correct offsets to EC RAM, you can force the kernel to re-probe `_BIX` and restore `capacity` and `energy_full` immediately without rebooting:
```bash
echo -n "PNP0C0A:00" | sudo tee /sys/bus/platform/drivers/acpi-battery/unbind
echo -n "PNP0C0A:00" | sudo tee /sys/bus/platform/drivers/acpi-battery/bind
```
*(With the ESP32 hardware emulator connected to SMBus, this is handled automatically before boot).*

---

## ⚡ Unlocking Fast PPT (3.0+ GHz All-Core Clock Speed)

By default, when running on AC without a valid OEM battery, Huawei firmware caps the Ryzen APU to an **18.0W STAPM limit**. Under combined CPU and GPU workloads (e.g. BOINC), this starves the CPU, locking cores to ~2.1 GHz.

The patcher continuously optimizes the SMU power table and GPU DPM states every 3 seconds:
* **STAPM Limit:** Set to **`35W`** (sustained continuous compute matching active fan + extrusion cooling)
* **Fast PPT Limit:** Set to **`38W`** (burst compute budget)
* **Slow PPT Limit:** Set to **`35W`**
* **VRM Max Current (EDC):** Set to **`70A`** (pins boost clocks up to **~2.74 – 3.16 GHz**)
* **VRM Current (TDC):** Set to **`55A`**
* **Thermal Limit (Tctl):** Set to **`84°C`** (runs cool at ~66–68°C with external fan, eliminating 400 MHz drops)
* **PROCHOT Deassertion Ramp:** Set to **`1`** (collapses 400 MHz recovery from 30 seconds to 1 millisecond)
* **GPU VRAM (MCLK) Lock:** Pinned permanently to **`1.2 GHz`** (State 3 - DDR4-2400) for maximum OpenCL compute bandwidth

**Result:** All 8 CPU threads stay pinned at **~2.74 – 3.16 GHz** with **0% throttle drops**, while GPU VRAM is locked to **1.2 GHz** permanently.

---

## 🚀 Installation & Usage

### 1. One-Click Persistent Installation (Survives Reboots)
Run the installer once as root:
```bash
cd /home/manupa/18650_battery_mod
sudo ./install_service.sh
```
This automatically:
1. Writes `/etc/modules-load.d/ec_sys.conf` so `ec_sys` loads at boot.
2. Writes `/etc/modprobe.d/ec_sys.conf` so `write_support=1` is permanent.
3. Installs and starts `ec-voltage-patcher.service` in systemd.

### 2. Real-Time Monitoring
Launch the live terminal monitor:
```bash
/home/manupa/18650_battery_mod/monitor_battery.sh
```

### 3. Service Management
```bash
# Check service status
systemctl status ec-voltage-patcher.service

# Restart service
sudo systemctl restart ec-voltage-patcher.service

# Uninstall service
sudo /home/manupa/18650_battery_mod/uninstall_service.sh
```
