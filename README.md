# clauline

Python3 statusline for Claude Code. Displays session stats — git status, model,
context usage, cost, duration, and rate limits — in a compact terminal bar.
No dependencies beyond the Python 3.8+ standard library.

## Preview

```
● myapp │ ⎇  main✓ │ Opus 4.7 ↑ │ ████████░░ 78% │ tok:45.2k │ cost:$1.23 │ dur:34m │ 5h:45% (↺1h 30m) · 7d:12% (↺2d)
```

The bar is fully colorized in the terminal. Colors shift green→yellow→red on the
context bar and rate-limit percentages. The dot pulses every second.

**Fields:**

1. Live pulsing dot
2. Current folder name
3. Git branch + clean (`✓`) / dirty (`✗`) indicator
4. Active model + effort level (`↑` high / `→` medium / `↓` low)
5. Context window usage bar (animated gradient, 10 blocks)
6. Total token count (input + output)
7. Session cost (actual if available, estimated otherwise)
8. Session duration
9. Rate limits — 5h window and 7-day window with reset countdown

## Requirements

- Python 3.8+
- Claude Code CLI
- Git (optional, for branch/status display)

## Installation

**Option A — curl one-liner:**

```bash
curl -fsSL https://raw.githubusercontent.com/vektor91/clauline/main/install.sh | bash
```

**Option B — via Claude Code prompt:**

Open Claude Code and run:

```
Install clauline from https://github.com/vektor91/clauline — clone the repo, run install.sh, and confirm the statusline is active.
```

**Option C — clone and install:**

```bash
git clone https://github.com/vektor91/clauline
cd clauline
bash install.sh
```

## Manual setup

```bash
cp clauline.py ~/.claude/clauline.py
chmod +x ~/.claude/clauline.py
```

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/clauline.py"
  }
}
```

Restart Claude Code to apply.

## Session cost estimation

If Claude Code exposes `cost.total_cost_usd` in the statusLine payload, that
value is used directly. Otherwise, cost is estimated from token counts using
known Claude pricing — Opus 4.7: $15/$75 per MTok in/out, Sonnet 4.6: $3/$15,
Haiku 4.5: $0.80/$4.

## License

MIT — Alberto Gil ([vektor91](https://github.com/vektor91))
