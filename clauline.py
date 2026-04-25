#!/usr/bin/env python3
import sys
import json
import os
import subprocess
import time
import re

RESET = "\033[0m"
BOLD  = "\033[1m"

def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def live_dot():
    frame = int(time.time()) % 4
    colors = [(40,170,80),(80,215,120),(140,255,180),(80,215,120)]
    r,g,b = colors[frame]
    bold = BOLD if frame == 2 else ""
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
        branch_line = lines[0]  # e.g. "## main...origin/main"
        m = re.match(r"^##\s+([^\.]+)", branch_line)
        branch = m.group(1) if m else "?"
        # strip leading "No commits yet on " prefix
        branch = re.sub(r"^No commits yet on\s+", "", branch)
        dirty = len(lines) > 1
        if dirty:
            status_sym = f"{rgb(255,140,0)}✗{RESET}"
        else:
            status_sym = f"{rgb(80,215,120)}✓{RESET}"
        return f"⎇  {rgb(200,180,255)}{branch}{RESET}{status_sym}"
    except Exception:
        return None

def parse_model(model_obj):
    model_id = (model_obj or {}).get("id", "")
    m = re.match(r"claude-(opus|sonnet|haiku)-(\d+)-(\d+)", model_id, re.IGNORECASE)
    if m:
        family = m.group(1).lower()
        major  = m.group(2)
        minor  = m.group(3)
        return family, f"{family.capitalize()} {major}.{minor}"
    display = (model_obj or {}).get("display_name", "")
    if display:
        fam_m = re.search(r"(opus|sonnet|haiku)", display, re.IGNORECASE)
        family = fam_m.group(1).lower() if fam_m else None
        return family, display
    return None, "Claude"

def effort_arrow(effort):
    e = (effort or "").lower()
    return {"high": "↑", "low": "↓", "medium": "→", "med": "→"}.get(e, "")

def model_segment(model_obj, effort):
    family, label = parse_model(model_obj)
    arrow = effort_arrow(effort)
    color = {
        "opus":   rgb(220,160,255),
        "sonnet": rgb(120,200,255),
        "haiku":  rgb(150,255,200),
    }.get(family, rgb(200,200,200))
    parts = f"{color}{label}{RESET}"
    if arrow:
        parts += f" {rgb(255,220,100)}{arrow}{RESET}"
    return parts

