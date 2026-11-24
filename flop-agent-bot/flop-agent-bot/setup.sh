#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  FLOP Agent Bot - Setup"
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
else
  echo "Unsupported OS: $OSTYPE"
  exit 1
fi

echo "[1/5] Checking Python..."
if ! command -v python3 &>/dev/null; then
  echo "Python 3 is required. Install it first."
  exit 1
fi
python3 --version

echo "[2/5] Checking / installing Node 22..."
if ! command -v node &>/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]]; then
  echo "Installing Node 22 via nvm..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm install 22
  nvm use 22
  nvm alias default 22
else
  echo "Node $(node -v) found"
fi

# Ensure npx is available
if ! command -v npx &>/dev/null; then
  echo "npx not found. Trying to install npm..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -y && sudo apt-get install -y npm
  else
    echo "Please install npm manually."
    exit 1
  fi
fi

echo "[3/5] Creating Python virtualenv..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/5] Pre-fetching FLOP CLI..."
npx --yes @flop-labs/cli@0.7.0 --version || true

echo "[5/5] Creating .env template..."
if [[ ! -f .env ]]; then
  cat > .env << 'EOF'
# Required: strong password for the keystore (never commit this file)
FLOP_KEYSTORE_PASSWORD=change-me-to-a-strong-password

# Network: testnet (real) or devnet (practice, zero airdrop weight)
FLOP_NETWORK=testnet

# Safety limits
MAX_FLOP_PER_SESSION=0.5
MAX_SESSIONS_PER_DAY=40
MIN_BALANCE_TO_SPEND=0.2
LOOP_SLEEP=90
EOF
  echo "Created .env – edit it and set a strong FLOP_KEYSTORE_PASSWORD"
else
  echo ".env already exists, skipping"
fi

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env and set a strong password:"
echo "       nano .env"
echo "  2. Load the password into the current shell:"
echo "       export \$(grep -v '^#' .env | xargs)"
echo "  3. Start the bot:"
echo "       source .venv/bin/activate"
echo "       python bot.py"
echo ""
echo "Or use Docker (recommended for 24/7):"
echo "  docker compose up -d"
echo ""
