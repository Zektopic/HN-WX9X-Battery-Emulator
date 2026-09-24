#!/usr/bin/env python3
"""
EC Voltage, Capacity & Anti-400MHz Fast PPT Patcher Daemon
Solves both battery emulation and the 400 MHz throttling issue:
  1. EC RAM Injection (Exact Huawei DSDT Layout):
     - Offset 0x80: ACST | BST1 (0x03: AC connected & Battery present)
     - Offset 0x84: BTDC (Design Capacity: 3610 mAh)
     - Offset 0x86: BTDV (Design Voltage: 11400 mV)
     - Offset 0x88: BTFC (Full Charge Capacity: 3610 mAh)
     - Offset 0x90: BAPV (Present Voltage: 12500 mV / 12.5V)
     - Offset 0x92: BARC (Remaining Capacity: 2888 mAh / 80%)
     - Offset 0x94: BFCC (3610 mAh)
     - Offset 0x9A: BTEM (Temperature: 2980 = 25.0 C)
  2. CPU C-State Latency Lock:
     - Locks /dev/cpu_dma_latency to 0 to eliminate C-state sleep drops.
  3. Anti-400MHz & Ryzen Fast PPT Boost:
     - Sets --prochot-deassertion-ramp=1 (instantly recovers from BD PROCHOT trips).
     - Enforces stable 38W Fast PPT & 65A VRM limits to prevent VRM overheating.
     - Sets --tctl-temp=85 to prevent motherboard thermal sensor trips.
"""

import time
import struct
import os
import sys
import signal
import subprocess

# Ensure ec_sys with write_support is loaded
os.system("modprobe ec_sys write_support=1 2>/dev/null")

ec_paths = ["/sys/kernel/debug/ec/ec0/io", "/sys/kernel/debug/ec/ec_sys"]
ec_path = None
for p in ec_paths:
    if os.path.exists(p):
        ec_path = p
        break

if not ec_path:
    os.system("mount -t debugfs none /sys/kernel/debug 2>/dev/null")
    for p in ec_paths:
        if os.path.exists(p):
            ec_path = p
            break

if not ec_path:
    print("Error: EC debug node not found! Make sure debugfs is mounted.", file=sys.stderr)
    sys.exit(1)

print(f"EC Voltage & Fast PPT Patcher active on {ec_path}...")

# 1. Lock CPU C-states (prevents CPU from dipping to 400 MHz idle states)
try:
    latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
    os.write(latency_fd, struct.pack("i", 0))
    print("Locked /dev/cpu_dma_latency to 0 (Disabled 400 MHz C-state drops)")
except Exception as e:
    print(f"Warning: Could not lock cpu_dma_latency: {e}", file=sys.stderr)

# 2. Packed binary values matching exact Huawei DSDT fields
btdc_bytes = struct.pack("<H", 3610)   # 0x84: Design Capacity (mAh)
btdv_bytes = struct.pack("<H", 11400)  # 0x86: Design Voltage (mV)
btfc_bytes = struct.pack("<H", 3610)   # 0x88: Full Charge Capacity (mAh)
bapv_bytes = struct.pack("<H", 12500)  # 0x90: Present Voltage (mV)
barc_bytes = struct.pack("<H", 2888)   # 0x92: Remaining Capacity (mAh - 80%)
bfcc_bytes = struct.pack("<H", 3610)   # 0x94: Full Capacity (mAh)
btem_bytes = struct.pack("<H", 2980)   # 0x9A: Temperature (25 C)

# 3. Ryzen SMU Power Boost with Anti-400MHz Prochot Recovery
RYZENADJ_BIN = "/usr/local/bin/ryzenadj"

def apply_fast_ppt():
    """Apply calibrated 28W-30W targets to pin CPU to ~2.8 GHz and 84C thermal ceiling"""
    if not os.path.exists(RYZENADJ_BIN):
        return
    try:
        subprocess.run([
            RYZENADJ_BIN,
            "--stapm-limit=28000",
            "--fast-limit=30000",
            "--slow-limit=28000",
            "--vrm-current=45000",
            "--vrmmax-current=55000",
            "--vrmsoc-current=14000",
            "--vrmsocmax-current=18000",
            "--tctl-temp=84",
            "--prochot-deassertion-ramp=1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except Exception:
        pass

# Initial power unlock
apply_fast_ppt()
last_power_time = time.time()

running = True
def stop_handler(sig, frame):
    global running
    running = False
    print("EC Voltage Patcher stopping...")

signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)

try:
    with open(ec_path, "r+b", buffering=0) as f:
        while running:
            # 0x80: AC connected (bit 0) + Battery 1 present (bit 1) -> 0x03
            f.seek(0x80)
            b80 = f.read(1)
            curr_80 = b80[0] if b80 else 0
            f.seek(0x80)
            f.write(bytes([curr_80 | 0x03]))

            # 0x84: BTDC (Design Capacity: 3610 mAh)
            f.seek(0x84)
            f.write(btdc_bytes)

            # 0x86: BTDV (Design Voltage: 11400 mV)
            f.seek(0x86)
            f.write(btdv_bytes)

            # 0x88: BTFC (Full Charge Capacity: 3610 mAh)
            f.seek(0x88)
            f.write(btfc_bytes)

            # 0x90: BAPV (Present Voltage: 12500 mV)
            f.seek(0x90)
            f.write(bapv_bytes)

            # 0x92: BARC (Remaining Capacity: 2888 mAh)
            f.seek(0x92)
            f.write(barc_bytes)

            # 0x94: BFCC (3610 mAh)
            f.seek(0x94)
            f.write(bfcc_bytes)

            # 0x9A: BTEM (Temperature: 2980 = 25 C)
            f.seek(0x9A)
            f.write(btem_bytes)

            # Re-apply Fast PPT & instant PROCHOT recovery every 3 seconds
            now = time.time()
            if now - last_power_time >= 3.0:
                apply_fast_ppt()
                last_power_time = now

            time.sleep(0.005)  # 5ms loop
except Exception as e:
    print(f"EC Patcher Error: {e}", file=sys.stderr)
    sys.exit(1)

print("EC Voltage Patcher stopped cleanly.")