def ctx_bar_segment(ctx):
    used_pct = ctx.get("used_percentage", 0)
    filled = min(10, (int(used_pct * 10 + 50)) // 100)
    shimmer_pos = int(time.time()) % 13
    blocks = []
    for i in range(10):
        pos = (2 * i + 1) * 5  # center % of this block (5,15,25,...,95)
        if pos <= 50:
            r = pos * 255 // 50
            g = 255
        else:
            r = 255
            g = max(0, (100 - pos) * 255 // 50)
        b = 0
        if i < filled:
            if i == shimmer_pos:
                r = min(255, r + 60)
                g = min(255, g + 60)
                b = min(255, b + 60)
            blocks.append(f"{rgb(r,g,b)}█{RESET}")
        else:
            if i == shimmer_pos:
                blocks.append(f"{rgb(80,80,80)}░{RESET}")
            else:
                blocks.append(f"{rgb(50,50,50)}░{RESET}")
    bar = "".join(blocks)
    pct_color = rgb(255,100,100) if used_pct > 85 else rgb(255,220,80) if used_pct > 60 else rgb(120,220,120)
    return f"{bar} {pct_color}{int(used_pct)}%{RESET}"

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def token_segment(ctx):
    total = ctx.get("total_input_tokens", 0) + ctx.get("total_output_tokens", 0)
    return f"tok:{rgb(180,200,255)}{fmt_tokens(total)}{RESET}"

PRICING = {
    "opus":   (15.0, 75.0),
    "sonnet": (3.0,  15.0),
    "haiku":  (0.80,  4.0),
}

def estimate_cost(family, ctx):
    if family not in PRICING:
        return None
    inp_price, out_price = PRICING[family]
    inp_tok = ctx.get("total_input_tokens", 0)
    out_tok = ctx.get("total_output_tokens", 0)
    return (inp_tok * inp_price + out_tok * out_price) / 1_000_000

def fmt_cost(usd):
    if usd is None:
        return f"cost:{rgb(180,180,180)}—{RESET}"
    if usd < 0.01:
        return f"cost:{rgb(150,255,150)}<$0.01{RESET}"
    if usd < 1.0:
        return f"cost:{rgb(150,255,150)}${usd:.2f}{RESET}"
    return f"cost:{rgb(255,220,100)}${usd:.1f}{RESET}"

def cost_segment(cost_obj, model_obj, ctx):
    actual = (cost_obj or {}).get("total_cost_usd")
    if actual is not None:
        return fmt_cost(actual)
    family, _ = parse_model(model_obj)
    estimated = estimate_cost(family, ctx)
    return fmt_cost(estimated)

def fmt_duration(ms):
    if ms is None:
        return "—"
    s = int(ms / 1000)
    if s < 60:
        return f"{s}s"
    m = s // 60
    h = m // 60
    if h > 0:
        return f"{h}h{m % 60}m"
    return f"{m}m"

def duration_segment(cost_obj):
    ms = (cost_obj or {}).get("total_duration_ms")
    return f"dur:{rgb(180,210,255)}{fmt_duration(ms)}{RESET}"

def fmt_reset_time(ts):
    if not ts:
        return "—"
    now = int(time.time())
    diff = ts - now
    if diff <= 0:
        return "<1m"
    minutes = diff // 60
    if minutes < 1:
        return "<1m"
    hours = minutes // 60
    days  = hours  // 24
    if days >= 1:
        leftover_h = hours % 24
        return f"{days}d" if leftover_h == 0 else f"{days}d {leftover_h}h"
    if hours >= 1:
        leftover_m = minutes % 60
        return f"{hours}h" if leftover_m == 0 else f"{hours}h {leftover_m}m"
    return f"{minutes}m"

def pct_color(pct):
    if pct > 85:
        return f"{BOLD}{rgb(255,80,80)}"
    if pct > 60:
        return f"{BOLD}{rgb(255,200,60)}"
    return f"{BOLD}{rgb(80,220,100)}"

def rate_limits_segment(rl):
    five  = (rl or {}).get("five_hour", {})
    seven = (rl or {}).get("seven_day", {})

    fp  = five.get("used_percentage", 0)
    fts = five.get("resets_at", 0)
    sp  = seven.get("used_percentage", 0)
    sts = seven.get("resets_at", 0)

    fc = pct_color(fp)
    sc = pct_color(sp)
    fr = fmt_reset_time(fts)
    sr = fmt_reset_time(sts)

    five_str  = f"{fc}{int(fp)}%{RESET} (↺{fr})"
    seven_str = f"{sc}{int(sp)}%{RESET} (↺{sr})"
    return f"5h:{five_str} · 7d:{seven_str}"

SEP = f" {rgb(80,80,100)}│{RESET} "

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}

        model_obj  = data.get("model", {})
        out_cfg    = data.get("output_config", {})
        workspace  = data.get("workspace", {})
        ctx        = data.get("context_window", {})
        cost_obj   = data.get("cost", {})
        rl         = data.get("rate_limits", {})

        cwd = workspace.get("current_dir", os.getcwd())

        segments = [live_dot()]
        segments.append(folder_segment(cwd))

        git = git_segment(cwd)
        if git:
            segments.append(git)

        segments.append(model_segment(model_obj, out_cfg.get("effort")))
        segments.append(ctx_bar_segment(ctx))
        segments.append(token_segment(ctx))
        segments.append(cost_segment(cost_obj, model_obj, ctx))
        segments.append(duration_segment(cost_obj))
        segments.append(rate_limits_segment(rl))

        print(SEP.join(segments))
    except Exception:
        dot = f"{rgb(40,170,80)}●{RESET}"
        print(f"{dot} clauline error")

if __name__ == "__main__":
    main()
