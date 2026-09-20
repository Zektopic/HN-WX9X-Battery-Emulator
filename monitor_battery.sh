#!/usr/bin/env bash
# Real-Time Battery, CPU Boost (3.0+ GHz), & Ryzen Power Monitor

watch -n 1 '
echo "=================================================="
echo "      18650 BATTERY MOD & FAST PPT BOOST MONITOR  "
echo "=================================================="

echo "--- Battery Emulation Status ---"
if [ -d /sys/class/power_supply/BAT0 ]; then
  echo -n "Status:          "
  cat /sys/class/power_supply/BAT0/status 2>/dev/null || echo "N/A"
  echo -n "Voltage:         "
  [ -f /sys/class/power_supply/BAT0/voltage_now ] && awk "{print \$1/1000000 \" V\"}" /sys/class/power_supply/BAT0/voltage_now 2>/dev/null || echo "N/A"
  echo -n "Energy Now:      "
  [ -f /sys/class/power_supply/BAT0/energy_now ] && awk "{print \$1/1000000 \" Wh\"}" /sys/class/power_supply/BAT0/energy_now 2>/dev/null || echo "N/A"
else
  echo "BAT0 sysfs node not present"
fi

echo ""
echo "--- CPU Clock Frequencies (Target: 3.0+ GHz) ---"
grep "cpu MHz" /proc/cpuinfo 2>/dev/null | awk "{
  ghz = \$4/1000;
  tag = (ghz >= 3.0) ? \"[FAST BOOST 3.0G+]\" : \"[BOOST ACTIVE]\";
  printf(\" Core %d:  %.3f GHz  %s\n\", NR-1, ghz, tag);
}"

echo ""
echo "--- Ryzen SMU Power State ---"
if [ -x /usr/local/bin/ryzenadj ]; then
  sudo /usr/local/bin/ryzenadj -i 2>/dev/null | grep -iE "stapm limit|ppt limit fast|edc limit vdd|thm limit core|thm value core" | head -n 5
fi

echo ""
echo "--- GPU Utilization ---"
echo -n "GPU Load:        "
cat /sys/class/drm/card0/device/gpu_busy_percent 2>/dev/null | awk "{print \$1 \"%\"}" || echo "N/A"
'
