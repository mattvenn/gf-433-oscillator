# 433.92 MHz codes on the extracted core, with the level shifter + /4 on a0

From `sim/lsdiv/remap.py` (27 °C, VDD 3.3 V; data `sim/lsdiv/results/remap.csv`).

| corner | f code 0 / 31 at 1.65 V (MHz) | 433.92 code at 1.65 V | f there (MHz) | sch map code | RC, no LS | codes covering 433.92 with vctrl 0–3.3 V (f range MHz) | worst ls duty % | ÷4 exact |
|---|---|---|---|---|---|---|---|---|
| tt | 214 / 779 | 10 | 437.9 | 9 | 12 | 8 (383–465), 9 (404–483), 10 (424–501) | 53.0 | yes |
| ss | 193 / 718 | 12 | 436.6 | 11 | 14 | 10 (392–451), 11 (410–467), 12 (428–483) | 51.4 | yes |
| ff | 241 / 851 | 8 | 439.5 | 7 | 10 | 6 (371–485), 7 (395–505), 8 (418–525) | 54.1 | yes |
| sf | 208 / 790 | 10 | 438.8 | 9 | – | 8 (386–460), 9 (407–479), 10 (428–498) | 51.4 | yes |
| fs | 214 / 762 | 10 | 430.3 | 9 | – | 9 (394–480), 10 (413–498), 11 (433–515) | 54.7 | yes |
