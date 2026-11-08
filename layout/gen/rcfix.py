#!/usr/bin/env python3
"""Remove the double-counted coupling C from a magic R+C extraction (pex_*.sh rc).

    python3 layout/gen/rcfix.py <rc.spice> <out.spice> [--check <c-only.spice>]

Problem (found 2026-11-08, docs/rc_extraction_fix.md): on every labelled net (the ports, e.g. a0..a4, vg, vbn)
and every net extresist splits into sub-nodes (<net>.t<i> / <net>.n<i>), the C to VSS equals the net's *total* C
(as in the C-only extraction, coupling included), while ext2spice also writes the net's coupling caps to other
nets. So these nets carry their coupling twice: once as coupling, once lumped to VSS. (The .sim node C that
extresist starts from is the lumped total.) Unlabelled internal nets are not affected (checked: lsdiv lg, ls, q1).

Fix: for each such net N (not VSS), K = its coupling C to all non-VSS nets, S = its C to VSS; every N-to-VSS cap
is scaled by (S - K) / S. The total C of N then equals the C-only extraction's, and the coupling stays where it
is. --check compares every net's total C, and its C to VSS, with a C-only extraction of the same GDS.
"""
import re
import sys
from collections import Counter, defaultdict

SUB = re.compile(r"^(.+)\.[tn]\d+$")
UNIT = {"": 1, "f": 1e-15, "p": 1e-12, "n": 1e-9, "a": 1e-18}


def base(n):
    m = SUB.match(n)
    return m.group(1) if m else n


def val(v):
    m = re.fullmatch(r"([-\d.eE+]+)([fpna]?)", v)
    return float(m.group(1)) * UNIT[m.group(2)]


def lines(path):
    out = []
    for ln in open(path).read().splitlines():
        if ln.startswith("+") and out:
            out[-1] += " " + ln[1:].strip()
        else:
            out.append(ln)
    return out


def caps(ls):
    for i, ln in enumerate(ls):
        if ln[:1] in "Cc" and not ln.lower().startswith(".") and len(ln.split()) >= 4:
            t = ln.split()
            yield i, t[1], t[2], val(t[3])


def totals(ls, vss="VSS"):
    tot, gnd = Counter(), Counter()
    for _, a, b, c in caps(ls):
        a, b = base(a), base(b)
        if a == b:
            continue
        tot[a] += c; tot[b] += c
        if b == vss:
            gnd[a] += c
        if a == vss:
            gnd[b] += c
    return tot, gnd


def main():
    src, dst = sys.argv[1], sys.argv[2]
    chk = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    ls = lines(src)
    split = set()
    for ln in ls:
        if ln.lower().startswith(".subckt"):
            split.update(t for t in ln.split()[2:] if "=" not in t)     # ports (labelled nets)
        for tok in ln.split()[1:3]:
            if SUB.match(tok):
                split.add(base(tok))
    split.discard("VSS")
    K, S, idx = Counter(), Counter(), defaultdict(list)
    for i, a, b, c in caps(ls):
        A, B = base(a), base(b)
        if A == B:
            continue
        for n, o in ((A, B), (B, A)):
            if n in split:
                if o == "VSS":
                    S[n] += c; idx[n].append(i)
                else:
                    K[n] += c
    scale = {}
    for n in sorted(split):
        if S[n] <= 0:
            continue
        k = max(0.0, (S[n] - K[n]) / S[n])
        if S[n] < K[n]:
            print(f"WARN {n}: C to VSS {S[n] * 1e15:.2f} fF < coupling {K[n] * 1e15:.2f} fF; VSS caps set to 0")
        scale[n] = k
        for i in idx[n]:
            t = ls[i].split()
            t[3] = f"{val(t[3]) * k * 1e15:.6g}f"
            ls[i] = " ".join(t)
    ls.insert(1, f"* rcfix.py: split-net C to VSS scaled by (S - K) / S on {len(scale)} nets (coupling double count removed)")
    open(dst, "w").write("\n".join(ls) + "\n")
    print(f"{len(scale)} nets corrected (ports + split nets); e.g. " + ", ".join(
        f"{n} {S[n] * 1e15:.2f}->{S[n] * scale[n] * 1e15:.2f} fF" for n in sorted(scale, key=lambda n: -S[n])[:6]))
    if chk:
        t1, g1 = totals(ls)
        t0, g0 = totals(lines(chk))
        worst = []
        for n in sorted(set(t0) & set(t1)):
            if n == "VSS" or t0[n] < 1e-16:
                continue
            worst.append((abs(t1[n] / t0[n] - 1), n))
        worst.sort(reverse=True)
        print("check against C-only: worst |total C ratio - 1| " + ", ".join(
            f"{n} {t1[n] * 1e15:.2f}/{t0[n] * 1e15:.2f} fF" for _, n in worst[:6]))
        return 0 if not worst or worst[0][0] < 0.05 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
