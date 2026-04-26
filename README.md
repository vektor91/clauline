# clauline

Python3 statusline for Claude Code. Displays session stats — git status, model,
context usage, cache efficiency, cost, duration, compaction warnings, and rate
limits — in a compact terminal bar. No dependencies beyond Python 3.8+ stdlib.

## Preview

```
● myapp │ ⎇  main✓ │ Sonnet 4.6 ↑ │ ████████░░ 78% /200k ⚠ │ cache:71% │ tok:45.2k │ cost:$1.23 │ dur:34m @14:30 │ compact:1x ⟳ │ quota  5h:45% (↺1h 30m) · 7d:12% (↺2d)
```

The bar is fully colorized. Colors shift green→yellow→red on context, cache, and
quota. The dot pulses every second.

**Fields:**

| Segment | Description |
|---------|-------------|
| `●` | Live pulsing dot |
| folder | Current folder name |
| `⎇  branch✓/✗` | Git branch + clean/dirty |
| model + `↑↓→` | Active model + effort level |
| `think:` | Extended thinking budget (when active) |
| context bar | Usage bar, percentage, max tokens, `⚠` at >80% |
| `cache:XX%` | Cache hit rate — higher = fewer tokens billed at full price |
| `tok:` | Total tokens this session |
| `cost:` | Session cost (actual if available, estimated otherwise) |
| `dur:Xm @HH:MM` | Duration + session start time |
| `compact:Nx ⟳` | Context compaction count (quality risk indicator) |
| `tools:N` | Tool calls this session |
| `quota` | Rate limits — 5h and 7-day windows with reset countdown |

## Token efficiency signals

Three signals tell you when to act for fewer tokens and better quality:

- **`cache:XX%`** — how much of your input came from cache (cheap). Below 30%:
  context isn't being reused well, consider restructuring or using `/compact`.
- **`compact:Nx ⟳`** — how many times context was auto-compacted. Each
  compaction loses information and degrades recall. If you see `2x`, start a
  fresh session.
- **`⚠` on the context bar** — fires at >80% usage. Quality degrades here as
  the model struggles to attend to the full context. Reset now, not after.

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

```
Install clauline from https://github.com/vektor91/clauline — clone the repo, run install.sh, and confirm the statusline is active.
```

**Option C — clone and install:**

```bash
git clone https://github.com/vektor91/clauline
cd clauline
bash install.sh
```

## Update

```bash
python3 ~/.claude/clauline.py --update
```

Downloads the latest version, backs up the current one.

## Uninstall

```bash
bash install.sh --uninstall
```

Removes `~/.claude/clauline.py`, cleans `statusLine` from `settings.json`.

## Configuration

Create `~/.claude/clauline.json` to override defaults. All keys are optional:

```json
{
  "segments": {
    "dot":         true,
    "folder":      true,
    "git":         true,
    "model":       true,
    "thinking":    true,
    "context_bar": true,
    "cache":       true,
    "tokens":      true,
    "cost":        false,
    "duration":    true,
    "compaction":  true,
    "tools":       true,
    "rate_limits": true
  },
  "pricing": {
    "opus":   [15.0, 75.0],
    "sonnet": [3.0, 15.0],
    "haiku":  [0.80, 4.0]
  },
  "warn_ctx_pct": 80,
  "max_width": 0
}
```

`max_width: 0` means auto-detect terminal width. If the bar is too wide, lower-
priority segments are dropped from the right.

### Per-project config

Place a `.clauline` file (same JSON format) in any project root. It overrides
the user config for that project only:

```json
{
  "segments": {
    "cost": false,
    "rate_limits": false
  }
}
```

## Session cost estimation

If Claude Code exposes `cost.total_cost_usd` in the statusLine payload, that
value is used directly. Otherwise cost is estimated from token counts using
Claude pricing with cache-aware calculation:

- Cache reads billed at ~10% of input price
- Cache writes billed at ~125% of input price
- Remaining tokens at full input price

Current defaults — Opus 4.7: $15/$75 per MTok in/out, Sonnet 4.6: $3/$15,
Haiku 4.5: $0.80/$4. Override in config if pricing changes.

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

## License

MIT — Alberto Gil ([vektor91](https://github.com/vektor91))
