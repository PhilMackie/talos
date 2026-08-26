#!/bin/bash
# One-time Talos setup on the Pi.
# Run ON THE PI: bash /opt/talos/app/deploy/pi-setup.sh
# (Pi already has Python, venv support, UFW from duo-brain setup.)

set -e

echo "=== Talos Pi Setup ==="

# Directories
sudo mkdir -p /opt/talos
sudo chown pi:pi /opt/talos
mkdir -p /opt/talos/app /opt/talos/logs

# Virtual environment
echo "Creating venv..."
python3 -m venv /opt/talos/venv
/opt/talos/venv/bin/pip install --upgrade pip -q
/opt/talos/venv/bin/pip install -q -r /opt/talos/app/requirements.txt

# .env
if [ ! -f /opt/talos/app/.env ]; then
    echo "Creating .env..."
    cat > /opt/talos/app/.env << 'EOF'
TALOS_ROUTINES_DIR=/opt/duobrain/vault/dev/Talos/routines
EOF
    chmod 600 /opt/talos/app/.env
    echo ".env created."
fi

# Open firewall port
echo "Opening port 5009..."
sudo ufw allow 5009/tcp

# Systemd service
echo "Installing systemd service..."
sudo cp /opt/talos/app/deploy/talos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable talos
sudo systemctl start talos

echo ""
sleep 2
sudo systemctl status talos --no-pager
echo ""
echo "=== Talos is running on port 5009 ==="
echo "Test: curl -I http://localhost:5009/"
