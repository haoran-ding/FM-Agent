#!/usr/bin/env bash
set -euo pipefail

echo "=== fm-agent: installing required software ==="

# ---------- Python 3.12+ ----------
if command -v python3 &>/dev/null; then
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    py_major=$(python3 -c 'import sys; print(sys.version_info.major)')
    py_minor=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [[ "$py_major" -lt 3 ]] || { [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -lt 12 ]]; }; then
        echo "[!!] python3 version $py_ver found, but 3.12+ is required."
        exit 1
    fi
    echo "[ok] python3 found: $(python3 --version)"
else
    echo "[!!] python3 not found. Please install Python 3.12+ for your platform."
    exit 1
fi

# ---------- pip ----------
if python3 -m pip --version &>/dev/null; then
    echo "[ok] pip found"
else
    echo "[..] installing pip"
    python3 -m ensurepip --upgrade || {
        echo "[!!] could not install pip. Install it manually."
        exit 1
    }
fi

# --break-system-packages requires pip >= 23.0.1; upgrade if too old
pip_ver=$(python3 -m pip --version | awk '{print $2}')
pip_major=$(echo "$pip_ver" | cut -d. -f1)
if [[ "$pip_major" -lt 23 ]]; then
    echo "[..] pip $pip_ver is too old (need >= 23.0.1 for --break-system-packages), upgrading..."
    python3 -m pip install --upgrade pip || {
        echo "[!!] could not upgrade pip."
        exit 1
    }
fi

# ---------- Python packages ----------
echo "[..] installing Python dependencies"
python3 -m pip install --upgrade --break-system-packages openai

# ---------- unzip ----------
if command -v unzip &>/dev/null; then
    echo "[ok] unzip found"
else
    echo "[..] installing unzip"
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y unzip
    elif command -v yum &>/dev/null; then
        sudo yum install -y unzip
    elif command -v apk &>/dev/null; then
        apk add --no-cache unzip
    else
        echo "[!!] could not install unzip. Install it manually."
        exit 1
    fi
fi

# ---------- opencode CLI ----------
if command -v opencode &>/dev/null; then
    echo "[ok] opencode found: $(opencode --version 2>/dev/null || echo 'unknown version')"
else
    echo "[..] installing opencode"
    curl -fsSL https://opencode.ai/install | bash
fi

# ---------- oh-my-opencode plugin ----------
if command -v bunx &>/dev/null; then
    echo "[ok] bun found"
else
    echo "[..] installing bun"
    curl -fsSL https://bun.sh/install | bash
    # source shell config to pick up bun PATH written by the installer
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        [[ -f "$rc" ]] && source "$rc"
    done
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
fi
echo "[..] installing/updating oh-my-opencode"
bunx oh-my-opencode install

echo ""
echo "=== all dependencies installed ==="
