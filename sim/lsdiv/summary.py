#!/usr/bin/env python3
"""Pair the no-block and block runs of build/lsdiv/ring_<runs>*.json into one markdown table, plus the /4 sweep.

    python3 sim/lsdiv/summary.py build/lsdiv/ring_main_c.json build/lsdiv/ring_robust_c.json ... [--div build/lsdiv/div.json]
Writes sim/lsdiv/results/summary.md and copies the json files there.
"""
import json, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "sim/lsdiv/results"


def main():
    args = sys.argv[1:]
    div = None
    if "--div" in args:
        i = args.index("--div"); div = args[i + 1]; del args[i:i + 2]
    RES.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in args:
        rows += json.load(open(f))["rows"]
        shutil.copy(f, RES / Path(f).name)
    key = lambda r: (r["corner"], r["temp"], r["code"], r["vdd"])
    base = {key(r): r for r in rows if r["block"] == "none"}
    out = ["| corner | T °C | VDD | code | f a0 no block MHz | f a0 with block MHz | Δf % | a0 swing V | LS out V | LS duty % | "
           "LS tr / tf ps | ÷4 f MHz | f a0 / f ÷4 | ÷4 duty % | P LS / ÷4+buf mW | warn |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["block"] == "none" or "error" in r:
            continue
        b = base.get(key(r))
        f0 = b["f_a0"] if b else float("nan")
        out.append(f"| {r['corner']} | {r['temp']} | {r['vdd']:.2f} | {r['code']} | {f0 / 1e6:.2f} | {r['f_a0'] / 1e6:.2f} | "
                   f"{100 * (r['f_a0'] / f0 - 1):+.2f} | {r['a0_min']:.2f}–{r['a0_max']:.2f} | {r['ls_min']:.2f}–{r['ls_max']:.2f} | "
                   f"{100 * r['ls_duty']:.1f} | {r['ls_tr'] * 1e12:.0f} / {r['ls_tf'] * 1e12:.0f} | {r['f_div'] / 1e6:.2f} | "
                   f"{r['div_ratio']:.4f} | {100 * r['div_duty']:.1f} | {r['p_ls'] * 1e3:.3f} / {r['p_div'] * 1e3:.3f} | "
                   f"{' '.join(r['warn'] + (b['warn'] if b else [])) or '-'} |")
    txt = "\n".join(out) + "\n"
    if div:
        d = json.load(open(div))
        shutil.copy(div, RES / Path(div).name)
        txt += "\n| corner | T °C | ÷4 max f_in (all pass from 150 MHz up) GHz | lowest passing f_in MHz | fails |\n|---|---|---|---|---|\n"
        for r in d["rows"]:
            bad = [f"{x['fin'] / 1e6:g}" for x in r["rows"] if not x["ok"]]
            txt += (f"| {r['corner']} | {r['temp']} | ≥ {r['fmax'] / 1e9:g} | {r['fmin'] / 1e6:g} | "
                    f"{', '.join(bad) or '-'} MHz |\n")
    (RES / "summary.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
