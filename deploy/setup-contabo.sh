#!/bin/bash
# Brazil MCP Server — Deploy script for Contabo VPS
# Run as root or with sudo
# Tailscale must be already configured on the server

set -e

APP_NAME="brazil-mcp-server"
APP_USER="mcp-server"
APP_DIR="/opt/${APP_NAME}"
DATA_DIR="${APP_DIR}/data"
VENV_DIR="${APP_DIR}/venv"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
REPO_URL="https://github.com/impulsoxai/brazil-mcp-server.git"

echo "=== Brazil MCP Server — Contabo Deploy ==="

# 1. Create dedicated user (no login shell)
if ! id "${APP_USER}" &>/dev/null; then
    echo "[1/7] Creating user ${APP_USER}..."
    sudo useradd -r -s /bin/false -d "${APP_DIR}" "${APP_USER}"
else
    echo "[1/7] User ${APP_USER} already exists"
fi

# 2. Create directories
echo "[2/7] Setting up directories..."
sudo mkdir -p "${APP_DIR}" "${DATA_DIR}"

# 3. Clone or update repo
if [ ! -d "${APP_DIR}/.git" ]; then
    echo "[3/7] Cloning repository..."
    sudo git clone "${REPO_URL}" "${APP_DIR}"
else
    echo "[3/7] Updating repository..."
    cd "${APP_DIR}" && sudo git pull origin main
fi

# 4. Python venv + dependencies
echo "[4/7] Setting up Python environment..."
if [ ! -d "${VENV_DIR}" ]; then
    sudo python3 -m venv "${VENV_DIR}"
fi
sudo "${VENV_DIR}/bin/pip" install --upgrade pip
sudo "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

# 5. Environment file
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "[5/7] Creating .env file..."
    sudo tee "${APP_DIR}/.env" > /dev/null << 'ENVEOF'
MCP_ENV=production
MCP_PORT=8000
BRASIL_API_BASE=https://brasilapi.com.br/api
AWESOME_API_BASE=https://economia.awesomeapi.com.br
SENTRY_DSN=
ENVEOF
    echo "  ⚠️  Edit ${APP_DIR}/.env with your production values"
else
    echo "[5/7] .env already exists"
fi

# 6. Set permissions (CRITICAL — protects data from other processes)
echo "[6/7] Setting secure permissions..."
sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
sudo chmod 700 "${DATA_DIR}"
sudo chmod 600 "${DATA_DIR}/"*.db 2>/dev/null || true
sudo chmod 600 "${APP_DIR}/.env"

# 7. Systemd service
echo "[7/7] Creating systemd service..."
sudo tee "${SERVICE_FILE}" > /dev/null << EOF
[Unit]
Description=Brazil MCP Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PATH=${VENV_DIR}/bin
ExecStart=${VENV_DIR}/bin/python -m uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${DATA_DIR}
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}"
sudo systemctl restart "${APP_NAME}"

echo ""
echo "=== Deploy complete ==="
echo "Service: sudo systemctl status ${APP_NAME}"
echo "Logs:    sudo journalctl -u ${APP_NAME} -f"
echo "Data:    ${DATA_DIR} (chmod 700, owned by ${APP_USER})"
echo ""
echo "Tailscale: ensure port 8000 is accessible within your tailnet"
echo "Public:    configure Tailscale funnel or reverse proxy if needed"
