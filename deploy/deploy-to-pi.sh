#!/bin/bash
# Deploy Talos to Raspberry Pi
# Usage: ./deploy-to-pi.sh [pi@duobrain.local]

set -e

PI_HOST="${1:-pi@duobrain.local}"
APP_SRC="/home/phil/Dev/Talos"
APP_DEST="/opt/talos/app"

echo "=== Deploying Talos to $PI_HOST ==="

echo "Creating remote directories..."
ssh -t "$PI_HOST" "sudo mkdir -p /opt/talos && sudo chown pi:pi /opt/talos && mkdir -p /opt/talos/app /opt/talos/logs"

echo "Syncing application files..."
rsync -avz --progress \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude '.env' \
  "$APP_SRC/" \
  "$PI_HOST:$APP_DEST/"

echo "Syncing gunicorn config..."
rsync -avz "$APP_SRC/deploy/gunicorn.conf.py" "$PI_HOST:/opt/talos/"

if ssh "$PI_HOST" "test -f /opt/talos/venv/bin/pip"; then
    echo "Installing dependencies..."
    ssh "$PI_HOST" "/opt/talos/venv/bin/pip install -q -r $APP_DEST/requirements.txt"
    echo "Restarting service..."
    ssh -t "$PI_HOST" "sudo systemctl restart talos"
    echo ""
    ssh -t "$PI_HOST" "sudo systemctl status talos --no-pager | head -20"
else
    echo ""
    echo "Venv not set up yet. SSH in and run:"
    echo "  bash /opt/talos/app/deploy/pi-setup.sh"
fi

echo ""
echo "=== Done ==="
