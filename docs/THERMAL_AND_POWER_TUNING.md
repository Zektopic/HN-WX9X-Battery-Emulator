# 🌡️ Thermal & Power Tuning Guide

This guide explains how to customize, calibrate, and verify thermal ceilings, frequency limits, and power targets on the **Huawei MateBook D (AMD Ryzen 5 3500U Picasso)**.

---

## 🎯 Tuning Goals & Preset Profiles

Depending on your use case, you can adjust the SMU parameters in [`ec_voltage_patcher.py`](file:///home/manupa/18650_battery_mod/ec_voltage_patcher.py) to achieve your desired balance between clock speeds, temperatures, and fan acoustics.

### Profile Comparison Matrix

| Profile | Fast PPT | Slow PPT | Tctl Temp | Target Clock (All Cores) | Noise & Thermals | Recommended For |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Silent / Cool** | `25 W` | `22 W` | `72 °C` | `~2.40 – 2.50 GHz` | Whisper quiet, ~65–70°C | Office work, quiet environments |
| **Stabilized (Current Default)** | `30 W` | `28 W` | `84 °C` | `~2.75 – 2.90 GHz` | Stable & cool, ~74–76°C | **24/7 BOINC compute (Passive extrusion / Pre-repaste)** |
| **Balanced (Active Fan/Repaste)** | `40 W` | `35 W` | `85 °C` | `~2.95 – 3.05 GHz` | Moderate fan, ~78–82°C | 24/7 compute with PTM7950 or fan on extrusion |
| **Max Turbo / Waterblock** | `45 W` | `45 W` | `95 °C` | `~3.02 – 3.05 GHz` | Maximum fan/loop, ~80–85°C | Full active watercooling loop |

---

## ⚙️ How to Customize Parameters

To modify your operating parameters, edit the `apply_fast_ppt()` function inside [`ec_voltage_patcher.py`](file:///home/manupa/18650_battery_mod/ec_voltage_patcher.py):

```python
def apply_fast_ppt():
    if not os.path.exists(RYZENADJ_BIN):
        return
    try:
        subprocess.run([
            RYZENADJ_BIN,
            "--stapm-limit=28000",        # Sustained power limit (in mW)
            "--fast-limit=30000",         # Short burst power limit (in mW)
            "--slow-limit=28000",         # Sustained package power limit (in mW)
            "--vrm-current=45000",        # TDC limit (in mA)
            "--vrmmax-current=55000",     # EDC limit (in mA)
            "--vrmsoc-current=14000",     # SoC TDC limit (in mA)
            "--vrmsocmax-current=18000",  # SoC EDC limit (in mA)
            "--tctl-temp=84",             # Temperature cap (in °C)
            "--prochot-deassertion-ramp=1"# Instant recovery from 400 MHz trips
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except Exception:
        pass
```

After modifying the file, restart the background service:
```bash
sudo systemctl restart ec-voltage-patcher.service
```

---

## 🛠️ Cooler Modding & Silicon Headroom

### A. What Cooler Upgrades Can Achieve
If you attach an external copper heat-spreader, upgrade to Honeywell PTM7950 phase-change material, or add a high-CFM auxiliary cooling fan:
1. **Zero Thermal Throttling:** The SMU will never encounter temperature-based power clamping.
2. **Permanent Maximum All-Core Boost:** The cores will remain pinned at **~3.05 GHz** indefinitely under full CPU + GPU stress.
3. **VRM Protection:** Cooler motherboard surface temperatures reduce the likelihood of BD PROCHOT pin assertions.

### B. What Cooler Upgrades CANNOT Change
* **The 3.05 GHz Multiplier Cap:** The Ryzen 5 3500U multiplier is locked by AMD. Even at liquid nitrogen temperatures (-196°C), all 4 cores / 8 threads will not exceed **~3.05 GHz** under full multi-core load unless AMD's fused microcode is bypassed.
* **Higher Clocks on Fewer Cores:** If you require **3.40 – 3.70 GHz**, configure your workload (e.g. BOINC) to use **2 cores** instead of all 4 cores. Precision Boost 2 will automatically boost the active cores into the 3.5 GHz tier.

---

## 📊 Live Verification & Telemetry Tools

### 1. Monitor Clocks and SMU Limits
Run the built-in monitor dashboard:
```bash
/home/manupa/18650_battery_mod/monitor_battery.sh
```

### 2. Check Active SMU Register Values
To dump the live hardware power table directly from the SMU:
```bash
sudo /usr/local/bin/ryzenadj -i
```
Look for:
* `STAPM VALUE`: Real-time rolling power consumption.
* `PPT VALUE FAST`: Instantaneous power draw.
* `EDC VALUE VDD`: Electrical current delivered to the cores.
* `THM VALUE CORE`: Current Tctl junction temperature.

### 3. Check All-Core Frequencies Directly
```bash
grep "cpu MHz" /proc/cpuinfo | awk '{printf "Core %d: %.3f GHz\n", NR-1, $4/1000}'
```
