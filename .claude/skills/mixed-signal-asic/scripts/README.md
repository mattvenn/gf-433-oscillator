# Reusable scripts

Copy them into the new repo. They assume this layout, run from the repo root inside the tools image:
`layout/<block>.gds`, `xschem/<block>.sch`, `layout/ref/<block>.spice` (an optional LVS reference),
`layout/pex/`, and `build/` (gitignored).

| Script | Put in | What it does | Adapt |
|---|---|---|---|
| `osic-mac` | `tools/` | Runs a command in the pinned IIC-OSIC-TOOLS image: repo mounted at its own path, `.designinit` mounted, `.spiceinit` copied into build/, `OSIC_PDK_ROOT` override, direct exec inside the image | image tag; `DESIGNINIT` env (default `~/asic/.designinit`, example in `designinit.example`); it calls `tools/osic-inimage` when already in the image |
| `longrun` | `tools/` | Detached job → `build/<name>.log` + `build/<name>.done`, systemd-inhibit sleep where available | on the Mac wrap it in `caffeinate -i` |
| `sched.py` | `sim/rerun/` | CPU-budget job scheduler (threads, est, deps, lock, stagger, adopts orphans, live job-file reload, `--status`) | `--budget` = cgroup CPUs − 2 |
| `check.sh` | `layout/` | Block DRC (magic full + KLayout `sky130A_mr`), antenna on a flattened copy in a fresh session, density, netgen LVS that **fails on property errors** | std-cell lib name if not hd |
| `pex.sh` + `pexfix.py` | `layout/` | magic R+C extraction → `layout/pex/<b>.spice` with the schematic port order and the substrate tied to VSS | pin a magic version that keeps substrate C (8.3.642 did; 8.3.684 didn't) |
| `pexswap.py` | `tools/` | Swaps schematic `.subckt`s in a deck for the extracted ones | include path relative to build/ |
| `export_tt.sh` | `layout/` | gds/ + lef/ for TT, adding the `USE POWER/GROUND` fix | pass the `tt_um_…` name; source GDS path |
| `rawread.py` | `tools/` | numpy reader for ngspice raw files (binary/ascii, real/complex) | none |
| `xsch.py` | `tools/` | Write xschem schematics/testbenches from Python (lab_pins on pin coordinates, TT_MODELS + code blocks) | `LIB_PINS` for any new symbols |
| `kpcell_setup.sh` | `tools/` | Installs gdsfactory 8.5 in `build/pyold` for the sky130 KLayout pcells | drop it once the image matches |
| `render_gds.py` | `tools/` | KLayout batch GDS → PNG with the PDK .lyp | none |
| `gds_links.py` | `tools/` | Layout README with TT GDS viewer links and sizes | `RAW` URL |

Not copied because they are too project-specific, but worth rebuilding from the ideas in the
references: `lay.py` / `rows.py` (generator library), `route.py` (A* top router), `check_top.sh`
(staged tile checks + local precheck), `pex_tile.sh {lvs|c|rc}`, `check_pinout.py`, the floorplan page
(`layout/floorplan/page/`), and the power mesh flow (`sim/power/`). The originals are in
<https://github.com/mattvenn/ook-asic-radio> (`layout/`, `tools/`, `sim/power/`).
