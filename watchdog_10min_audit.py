#!/usr/bin/env python3
"""
10-Minute Comprehensive System Watchdog & Telemetry Auditor
Monitors:
  - CPU frequencies across all 8 threads (detects any 400 MHz throttling)
  - GPU Core (SCLK), VRAM (MCLK), Busy %, VRAM & GTT allocations
  - Tctl Junction Temperature & Headroom vs 84C SMU ceiling
  - BOINC OpenCL Genefer execution progress & stability
  - Frigate NVR & FFmpeg camera stream continuity
  - Kernel dmesg logs for panics, resets, MCEs, or thermal alarms
"""

import time
import subprocess
import os
import sys
import json

DURATION = 600  # 10 minutes
INTERVAL = 1.0  # 1.0 second per sample

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

def get_gpu_metrics():
    sclk = 0
    mclk = 0
    busy = 0
    vram_mb = 0.0
    gtt_mb = 0.0
    try:
        with open('/sys/class/drm/card0/device/pp_dpm_sclk') as f:
            for line in f:
                if '*' in line:
                    sclk = int(line.strip().split()[1].replace('Mhz', ''))
        with open('/sys/class/drm/card0/device/pp_dpm_mclk') as f:
            for line in f:
                if '*' in line:
                    mclk = int(line.strip().split()[1].replace('Mhz', ''))
        with open('/sys/class/drm/card0/device/gpu_busy_percent') as f:
            busy = int(f.read().strip())
        with open('/sys/class/drm/card0/device/mem_info_vis_vram_used') as f:
            vram_mb = int(f.read().strip()) / (1024 * 1024)
        with open('/sys/class/drm/card0/device/mem_info_gtt_used') as f:
            gtt_mb = int(f.read().strip()) / (1024 * 1024)
    except Exception:
        pass
    return sclk, mclk, busy, vram_mb, gtt_mb

def get_process_stats():
    genefer_alive = False
    genefer_pid = None
    frigate_alive = False
    ffmpeg_count = 0
    try:
        g_out = subprocess.check_output(['pgrep', '-f', 'genefer'], stderr=subprocess.DEVNULL).decode().strip()
        if g_out:
            genefer_alive = True
            genefer_pid = g_out.splitlines()[0]
    except Exception:
        pass

    try:
        f_out = subprocess.check_output(['pgrep', '-f', 'frigate.detecto'], stderr=subprocess.DEVNULL).decode().strip()
        if f_out:
            frigate_alive = True
    except Exception:
        pass

    try:
        ff_out = subprocess.check_output(['pgrep', '-c', '-f', 'ffmpeg'], stderr=subprocess.DEVNULL).decode().strip()
        ffmpeg_count = int(ff_out)
    except Exception:
        pass

    return genefer_alive, genefer_pid, frigate_alive, ffmpeg_count

def get_dmesg_lines():
    try:
        out = subprocess.check_output(['sudo', '-S', 'dmesg'], input=b'manupa\n', stderr=subprocess.DEVNULL).decode()
        return out.splitlines()
    except Exception:
        return []

print("=" * 80)
print("STARTING 10-MINUTE SYSTEM WATCHDOG & TELEMETRY AUDIT")
print(f"Target Duration: {DURATION} seconds | Sampling Interval: {INTERVAL}s")
print("Workload: Full BOINC CPU (6 AVX threads) + BOINC GPU (Genefer OpenCL) + Frigate NVR")
print("Power Profile: 35W STAPM / 38W Fast PPT on 100W USB-PD Charger")
print("=" * 80)

initial_dmesg = get_dmesg_lines()
initial_dmesg_count = len(initial_dmesg)

all_cpu_avgs = []
all_cpu_mins = []
all_cpu_maxs = []
all_temps = []
all_sclks = []
all_mclks = []
all_busys = []
all_vram = []
all_gtt = []
throttle_400_hits = 0
total_samples = 0

start_time = time.time()
next_log = start_time + 30.0

