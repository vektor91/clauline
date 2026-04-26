#!/usr/bin/env python3
import sys
import json
import os
import subprocess
import time
import re
import copy
import urllib.request
import shutil

VERSION = "2.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/vektor91/clauline/main/clauline.py"
STATE_FILE  = os.path.expanduser("~/.claude/clauline_state.json")

RESET = "\033[0m"
BOLD  = "\033[1m"

def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "segments": {
        "dot":         True,
        "folder":      True,
        "git":         True,
        "model":       True,
        "thinking":    True,
        "context_bar": True,
        "cache":       True,
        "tokens":      True,
        "cost":        True,
        "duration":    True,
        "compaction":  True,
        "tools":       True,
        "rate_limits": True,
    },
    "pricing": {
        "opus":   [15.0, 75.0],
        "sonnet": [3.0,  15.0],
        "haiku":  [0.80,  4.0],
    },
    "warn_ctx_pct": 80,
    "max_width":    0,
}

def _deep_merge(base, override):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v

def load_config(cwd):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for path in [
        os.path.expanduser("~/.claude/clauline.json"),
        os.path.join(cwd, ".clauline"),
    ]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    _deep_merge(cfg, json.load(f))
            except Exception:
                pass
    return cfg

# ── Auto-update ────────────────────────────────────────────────────────────────

def do_update():
    dest = os.path.abspath(__file__)
    print(f"Fetching {UPDATE_URL} ...")
    try:
        ts  = time.strftime("%Y%m%d-%H%M%S")
        bak = f"{dest}.bak.{ts}"
        shutil.copy2(dest, bak)
        with urllib.request.urlopen(UPDATE_URL, timeout=10) as r:
            content = r.read()
        with open(dest, "wb") as f:
            f.write(content)
        print(f"Updated to latest. Backup: {bak}")
    except Exception as e:
        print(f"Update failed: {e}")
    sys.exit(0)

# ── Session state (start time) ─────────────────────────────────────────────────
# Detects new session when duration_ms decreases (reset) or is absent (fresh open).

def get_session_start(current_duration_ms):
    now = int(time.time())
    try:
        state = {}
        if os.path.isfile(STATE_FILE):
            with open(STATE_FILE) as f:
                state = json.load(f)
        last_dur   = state.get("last_duration_ms", 0)
        start_time = state.get("start_time", now)
        if not current_duration_ms or current_duration_ms < last_dur:
            start_time = now
        with open(STATE_FILE, "w") as f:
            json.dump({"last_duration_ms": current_duration_ms or 0,
                       "start_time": start_time}, f)
        return start_time
    except Exception:
        return now

# ── Visual helpers ─────────────────────────────────────────────────────────────

def live_dot():
    frame  = int(time.time()) % 4
    colors = [(40,170,80),(80,215,120),(140,255,180),(80,215,120)]
    r,g,b  = colors[frame]
    bold   = BOLD if frame == 2 else ""
    return f"{bold}{rgb(r,g,b)}●{RESET}"

def folder_segment(cwd):
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    name = os.path.basename(cwd) if cwd != "~" else "~"
    return f"{rgb(180,210,255)}{name}{RESET}"

def git_segment(cwd):
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain=v1", "--branch"],
            timeout=2, capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        lines = result.stdout.splitlines()
        if not lines:
            return None
        m = re.match(r"^##\s+([^\.]+)", lines[0])
        branch = re.sub(r"^No commits yet on\s+", "", m.group(1) if m else "?")
        dirty  = len(lines) > 1
        sym    = f"{rgb(255,140,0)}✗{RESET}" if dirty else f"{rgb(80,215,120)}✓{RESET}"
        return f"⎇  {rgb(200,180,255)}{branch}{RESET}{sym}"
    except Exception:
        return None

# ── Model parsing ──────────────────────────────────────────────────────────────

def parse_model(model_obj):
    model_id = (model_obj or {}).get("id", "")

    # New format:  claude-{family}-{major}-{minor}[-suffix]
    m = re.match(r"claude-(opus|sonnet|haiku)-(\d+)-(\d+)", model_id, re.IGNORECASE)
    if m:
        family = m.group(1).lower()
        return family, f"{family.capitalize()} {m.group(2)}.{m.group(3)}"

    # Legacy format: claude-{major}[-{minor}]-{family}-{date}
    m = re.match(r"claude-(\d+)-?(\d*)-(opus|sonnet|haiku)", model_id, re.IGNORECASE)
    if m:
        family = m.group(3).lower()
        major  = m.group(1)
        minor  = m.group(2)
        label  = f"{family.capitalize()} {major}" + (f".{minor}" if minor else "")
        return family, label

    display = (model_obj or {}).get("display_name", "")
    if display:
        fm = re.search(r"(opus|sonnet|haiku)", display, re.IGNORECASE)
        return (fm.group(1).lower() if fm else None), display

    return None, "Claude"

def effort_arrow(effort):
    return {"high": "↑", "low": "↓", "medium": "→", "med": "→"}.get(
        (effort or "").lower(), "")

