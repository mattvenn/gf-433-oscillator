# Project rules: gf-433-oscillator

A tunable 433.92 MHz VCO, growing into an FM radio toolkit, on GF180MCU (Tiny Tapeout ttgf26c). Start with
**`STATUS.md`**: the current state, the next steps and where everything lives. Matt's personal preferences
(branding, writing style, audience) come from his user-level `~/.claude/CLAUDE.md`. If that is missing on this
machine, ask him to install his private claude-config repo.

## How Matt wants to work
- **This is a learning project.** Matt is learning VCO, ring-oscillator and RF design, and will explain it to others.
  His background is digital and the ASIC flow, plus earlier sky130 mixed-signal work.
  - Explain the *why* briefly in chat as results come in: the intuition and the trade-off, tied to our own numbers.
  - **Don't create or append to learning docs (`docs/learning.md` or similar) unless he asks.**
- **Use the project skill** `.claude/skills/mixed-signal-asic/` (the SKILL.md, the matching `references/*.md`, and
  tools from its `scripts/`). It is written for sky130, so adapt to gf180mcuD.
- **Delegate documents** (datasheets, write-ups) to a background subagent with a tight brief:
  - the most important specs only;
  - reuse existing data first;
  - capped sims and figures;
  - a time budget (about 10 minutes unless he says otherwise).
- **Plots:** Matt likes explanatory figures (for example `docs/tuning.md`). Put figures he wants kept under
  `docs/img/`, with a docs page that captions them.
- **Schematics:** xschem, generated from Python (`xschem/gen/`), drawn **like textbook schematics with wires**
  (labels only for ports and supplies). They are viewed in xschem-viewer, with links in `docs/schematics.md`. They
  are netlist-checked against the simulated circuit and the layout's LVS source (`xschem/gen/check.py`).
- **Commit and push only when Matt asks**, or as part of a task he asked for. Stage and commit in one command, never
  `git add -A`, and **never commit `sim.yaml`** (it holds the VNC password).

## Simulation policy
- **Corners:** iterate at **27 °C, VDD 3.3 V**, on the 3–4 bounding process corners. Run the full process set once
  per circuit change to find them.
  - Matt only cares about room-temperature operation. Use 20 / 35 °C only for drift checks.
  - 0 / 70 °C and VDD ±4.5 % are only for robustness checks (start-up) and **sign-off**.
  - **Sign-off** is full PVT plus Monte Carlo on the extracted layout.
  - Details: `docs/handoff_autonomy.md`, "Corner policy".
- **Where things run:**
  - **Short sims (under about 5 minutes) run locally.**
  - **Long runs go to the sim server** through a `docs/handoff_<topic>.md`, following `docs/handoff_autonomy.md`:
    - one driver started with `run_in_background`;
    - status and DONE/FAILED files;
    - a `Running: step N/M` line pushed at each step change;
    - a heartbeat;
    - write up and push straight after.
  - The handoff is the server agent's whole brief, so commit and push the scripts it needs first.
- **Agents in parallel:** each has its own clone (`gf433-sims`, `gf433-layout`) and owns its own directories.
  Commit only your own files, and `git pull --rebase` before pushing.
- **Judge runs by their output files and log tails, not by exit codes.** Check logs for "Transient op started" and
  "singular". Mutation-test every checker (LVS, netgen, antenna).

## Tool traps
- `tools/osic-mac` does **not** pass env vars into Docker: use `tools/osic-mac env K=V cmd`.
- Extract with **magic 8.3.642**: 8.3.684 drops substrate C.
- KLayout gf180 DRC: pass `feol=true beol=true`, because otherwise the deck can silently run zero rules.
- The GF180 ngspice models give one mismatch draw per instance, ignoring `m`. Split devices into unit instances for MC.
- Frequency in the current-fed ring must be measured at **mid-swing**: the ring swings vg…VDD, so it never crosses
  VDD/2.
- The tuning map (`map.csv`) reads about 1.3 % high against a settled ring. The extracted layout runs at about 0.87×
  the schematic.

## Public docs in this repo
These rules come from Matt's global config; they're repeated here because they matter for anything in `docs/`.
- Add the **Made with Claude** badge to anything likely to be shared publicly.
- Write **"Zero to ASIC Course"**, never just "Zero to ASIC".
- Use **Matt's technical-writing style** for reports and datasheets: plain and factual, every acronym expanded at
  first use, problem → fix → evidence, honest limits, and "Fig. N." captions that give the measured value.
