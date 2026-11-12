![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/lvs/badge.svg)

[![Made with Claude](https://img.shields.io/badge/Made%20with-Claude-D97757?logo=anthropic&logoColor=white)](https://claude.com/claude-code)

# 433 MHz VCO for an FM radio toolkit (GF180MCU, Tiny Tapeout)

A tunable 433.92 MHz current-fed ring oscillator with a 5-bit DAC, a fine-tune input and a divide-by-4 clock
output, with no inductors and no external components. It is the first part of an FM radio toolkit for the Zero to
ASIC Course.

- [Project datasheet page](docs/info.md)
- [Where the design is at, and what's next](STATUS.md)
- [Schematics](docs/schematics.md) and [top-level layout](docs/top_layout.md)

> **Radio regulations.** This is an experimental, uncertified transmitter. The antenna driver is off unless ui_in[5] / ui_in[6] enable it. The coarse code alone puts the ring anywhere in about 193–851 MHz, and until the RP2350 has tuned it, it can be tens of MHz away from 433.92 MHz, outside the narrow 433.05–434.79 MHz licence-exempt band. That range includes frequencies used by aviation, emergency services and the 406 MHz distress beacons. The output is close to a square wave: in simulation the 3rd harmonic (1.3 GHz) is −14 dBc and the 5th −23 dBc at the dipole, well above the band's spurious-emission limits. Power is low (about +6 dBm, 4 mW, into the dipole), but transmitting over the air may need an amateur radio licence (the 70 cm band is 420–450 MHz in the US, 430–440 MHz in the UK and much of Europe), and outside the amateur band it may not be legal at all. Measure the frequency and harmonics with an SDR or spectrum analyser first, keep transmissions short, and prefer a cabled link with an attenuator. Receiving is fine. You are responsible for following your local rules.

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Analog projects

For specifications and instructions, see the [analog specs page](https://tinytapeout.com/specs/analog/).

## Enable GitHub actions to build the results page

- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)

## What next?

- [Submit your design to the next shuttle](https://app.tinytapeout.com/).
- Edit [this README](README.md) and explain your design, how it works, and how to test it.
- Share your project on your social network of choice:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [@TinyTapeout](https://www.linkedin.com/company/100708654/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - X (formerly Twitter) [#tinytapeout](https://twitter.com/hashtag/tinytapeout) [@tinytapeout](https://twitter.com/tinytapeout)
  - Bluesky [@tinytapeout.com](https://bsky.app/profile/tinytapeout.com)
