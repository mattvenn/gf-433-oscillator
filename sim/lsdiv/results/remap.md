# 433.92 MHz codes on the extracted core, with the level shifter + /4 on a0

From `sim/lsdiv/remap.py` (27 °C, VDD 3.3 V; data `sim/lsdiv/results/remap.csv`).

| corner | f code 0 / 31 at 1.65 V (MHz) | 433.92 code at 1.65 V | f there (MHz) | sch map code | RC, no LS | codes covering 433.92 with vctrl 0–3.3 V (f range MHz) | worst ls duty % | ÷4 exact |
|---|---|---|---|---|---|---|---|---|
| tt | 191 / 697 | 13 | 441.6 | 9 | 12 | 11 (396–464), 12 (413–479), 13 (430–494) | 51.5 | yes |
| ss | 172 / 643 | 15 | 436.2 | 11 | 14 | 13 (399–447), 14 (414–461), 15 (429–475) | 53.0 | yes |
| ff | 215 / 760 | 10 | 430.5 | 7 | 10 | 9 (392–485), 10 (412–503), 11 (431–520) | 52.8 | yes |
| sf | 186 / 706 | 12 | 426.9 | 9 | – | 11 (400–461), 12 (417–477) | 52.2 | yes |
| fs | 191 / 682 | 13 | 433.1 | 9 | – | 12 (403–474), 13 (419–489) | 52.0 | yes |
