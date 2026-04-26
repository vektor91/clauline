#!/usr/bin/env bash
set -euo pipefail

# clauline installer / uninstaller
# https://github.com/vektor91/clauline
# MIT License — Alberto Gil (vektor91)

CLAULINE_URL="https://raw.githubusercontent.com/vektor91/clauline/main/clauline.py"
DEST="$HOME/.claude/clauline.py"
SETTINGS="$HOME/.claude/settings.json"

say()  { printf '\033[0;36m:: \033[0m%s\n' "$*"; }
warn() { printf '\033[0;33m!! \033[0m%s\n' "$*"; }
die()  { printf '\033[0;31mxx \033[0m%s\n' "$*" >&2; exit 1; }

# ── Uninstall ──────────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--uninstall" ]]; then
  say "Uninstalling clauline..."

  [[ -f "$DEST" ]] && rm -f "$DEST" && say "Removed $DEST"

  if [[ -f "$SETTINGS" ]]; then
    python3 - <<PYEOF
import json, os, sys
p = os.path.expanduser("~/.claude/settings.json")
try:
    with open(p) as f:
        d = json.load(f)
    if "statusLine" in d:
        del d["statusLine"]
        with open(p, "w") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
        print(":: Removed statusLine from", p)
    else:
        print(":: statusLine not present in", p)
except Exception as e:
    print("!! Could not update settings.json:", e)
PYEOF
  fi

  # Clean up state file
  [[ -f "$HOME/.claude/clauline_state.json" ]] \
    && rm -f "$HOME/.claude/clauline_state.json" \
    && say "Removed state file"

  say "Done. Restart Claude Code to apply."
  exit 0
fi

# ── Pre-checks ─────────────────────────────────────────────────────────────────

say "Checking requirements..."

command -v python3 >/dev/null 2>&1 \
  || die "python3 not found. Install Python 3.8+ and re-run."

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" \
  || die "Python 3.8 or newer required. Current: $(python3 --version 2>&1)."

say "python3 OK: $(python3 --version)"

# ── Install ────────────────────────────────────────────────────────────────────

mkdir -p "$HOME/.claude"

if [[ -f "$DEST" ]]; then
  TS="$(date +%Y%m%d-%H%M%S)"
  BAK="${DEST}.bak.${TS}"
  warn "Existing $DEST found — backing up to $BAK"
  cp "$DEST" "$BAK"
fi

if [[ -f "./clauline.py" ]]; then
  say "Using local clauline.py..."
  cp ./clauline.py "$DEST"
else
  say "Downloading clauline.py..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$CLAULINE_URL" -o "$DEST" || die "curl download failed."
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$CLAULINE_URL" -O "$DEST"    || die "wget download failed."
  else
    die "Neither curl nor wget found."
  fi
fi

chmod +x "$DEST"
say "clauline.py installed to $DEST"

# ── Configure settings.json ────────────────────────────────────────────────────

say "Configuring $SETTINGS..."

if [[ -f "$SETTINGS" ]]; then
  TS="$(date +%Y%m%d-%H%M%S)"
  warn "Existing settings.json found — backing up to ${SETTINGS}.bak.${TS}"
  cp "$SETTINGS" "${SETTINGS}.bak.${TS}"
fi

python3 - <<PYEOF
import json, os
p    = os.path.expanduser("~/.claude/settings.json")
home = os.path.expanduser("~")
entry = {"type": "command",
         "command": "python3 {home}/.claude/clauline.py".format(home=home)}
data = {}
if os.path.isfile(p):
    try:
        with open(p) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("!! settings.json invalid JSON — creating fresh one.")
data["statusLine"] = entry
with open(p, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(":: statusLine configured in", p)
PYEOF

# ── Test render ────────────────────────────────────────────────────────────────

say "Testing render..."
T5H=$(( $(date +%s) + 7200 ))
T7D=$(( $(date +%s) + 259200 ))
printf '{
  "model": {"id": "claude-sonnet-4-6", "display_name": "Sonnet 4.6"},
  "output_config": {"effort": "high"},
  "workspace": {"current_dir": "%s"},
  "context_window": {
    "used_percentage": 38,
    "total_input_tokens": 9000,
    "total_output_tokens": 3200,
    "cache_read_input_tokens": 5400,
    "cache_creation_input_tokens": 800,
    "max_tokens": 200000
  },
  "cost": {"total_duration_ms": 420000},
  "rate_limits": {
    "five_hour": {"used_percentage": 8,  "resets_at": %d},
    "seven_day": {"used_percentage": 2,  "resets_at": %d}
  }
}' "$HOME" "$T5H" "$T7D" | python3 "$DEST"

# ── Done ───────────────────────────────────────────────────────────────────────

say "Done. Restart Claude Code to apply clauline."
say "To update later: python3 ~/.claude/clauline.py --update"
say "To uninstall:    bash install.sh --uninstall"
