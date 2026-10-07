# 🌡️ Thermal & Power Tuning Guide

This guide explains how to customize, calibrate, and verify thermal ceilings, frequency limits, and power targets on the **Huawei MateBook D (AMD Ryzen 5 3500U Picasso)**.

---

## 🎯 Tuning Goals & Preset Profiles

Depending on your use case, you can adjust the SMU parameters in [`ec_voltage_patcher.py`](file:///home/manupa/18650_battery_mod/ec_voltage_patcher.py) to achieve your desired balance between clock speeds, temperatures, and fan acoustics.

### Profile Comparison Matrix

| Profile | Fast PPT | Slow PPT | Tctl Temp | Target Clock (All Cores) | Noise & Thermals | Recommended For |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Silent / Cool** | `25 W` | `22 W` | `72 °C` | `~2.40 – 2.50 GHz` | Whisper quiet, ~65–70°C | Office work, quiet environments |
| **Stabilized 65W** | `30 W` | `28 W` | `84 °C` | `~2.40 – 2.89 GHz` | Passive block or stock 65W adapter | 24/7 compute with OEM 65W charger |
| **Active Fan + 100W PD (Current)** | `38 W` | `35 W` | `88 °C` | `~2.72 – 3.16 GHz` | Cool, ~68–78°C with external fan | **24/7 BOINC (CPU+GPU) + Frigate with 100W charger** |
| **Max Turbo / Waterblock** | `45 W` | `45 W` | `95 °C` | `~3.05 GHz (All Core)` | Maximum fan/loop, ~75–80°C | Full active watercooling loop |

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
            "--stapm-limit=35000",        # Sustained power limit (35W in mW)
            "--fast-limit=38000",         # Short burst power limit (38W in mW)
            "--slow-limit=35000",         # Sustained package power limit (35W in mW)
            "--vrm-current=55000",        # TDC limit (55A in mA)
            "--vrmmax-current=70000",     # EDC limit (70A in mA)
            "--vrmsoc-current=14000",     # SoC TDC limit (14A in mA)
            "--vrmsocmax-current=18000",  # SoC EDC limit (18A in mA)
            "--tctl-temp=88",             # Temperature cap (in °C - prevents false 400MHz trips)
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

### C. Real-World Measured Results: Honeywell PTM7950 + VRM Pads
With Honeywell PTM7950 applied directly to the bare APU die and dedicated thermal pads on the motherboard VRM MOSFETs:

| Metric | Stock Paste (Pre-Mod) | Honeywell PTM7950 + VRM Pads | Delta / Improvement |
| :--- | :---: | :---: | :--- |
| **28W Sustained Tctl** | ~71.0 °C | **61.0 °C** | **-10.0 °C cooler** |
| **35W/38W Sustained Tctl** | ~79.5 °C (thermal trip risk) | **70.1 °C** | **-9.4 °C cooler (18°C headroom)** |
| **GPU Edge Temp (OpenCL)** | ~77.0 °C | **70.0 °C** | **-7.0 °C cooler** |
| **GPU Core Clock (sclk)** | ~733 MHz | **914 MHz** | **+181 MHz higher sustained boost** |
| **CPU All-Core Clock (8T)** | ~2.50 – 2.62 GHz | **~2.75 – 3.14 GHz** | **Consistent PB2 Turbo (~3.14 GHz peak)** |
| **400 MHz Drops (15s sample)**| Frequent BD PROCHOT trips | **0 drops** | **100% eliminated** |

### D. Empirical 20-Minute Head-to-Head: Flat 35W (Option A) vs. 38W Burst (Option B)
To find the absolute optimal 24/7 operating profile, both profiles were tested back-to-back under continuous 100% compute load for 10 minutes each (5,917 high-resolution 100ms samples per phase):

| Metric | Option A: Flat 35W Capped (70A EDC) | Option B: 38W Burst (75A EDC) | Winner & Hardware Takeaway |
| :--- | :---: | :---: | :--- |
| **400 MHz Throttle Drops** | **0 episodes (0.0s)** | 1 episode (517s in clamp) | **Option A (Flawless 100% stability)** |
| **Sustained System Avg Clock** | **2,848.3 MHz** | 893.3 MHz (collapsed) | **Option A (+1,955 MHz higher throughput)** |
| **Average Tctl Temperature** | **71.2 °C** | 52.8 °C (idle during clamp)| **Option A (Stable linear heat dissipation)** |
| **Peak Tctl Temperature** | **82.0 °C** | 78.8 °C | **Option A (Plenty of margin below 88°C)** |
| **Average GPU Temperature** | **70.8 °C** | 52.3 °C | **Option A (Pegged OpenCL compute)** |

#### 🔬 Engineering Finding: Why Option A Wins
The Huawei MateBook D motherboard's VRM controller / PWM circuitry features a hardware Over-Current Protection (OCP) trip threshold around **~70A–72A**. 
* **Option B (38W Fast PPT):** Even with 75A requested from SMU, transient 38W bursts force the VRMs past their physical OCP threshold, latching the hardware PROCHOT pin LOW and stalling the APU at 400 MHz for 86% of the time.
* **Option A (35W Flat Fast PPT):** Keeping Fast PPT identical to Slow PPT (`--fast-limit=35000` = `--slow-limit=35000`) completely prevents overshoot, keeping current strictly within the VRM's continuous delivery envelope. This delivers **0 throttle drops**, completely smooth 24/7 operation, and peak multi-core compute throughput.

### E. GPU-Biased Compute Profile (GPU @ ~950 MHz, CPU @ 2.10 GHz Base)

For workloads heavily reliant on GPU compute (e.g., PrimeGrid Genefer19 OpenCL + Frigate NVR VA-API decoding), the monolithic APU power budget can be strategically partitioned:

#### 1. The Monolithic 35W Power Trade-Off
On AMD Picasso 12nm, the CPU cores and Vega 8 iGPU share the same package power envelope:
* When CPU Precision Boost 2 is unconstrained, 8 CPU threads boost to **~2.85–3.10 GHz**, drawing **~24W** of power. This leaves only **~11W** for the GPU, forcing `sclk` to fluctuate between 700–900 MHz.
* By disabling CPU boost (`/sys/devices/system/cpu/cpufreq/boost = 0`), all 8 CPU threads are locked to their rock-solid **2.10 GHz Base Clock**, drawing only **~11–12W**.
* This frees up **~23–24W** of package power, allowing the Vega 8 GPU to stay continuously pinned at **~942–950 MHz** (DPM State 1) under 100% compute load.

#### 2. Measured Live Telemetry (GPU ~950 MHz Profile)
| Metric | Stock APU Balancing | GPU ~950 MHz Biased Profile | System Benefit |
| :--- | :---: | :---: | :--- |
| **GPU Clock (`sclk`)** | 733 – 800 MHz fluctuating | **942.0 MHz pegged** | **+25% OpenCL throughput** |
| **GPU VRAM (`mclk`)** | Dynamic downclocking | **1,200.0 MHz pinned (State 3)** | **Zero memory bus latency** |
| **CPU All-Core Clock** | 2.75 – 3.05 GHz | **2,095.9 MHz locked (2.10 GHz Base)**| **Rock-solid stability, 0 drops** |
| **APU Junction (`Tctl`)** | ~71.0 – 74.0 °C | **64.5 °C** | **40.5 °C headroom below 105°C TjMax** |
| **GPU Edge Temp** | ~70.0 °C | **64.0 °C** | **Ultra-cool silicon temperatures** |
| **400 MHz Drops** | 0 drops | **0 drops** | **100% glitch-free continuous compute** |

#### 3. Automation via `ec_voltage_patcher.py`
The patcher automatically enforces this balance every 3.0 seconds:
```python
# 1. Lock APU to flat 35W and set min/max gfxclk to 950 MHz
subprocess.run([
    RYZENADJ_BIN,
    "--stapm-limit=35000",
    "--fast-limit=35000",
    "--slow-limit=35000",
    "--vrm-current=55000",
    "--vrmmax-current=70000",
    "--tctl-temp=88",
    "--min-gfxclk=950",
    "--max-gfxclk=950",
    "--prochot-deassertion-ramp=1"
])

# 2. Lock CPU boost to 0 (locks CPU at 2.10 GHz Base)
with open("/sys/devices/system/cpu/cpufreq/boost", "w") as f:
    f.write("0")
```

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

### 4. Comprehensive Sensor & Junction Telemetry (SensorView)
The globally installed [`sensorview`](file:///usr/local/bin/sensorview) tool provides real-time terminal output or reports for all CPU cores, k10temp junction (`Tctl`), AMDGPU core clocks, and memory:
```bash
# Display live sensor tree in terminal
sensorview sensors

# Dump diagnostic report file
sensorview report

# Inspect hardware system overview
sensorview info
```