def model_segment(model_obj, effort):
    family, label = parse_model(model_obj)
    arrow  = effort_arrow(effort)
    color  = {"opus": rgb(220,160,255), "sonnet": rgb(120,200,255),
               "haiku": rgb(150,255,200)}.get(family, rgb(200,200,200))
    out = f"{color}{label}{RESET}"
    if arrow:
        out += f" {rgb(255,220,100)}{arrow}{RESET}"
    return out

# ── Thinking budget ────────────────────────────────────────────────────────────

def thinking_segment(out_cfg):
    thinking = (out_cfg or {}).get("thinking") or {}
    budget = thinking.get("budget_tokens")
    used   = thinking.get("used_tokens")
    if not budget:
        return None
    color = rgb(220,160,255)
    if used:
        pct = int(used / budget * 100)
        return f"think:{color}{fmt_tokens(used)}/{fmt_tokens(budget)} {pct}%{RESET}"
    return f"think:{color}on{RESET}"

# ── Context bar ────────────────────────────────────────────────────────────────

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def ctx_bar_segment(ctx, warn_pct):
    used_pct   = ctx.get("used_percentage") or 0
    max_tokens = ctx.get("max_tokens") or ctx.get("context_window_size")
    filled     = min(10, (int(used_pct * 10 + 50)) // 100)
    shimmer    = int(time.time()) % 13
    blocks     = []
    for i in range(10):
        pos = (2 * i + 1) * 5
        r   = pos * 255 // 50 if pos <= 50 else 255
        g   = 255              if pos <= 50 else max(0, (100 - pos) * 255 // 50)
        b   = 0
        if i < filled:
            if i == shimmer:
                r, g, b = min(255, r+60), min(255, g+60), min(255, b+60)
            blocks.append(f"{rgb(r,g,b)}█{RESET}")
        else:
            blocks.append(f"{rgb(80,80,80) if i == shimmer else rgb(50,50,50)}░{RESET}")

    bar   = "".join(blocks)
    pc    = rgb(255,80,80) if used_pct > warn_pct else rgb(255,220,80) if used_pct > 60 else rgb(120,220,120)
    out   = f"{bar} {pc}{int(used_pct)}%{RESET}"
    if max_tokens:
        out += f" {rgb(120,120,140)}/{fmt_tokens(max_tokens)}{RESET}"
    if used_pct >= warn_pct:
        out += f" {BOLD}{rgb(255,80,80)}⚠{RESET}"
    return out

# ── Cache efficiency ───────────────────────────────────────────────────────────

def cache_segment(ctx):
    hit   = ctx.get("cache_read_input_tokens") or 0
    write = ctx.get("cache_creation_input_tokens") or 0
    total = ctx.get("total_input_tokens") or 0
    if total == 0 or (hit == 0 and write == 0):
        return None
    pct   = hit / total * 100
    color = rgb(120,220,120) if pct >= 60 else rgb(255,220,80) if pct >= 30 else rgb(255,120,80)
    return f"cache:{color}{int(pct)}%{RESET}"

# ── Tokens ─────────────────────────────────────────────────────────────────────

def token_segment(ctx):
    total = (ctx.get("total_input_tokens") or 0) + (ctx.get("total_output_tokens") or 0)
    return f"tok:{rgb(180,200,255)}{fmt_tokens(total)}{RESET}"

# ── Cost ───────────────────────────────────────────────────────────────────────

def _estimate_cost(family, ctx, pricing):
    if family not in pricing:
        return None
    inp_p, out_p = pricing[family]
    inp   = ctx.get("total_input_tokens") or 0
    out   = ctx.get("total_output_tokens") or 0
    hit   = ctx.get("cache_read_input_tokens") or 0
    write = ctx.get("cache_creation_input_tokens") or 0
    # Cache reads cost ~10% of input price; cache writes ~125%
    base  = max(0, inp - hit - write)
    return (base  * inp_p / 1_000_000 +
            out   * out_p / 1_000_000 +
            hit   * inp_p * 0.10 / 1_000_000 +
            write * inp_p * 1.25 / 1_000_000)

def _fmt_cost(usd):
    if usd is None:
        return f"cost:{rgb(180,180,180)}—{RESET}"
    if usd < 0.01:
        return f"cost:{rgb(150,255,150)}<$0.01{RESET}"
    if usd < 1.0:
        return f"cost:{rgb(150,255,150)}${usd:.2f}{RESET}"
    return f"cost:{rgb(255,220,100)}${usd:.1f}{RESET}"

def cost_segment(cost_obj, model_obj, ctx, pricing):
    actual = (cost_obj or {}).get("total_cost_usd")
    if actual is not None:
        return _fmt_cost(actual)
    family, _ = parse_model(model_obj)
    return _fmt_cost(_estimate_cost(family, ctx, pricing))

# ── Duration + session start ───────────────────────────────────────────────────

def _fmt_duration(ms):
    if ms is None:
        return "—"
    s = int(ms / 1000)
    if s < 60:
        return f"{s}s"
    m = s // 60
    h = m // 60
    return f"{h}h{m%60}m" if h > 0 else f"{m}m"

def duration_segment(cost_obj):
    ms  = (cost_obj or {}).get("total_duration_ms")
    dur = _fmt_duration(ms)
    start_ts  = get_session_start(ms)
    start_str = time.strftime("%H:%M", time.localtime(start_ts))
    return f"dur:{rgb(180,210,255)}{dur} @{start_str}{RESET}"

# ── Compaction ─────────────────────────────────────────────────────────────────

def compaction_segment(data):
    n = data.get("compaction_count") or data.get("context_compactions") or 0
    if not n:
        return None
    color = rgb(255,80,80) if n >= 2 else rgb(255,200,60)
    return f"compact:{color}{n}x ⟳{RESET}"

# ── Tool calls ─────────────────────────────────────────────────────────────────

def tools_segment(data):
    n = data.get("tool_use_count") or data.get("total_tool_uses") or 0
    if not n:
        return None
    return f"tools:{rgb(200,180,255)}{n}{RESET}"

# ── Rate limits ────────────────────────────────────────────────────────────────

def _fmt_reset(ts):
    if not ts:
        return "—"
    diff = ts - int(time.time())
    if diff <= 0:
        return "<1m"
    m = diff // 60
    h = m // 60
    d = h // 24
    if d >= 1:
        return f"{d}d" if h % 24 == 0 else f"{d}d {h%24}h"
    if h >= 1:
        return f"{h}h" if m % 60 == 0 else f"{h}h {m%60}m"
    return f"{m}m" if m >= 1 else "<1m"

def _quota_color(pct):
    if pct > 85:
        return f"{BOLD}{rgb(255,80,80)}"
    if pct > 60:
        return f"{BOLD}{rgb(255,200,60)}"
    return f"{BOLD}{rgb(80,220,100)}"

def rate_limits_segment(rl):
    five  = (rl or {}).get("five_hour", {})
    seven = (rl or {}).get("seven_day", {})
    fp, fts = five.get("used_percentage") or 0, five.get("resets_at") or 0
    sp, sts = seven.get("used_percentage") or 0, seven.get("resets_at") or 0
    fs = f"{_quota_color(fp)}{int(fp)}%{RESET} (↺{_fmt_reset(fts)})"
    ss = f"{_quota_color(sp)}{int(sp)}%{RESET} (↺{_fmt_reset(sts)})"
    return f"quota  5h:{fs} · 7d:{ss}"

# ── Responsive width ───────────────────────────────────────────────────────────

SEP     = f" {rgb(80,80,100)}│{RESET} "
SEP_VIS = 3

def _strip_ansi(s):
    return re.sub(r"\033\[[^m]*m", "", s)

def _vis_len(s):
    return len(_strip_ansi(s))

def _fit(segments, max_width):
    if max_width <= 0:
        return segments
    while len(segments) > 3:
        total = sum(_vis_len(s) for s in segments) + SEP_VIS * (len(segments) - 1)
        if total <= max_width:
            break
        segments = segments[:-1]
    return segments

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if "--update" in sys.argv:
        do_update()
        return

    try:
        raw  = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}

        model_obj = data.get("model", {})
        out_cfg   = data.get("output_config", {})
        workspace = data.get("workspace", {})
        ctx       = data.get("context_window", {})
        cost_obj  = data.get("cost", {})
        rl        = data.get("rate_limits", {})

        cwd = workspace.get("current_dir", os.getcwd())
        cfg = load_config(cwd)
        seg = cfg["segments"]

        try:
            term_w = os.get_terminal_size().columns
        except Exception:
            term_w = cfg.get("max_width", 0)

        parts = []
        if seg.get("dot",         True): parts.append(live_dot())
        if seg.get("folder",      True): parts.append(folder_segment(cwd))
        if seg.get("git",         True):
            g = git_segment(cwd)
            if g: parts.append(g)
        if seg.get("model",       True): parts.append(model_segment(model_obj, out_cfg.get("effort")))
        if seg.get("thinking",    True):
            t = thinking_segment(out_cfg)
            if t: parts.append(t)
        if seg.get("context_bar", True): parts.append(ctx_bar_segment(ctx, cfg.get("warn_ctx_pct", 80)))
        if seg.get("cache",       True):
            c = cache_segment(ctx)
            if c: parts.append(c)
        if seg.get("tokens",      True): parts.append(token_segment(ctx))
        if seg.get("cost",        True): parts.append(cost_segment(cost_obj, model_obj, ctx, cfg["pricing"]))
        if seg.get("duration",    True): parts.append(duration_segment(cost_obj))
        if seg.get("compaction",  True):
            c = compaction_segment(data)
            if c: parts.append(c)
        if seg.get("tools",       True):
            t = tools_segment(data)
            if t: parts.append(t)
        if seg.get("rate_limits", True): parts.append(rate_limits_segment(rl))

        print(SEP.join(_fit(parts, term_w)))

    except Exception:
        print(f"{rgb(40,170,80)}●{RESET} clauline error")

if __name__ == "__main__":
    main()