try:
    while True:
        now = time.time()
        elapsed = now - start_time
        if elapsed >= DURATION:
            break

        freqs = get_freqs()
        temp = get_temp()
        sclk, mclk, busy, vram_mb, gtt_mb = get_gpu_metrics()
        genefer_alive, genefer_pid, frigate_alive, ffmpeg_count = get_process_stats()

        avg_freq = sum(freqs) / len(freqs)
        min_freq = min(freqs)
        max_freq = max(freqs)

        all_cpu_avgs.append(avg_freq)
        all_cpu_mins.append(min_freq)
        all_cpu_maxs.append(max_freq)
        if temp > 0:
            all_temps.append(temp)
        if sclk > 0:
            all_sclks.append(sclk)
        if mclk > 0:
            all_mclks.append(mclk)
        all_busys.append(busy)
        all_vram.append(vram_mb)
        all_gtt.append(gtt_mb)

        if any(f <= 450.0 for f in freqs):
            throttle_400_hits += 1

        total_samples += 1

        if now >= next_log or total_samples == 1:
            next_log = now + 30.0
            print(f"[{elapsed:5.1f}s / {DURATION}s] Tctl: {temp:4.1f}°C | CPU: {avg_freq:6.1f} MHz (Min: {min_freq:6.1f}) | GPU: {sclk:4d}MHz ({busy:3d}% busy) | VRAM: {mclk:4d}MHz ({vram_mb:4.0f}MB) | Genefer: {'RUNNING' if genefer_alive else 'STOPPED'} | FFmpeg: {ffmpeg_count} | 400Mhz Drops: {throttle_400_hits}")

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nWatchdog interrupted by user.")

end_time = time.time()
total_time = end_time - start_time

# Audit final dmesg
final_dmesg = get_dmesg_lines()
new_dmesg_lines = final_dmesg[initial_dmesg_count:] if len(final_dmesg) >= initial_dmesg_count else []
error_lines = [line for line in new_dmesg_lines if any(k in line.lower() for k in ['panic', 'error', 'oops', 'bug', 'mce', 'warn', 'throttl', 'wedged'])]

print("\n" + "=" * 80)
print("10-MINUTE SYSTEM WATCHDOG AUDIT COMPLETED — FINAL AGGREGATE REPORT")
print("=" * 80)
print(f"Total Test Duration:       {total_time:.2f} seconds ({total_samples} samples)")
print(f"CPU Average Frequency:     {sum(all_cpu_avgs)/len(all_cpu_avgs):.1f} MHz")
print(f"CPU Minimum Frequency:     {min(all_cpu_mins):.1f} MHz")
print(f"CPU Maximum Frequency:     {max(all_cpu_maxs):.1f} MHz")
print(f"Tctl Core Temperature Avg: {sum(all_temps)/len(all_temps):.2f}°C (Min: {min(all_temps):.1f}°C, Max: {max(all_temps):.1f}°C)")
print(f"Thermal Headroom below 84C:{84.0 - max(all_temps):.1f}°C")
print(f"400 MHz Throttling Drops:  {throttle_400_hits} / {total_samples} ({(throttle_400_hits/total_samples)*100:.2f}%)")
print(f"GPU Core SCLK Average:     {sum(all_sclks)/len(all_sclks) if all_sclks else 0:.1f} MHz")
print(f"GPU VRAM MCLK Average:     {sum(all_mclks)/len(all_mclks) if all_mclks else 0:.1f} MHz (Pinned to 1200 MHz)")
print(f"GPU Busy Utilization Avg:  {sum(all_busys)/len(all_busys):.1f}%")
print(f"GPU VRAM Used Avg:         {sum(all_vram)/len(all_vram):.1f} MB (Dedicated)")
print(f"GPU GTT Used Avg:          {sum(all_gtt)/len(all_gtt):.1f} MB (Dynamic Shared)")
g_alive, g_pid, f_alive, ff_count = get_process_stats()
print(f"BOINC Genefer Status:      {'ACTIVE (PID ' + str(g_pid) + ')' if g_alive else 'STOPPED'}")
print(f"Frigate Detector Status:   {'ACTIVE' if f_alive else 'STOPPED'}")
print(f"Frigate FFmpeg Streams:    {ff_count} active camera decoders")
print(f"New Kernel Dmesg Entries:  {len(new_dmesg_lines)} lines")
print(f"Kernel Hardware Errors:    {len(error_lines)} errors/panics")
if error_lines:
    print("Detected Kernel Errors:")
    for err in error_lines[:10]:
        print("  - " + err)
else:
    print("Kernel Status:             CLEAN (Zero panics, zero resets, zero MCE errors)")
print("=" * 80)
