#!/usr/bin/env bash
# Uninstall & Disable EC Voltage & Fast PPT Patcher Service

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (e.g., sudo ./uninstall_service.sh)"
  exit 1
fi

SERVICE_NAME="ec-voltage-patcher.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

echo "Stopping and disabling $SERVICE_NAME..."
systemctl stop "$SERVICE_NAME" 2>/dev/null
systemctl disable "$SERVICE_NAME" 2>/dev/null

if [ -f "$SERVICE_PATH" ]; then
  rm -f "$SERVICE_PATH"
  echo "Removed $SERVICE_PATH"
fi

rm -f /etc/modules-load.d/ec_sys.conf 2>/dev/null
rm -f /etc/modprobe.d/ec_sys.conf 2>/dev/null

systemctl daemon-reload
systemctl reset-failed 2>/dev/null

echo "=================================================="
echo " SUCCESS: $SERVICE_NAME Uninstalled & Removed."
echo "=================================================="
