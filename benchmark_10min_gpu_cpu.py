#!/usr/bin/env python3
"""
10-Minute Continuous Benchmark & Telemetry Monitor:
Simultaneous Full CPU BOINC (6 AVX threads) + GPU BOINC (PrimeGrid Genefer OpenCL) + Frigate NVR
Monitors thermal stability, CPU scaling, GPU clocks, memory allocation, and 400 MHz throttling.
"""

import time
import subprocess
import os
import sys

DURATION = 600  # 10 minutes
INTERVAL = 1.0  # 1 second sampling interval

def get_freqs():
    with open('/proc/cpuinfo') as f:
        return [float(line.split(':')[1]) for line in f if 'cpu MHz' in line]

def get_temp():
    try:
        out = subprocess.check_output(['sensors'], stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            if 'Tctl:' in line:
                return float(line.split(':')[1].replace('+', '').replace('°C', '').strip())
    except Exception:
        pass
    return 0.0

def get_gpu_clocks():
    sclk = "N/A"
    mclk = "N/A"
    try:
        with open('/sys/class/drm/card0/device/pp_dpm_sclk') as f:
            for line in f:
                if '*' in line:
                    sclk = line.strip().split()[1]
        with open('/sys/class/drm/card0/device/pp_dpm_mclk') as f:
            for line in f:
                if '*' in line:
                    mclk = line.strip().split()[1]
    except Exception:
        pass
    return sclk, mclk

def get_gpu_mem():
    vram_mb = 0.0
    gtt_mb = 0.0
    try:
        with open('/sys/class/drm/card0/device/mem_info_vis_vram_used') as f:
            vram_mb = int(f.read().strip()) / (1024 * 1024)
        with open('/sys/class/drm/card0/device/mem_info_gtt_used') as f:
            gtt_mb = int(f.read().strip()) / (1024 * 1024)
    except Exception:
        pass
    return vram_mb, gtt_mb

def check_genefer():
    try:
        out = subprocess.check_output(['pgrep', '-f', 'genefer'], stderr=subprocess.DEVNULL).decode().strip()
        return bool(out)
    except Exception:
        return False

print("=" * 70)
print(f"STARTING 10-MINUTE BENCHMARK: CPU BOINC + GPU BOINC + FRIGATE NVR")
print(f"Target Duration: {DURATION} seconds | Sampling Rate: {INTERVAL}s")
print("=" * 70)

# Ensure GPU mode is always running in BOINC
subprocess.run(['sudo', '-S', 'boinccmd', '--set_gpu_mode', 'always'], input=b'manupa\n', check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

all_avg_freqs = []
all_temps = []
drops_400 = 0
total_samples = 0
start_time = time.time()
next_log_time = start_time + 30.0

try:
    while True:
        now = time.time()
        elapsed = now - start_time
        if elapsed >= DURATION:
            break

        freqs = get_freqs()
        temp = get_temp()
        sclk, mclk = get_gpu_clocks()
        vram_mb, gtt_mb = get_gpu_mem()
        genefer_alive = check_genefer()

        avg_freq = sum(freqs) / len(freqs)
        min_freq = min(freqs)
        max_freq = max(freqs)

        all_avg_freqs.append(avg_freq)
        if temp > 0:
            all_temps.append(temp)

        # Check for 400 MHz throttle drops (< 450 MHz)
        drop_count_in_sample = sum(1 for f in freqs if f <= 450.0)
        if drop_count_in_sample > 0:
            drops_400 += 1

        total_samples += 1

        # Periodic status output every 30 seconds
        if now >= next_log_time or total_samples == 1:
            next_log_time = now + 30.0
            print(f"[{elapsed:5.1f}s / {DURATION}s] Tctl: {temp:4.1f}°C | CPU Avg: {avg_freq:6.1f} MHz (Min: {min_freq:6.1f}, Max: {max_freq:6.1f}) | GPU SCLK: {sclk:>7} | MCLK: {mclk:>7} | VRAM: {vram_mb:5.0f}MB | GTT: {gtt_mb:5.0f}MB | Drops: {drops_400} | Genefer: {'RUNNING' if genefer_alive else 'STOPPED'}")

        # Emergency thermal failsafe
        if temp >= 86.0:
            print(f"\n[EMERGENCY FAILSAFE] Temp reached {temp}°C! Suspending GPU mode...")
            subprocess.run(['sudo', '-S', 'boinccmd', '--set_gpu_mode', 'never'], input=b'manupa\n', check=False)
            break

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nBenchmark interrupted by user.")

end_time = time.time()
total_time = end_time - start_time

print("\n" + "=" * 70)
print("10-MINUTE BENCHMARK COMPLETED — FINAL TELEMETRY REPORT")
print("=" * 70)
print(f"Actual Test Duration:    {total_time:.2f} seconds ({total_samples} samples)")
if all_avg_freqs:
    print(f"CPU Average Frequency:   {sum(all_avg_freqs)/len(all_avg_freqs):.1f} MHz")
    print(f"CPU Min Frequency:       {min(all_avg_freqs):.1f} MHz")
    print(f"CPU Max Frequency:       {max(all_avg_freqs):.1f} MHz")
if all_temps:
    print(f"Tctl Temperature Avg:    {sum(all_temps)/len(all_temps):.2f}°C")
    print(f"Tctl Temperature Min:    {min(all_temps):.1f}°C")
    print(f"Tctl Temperature Max:    {max(all_temps):.1f}°C")
print(f"400 MHz Throttling Hits: {drops_400} / {total_samples} ({(drops_400/total_samples)*100:.2f}%)")
print(f"GPU Genefer Status:      {'Still running' if check_genefer() else 'Exited'}")
print("=" * 70)
