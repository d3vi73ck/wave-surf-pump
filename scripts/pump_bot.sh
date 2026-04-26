#!/usr/bin/env bash
#
# pump_bot.sh — Wave Surf Pump v4.1 (LONG)
# Trader runs embedded scanner + BTC mood check.
#
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$DIR/data"

echo "🌊 Wave Surf Pump v4 — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "──────────────────────────────────────────"

cd "$DIR"
timeout 120 python3 -m scripts.trader
python3 -m scripts.report "$DATA_DIR" "long"
