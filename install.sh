#!/usr/bin/env bash
set -euo pipefail

# clauline installer
# https://github.com/vektor91/clauline
# MIT License — Alberto Gil (vektor91)

CLAULINE_URL="https://raw.githubusercontent.com/vektor91/clauline/main/clauline.py"
DEST="$HOME/.claude/clauline.py"
SETTINGS="$HOME/.claude/settings.json"

# ── helpers ────────────────────────────────────────────────────────────────────
say()  { printf '\033[0;36m:: \033[0m%s\n' "$*"; }
warn() { printf '\033[0;33m!! \033[0m%s\n' "$*"; }
die()  { printf '\033[0;31mxx \033[0m%s\n' "$*" >&2; exit 1; }

# ── pre-checks ─────────────────────────────────────────────────────────────────
say "Checking requirements..."

command -v python3 >/dev/null 2>&1 \
  || die "python3 not found. Install Python 3.8+ and re-run."

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" \
  || die "Python 3.8 or newer is required. Current: $(python3 --version 2>&1)."

say "python3 OK: $(python3 --version)"

# ── ensure ~/.claude exists ────────────────────────────────────────────────────
mkdir -p "$HOME/.claude"

# ── backup existing clauline.py ────────────────────────────────────────────────
if [[ -f "$DEST" ]]; then
  TS="$(date +%Y%m%d-%H%M%S)"
  BAK="${DEST}.bak.${TS}"
  warn "Existing $DEST found — backing up to $BAK"
  cp "$DEST" "$BAK"
fi

# ── obtain clauline.py ────────────────────────────────────────────────────────
if [[ -f "./clauline.py" ]]; then
  say "Using local clauline.py..."
  cp ./clauline.py "$DEST"
else
  say "Downloading clauline.py..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$CLAULINE_URL" -o "$DEST" \
      || die "curl download failed."
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$CLAULINE_URL" -O "$DEST" \
      || die "wget download failed."
  else
    die "Neither curl nor wget found. Install one and re-run."
  fi
fi

say "clauline.py installed to $DEST"

# ── set executable ─────────────────────────────────────────────────────────────
chmod +x "$DEST"

# ── configure ~/.claude/settings.json ─────────────────────────────────────────
say "Configuring $SETTINGS..."

if [[ -f "$SETTINGS" ]]; then
  TS="$(date +%Y%m%d-%H%M%S)"
  BAK_S="${SETTINGS}.bak.${TS}"
  warn "Existing settings.json found — backing up to $BAK_S"
  cp "$SETTINGS" "$BAK_S"
fi

python3 - <<PYEOF
import json, os, sys

settings_path = os.path.expanduser("~/.claude/settings.json")
home = os.path.expanduser("~")

status_line = {
    "type": "command",
    "command": "python3 {home}/.claude/clauline.py".format(home=home)
}

if os.path.isfile(settings_path):
    try:
        with open(settings_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("!! settings.json is not valid JSON — creating a fresh one.")
        data = {}
else:
    data = {}

data["statusLine"] = status_line

with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")

print(":: statusLine set in", settings_path)
PYEOF

# ── test render ────────────────────────────────────────────────────────────────
say "Testing render..."
T5H=$(( $(date +%s) + 7200 ))
T7D=$(( $(date +%s) + 259200 ))
printf '{
  "model": {"id": "claude-sonnet-4-6", "display_name": "Sonnet 4.6"},
  "output_config": {"effort": "high"},
  "workspace": {"current_dir": "%s"},
  "context_window": {"used_percentage": 38, "total_input_tokens": 9000, "total_output_tokens": 3200},
  "cost": {"total_duration_ms": 420000},
  "rate_limits": {
    "five_hour": {"used_percentage": 8, "resets_at": %d},
    "seven_day": {"used_percentage": 2, "resets_at": %d}
  }
}' "$HOME" "$T5H" "$T7D" | python3 "$DEST"

# ── done ───────────────────────────────────────────────────────────────────────
say "Done. Restart Claude Code to apply clauline."
