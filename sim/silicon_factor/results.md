# GF silicon factor: tt_um_algofoogle_vgaringosc, extracted layout vs ttgf0p2 silicon

f_sim in MHz (C-extracted, 27 °C, 3.3 V). factor = f_silicon(chip 1) / f_sim.

| ring | stages | silicon chip 1 | chip 2 | sim typical | sim ss | sim ff | sim sf | sim fs | factor vs typical | silicon inside sim corners? |
|---|---|---|---|---|---|---|---|---|---|---|
| inv1x5 | 5 | 319.6 | 311.6 | 342.0 | 243.0 | 454.9 | 337.1 | 332.4 | 0.935 | yes |
| inv4x5 (unconfirmed) | 5 | 206.5 | 206.5 | 362.7 | 256.2 | 482.6 | 349.1 | 359.8 | 0.569 | no |
| t3 | 3 | 220.5 | 216.0 | 220.9 | 157.1 | 292.9 | 218.5 | 214.0 | 0.998 | yes |
| t5 | 5 | 196.2 | – | 197.7 | 140.7 | 261.8 | 195.4 | 191.5 | 0.993 | yes |
| t9 | 9 | 160.7 | – | 161.8 | 115.3 | 214.3 | 161.0 | 155.9 | 0.993 | yes |
| t33 | 33 | 77.7 | – | 77.6 | 55.2 | 103.0 | 77.0 | 74.9 | 1.001 | yes |
| t65 | 65 | 49.9 | – | 50.1 | 35.7 | 66.4 | 49.7 | 48.5 | 0.995 | yes |
| t161 | 161 | 23.7 | – | 23.9 | 17.0 | 31.6 | 23.6 | 23.1 | 0.994 | yes |

## rc check (typical)

- inv1x5: c 342.0 MHz, rc 341.9 MHz (-0.0 %); rc includes magic's port double count (docs/rc_extraction_fix.md), so treat as a lower bound on f
- t3: c 220.9 MHz, rc 220.8 MHz (-0.0 %); rc includes magic's port double count (docs/rc_extraction_fix.md), so treat as a lower bound on f
