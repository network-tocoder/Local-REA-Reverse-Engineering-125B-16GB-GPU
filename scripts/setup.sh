#!/usr/bin/env bash
# setup.sh — full REA + local-agent stack, headless, on one machine.
#
# Mirrors the nine steps from the video. Safe to re-run: each step is
# individually idempotent.
#
#   ./setup.sh          run everything
#   ./setup.sh doctor   just check the install
#
# Tested on Ubuntu 24.04, RTX 5060 Ti 16GB, CUDA 13.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STRATA_DIR="${STRATA_DIR:-/workspace/Strata}"
STRATA_DATA="${STRATA_DATA:-/workspace/Strata-data}"
GHIDRA_DIR="${GHIDRA_DIR:-/opt/ghidra_12.1.4_PUBLIC}"
GHIDRA_VER="12.1.4"
REA_PKG="rea-agents@6.4.0"
STRATA_PORT="${STRATA_PORT:-8082}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# --- 1. hardware ------------------------------------------------------------
say "Step 1 — hardware"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

# --- 2. java + node ---------------------------------------------------------
say "Step 2 — JDK 21 and Node 24"
if ! command -v java >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y openjdk-21-jdk
fi
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
java -version
node --version

# --- 3. ghidra --------------------------------------------------------------
say "Step 3 — Ghidra ${GHIDRA_VER}"
if [ ! -d "$GHIDRA_DIR" ]; then
  # The release asset name carries a build date we can't guess
  # (ghidra_12.1.4_PUBLIC_20250715.zip), so ask the GitHub API for it.
  tmp=$(mktemp -d)
  url=$(curl -fsSL "https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/tags/Ghidra_${GHIDRA_VER}_build" \
        | grep -oE '"browser_download_url": *"[^"]*PUBLIC[^"]*\.zip"' \
        | head -1 | cut -d'"' -f4)
  [ -n "$url" ] || { echo "could not resolve Ghidra ${GHIDRA_VER} asset"; exit 1; }
  echo "  $url"
  curl -fL "$url" -o "$tmp/ghidra.zip"
  unzip -q "$tmp/ghidra.zip" -d "$tmp"
  sudo mkdir -p "$GHIDRA_DIR"
  sudo cp -r "$tmp"/ghidra_*/* "$GHIDRA_DIR"/
  rm -rf "$tmp"
fi
# You never open the Ghidra window. REA drives it headless.
ls "$GHIDRA_DIR/support/analyzeHeadless" >/dev/null && echo "headless launcher OK"

# --- 4. cuda (needed by Strata to compile its engine) -----------------------
say "Step 4 — CUDA 13"
if [ ! -d /usr/local/cuda/bin ]; then
  tmp=$(mktemp -d)
  sudo apt-get install -y cuda-toolkit-13-0
  rm -rf "$tmp"
fi
export PATH="/usr/local/cuda/bin:$PATH"
nvcc --version | tail -2 || true

# --- 5. strata --------------------------------------------------------------
say "Step 5 — Strata engine (auto-tune takes several minutes)"
if [ ! -d "$STRATA_DIR/.git" ]; then
  git clone https://github.com/Niko1221/Strata.git "$STRATA_DIR"
fi
cd "$STRATA_DIR"
# Strata's own installer, not this script.
chmod +x ./setup.sh
./setup.sh --port "$STRATA_PORT"
# Interactive menu: Qwen3.8-Flash-Next -> IQ3_S -> 64K -> KV int8
# Step 5b: then let it tune itself. It restarts repeatedly, measuring each
# setting: 47 workers -> 39 tok/s | 31 -> 57.8 | 24 -> 73.5 | final 77.7 tok/s

# --- 6. agent ---------------------------------------------------------------
say "Step 6 — OpenCode"
command -v opencode >/dev/null || npm install -g opencode-ai
opencode --version

# --- 7. REA -----------------------------------------------------------------
say "Step 7 — REA"
npx -y "$REA_PKG" setup
# Detects OpenCode, point it at Ghidra, registers itself as an MCP server.

# --- 8. the tool filter (do not skip this one) ------------------------------
say "Step 8 — cut 170 tools down to 19"
# All 170 tool descriptions ~= 150K tokens. Context window is 128K.
# Without this the agent compacts forever and never finishes.
python3 "$SCRIPT_DIR/rea-tool-filter.py" --derive --apply

# --- 9. doctor --------------------------------------------------------------
say "Step 9 — REA doctor"
npx -y "$REA_PKG" doctor

say "Done"
cat <<EOF
Next:
  1. start Strata:      cd $STRATA_DIR && ./run-*.sh
  2. confirm the API:   curl http://localhost:$STRATA_PORT/v1/models
  3. open your agent in the folder with the stripped binary
  4. run it, don't watch it fail on tool count first

Context and tool surface are the two dials. See ../docs/failures.md
EOF