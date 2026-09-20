#!/usr/bin/env bash
# Install & Enable EC Voltage & Fast PPT Patcher Systemd Service (Persistent Across Boots)

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (e.g., sudo ./install_service.sh)"
  exit 1
fi

SCRIPT_PATH="/home/manupa/18650_battery_mod/ec_voltage_patcher.py"
SERVICE_PATH="/etc/systemd/system/ec-voltage-patcher.service"

chmod +x "$SCRIPT_PATH"
[ -f /usr/local/bin/ryzenadj ] && chmod +x /usr/local/bin/ryzenadj

# 1. Ensure kernel module ec_sys with write_support=1 loads on boot
echo "Configuring persistent ec_sys kernel module..."
echo "ec_sys" > /etc/modules-load.d/ec_sys.conf
echo "options ec_sys write_support=1" > /etc/modprobe.d/ec_sys.conf

# 2. Load module immediately
modprobe ec_sys write_support=1 2>/dev/null

# 3. Create systemd unit file
cat << EOF > "$SERVICE_PATH"
[Unit]
Description=EC RAM Voltage, Capacity & Fast PPT 45W Patcher (3.0+ GHz Boost)
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
ExecStartPre=/sbin/modprobe ec_sys write_support=1
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
RestartSec=2s

[Install]
WantedBy=multi-user.target
EOF

# 4. Enable and start service
systemctl daemon-reload
systemctl enable ec-voltage-patcher.service
systemctl restart ec-voltage-patcher.service

echo "=================================================="
echo " SUCCESS: ec-voltage-patcher.service Installed & Active!"
echo " Status:"
systemctl status ec-voltage-patcher.service --no-pager
echo "=================================================="
