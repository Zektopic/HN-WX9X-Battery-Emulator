# 🔋 3S 18650 Laptop Battery Mod Guide & Fast PPT (3.0+ GHz) Automation Toolkit

This toolkit contains all scripts, microcontroller firmware, ACPI DSDT research, and system automation required for the **3S 18650 Battery Mod & 45W Fast PPT (3.0+ GHz) Power Boost** on Huawei MateBook laptops (AMD Ryzen Picasso platform).

---

## 📁 Files Included

| File | Description |
| :--- | :--- |
| **`ec_voltage_patcher.py`** | ⚡ High-speed daemon that injects exact DSDT offsets into EC RAM, locks C-states, and continuously locks the **45W Fast PPT & 65A VRM** limits to sustain **3.0+ GHz** on all cores. |
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

### 2. Why Earlier Patchers Failed:
In the DSDT, the ACPI Battery Extended Info method (`_BIX`) explicitly evaluates:
```asl
If (((BTDV && BTFC) && BTDC))
```
If `BTDC` (0x84) or `BTDV` (0x86) are zero, `_BIX` returns an uninitialized error package. The Linux kernel then drops `energy_full` and `capacity`, causing tools like `btop` and system monitors to hide the battery. The updated patcher writes all offsets simultaneously, restoring full battery telemetry.

---

## ⚡ Unlocking Fast PPT (3.0+ GHz All-Core Clock Speed)

By default, when running on AC without a valid OEM battery, Huawei firmware caps the Ryzen APU to an **18.0W STAPM limit**. Under combined CPU and GPU workloads (e.g. BOINC), this starves the CPU, locking cores to ~2.1 GHz.

The patcher uses `ryzenadj` to override the SMU power table every 5 seconds:
* **STAPM Limit:** Raised from `18W` ➔ **`45W`**
* **Fast PPT Limit:** Raised from `30W` ➔ **`45W`**
* **Slow PPT Limit:** Raised from `25W` ➔ **`45W`**
* **VRM Max Current (EDC):** Raised from `45A` ➔ **`65A`** (unlocks core electrical clamp)
* **VRM Current (TDC):** Raised from `35A` ➔ **`50A`**
* **Thermal Limit (Tctl):** Set to **`95°C`** (typical operating temperature stays cool at ~72°C)

**Result:** All 8 CPU threads boost up to **~3.0+ GHz** simultaneously, even while the Radeon Vega GPU is at 100% load.

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
