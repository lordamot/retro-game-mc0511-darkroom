# Sources and licenses

## A Dark Room

- Author: Michael Townsend and contributors, doublespeak games.
- Source: https://github.com/doublespeakgames/adarkroom
- Revision: `1fada4620b6c66bd07bf15a3f1eb8223df8bc1d7`.
- License: Mozilla Public License 2.0, reproduced in [LICENCE.md](LICENCE.md)
  with an unofficial Russian translation first and the authoritative English
  text second.
- Reference checkout: `orig/adarkroom/`; extracted data: `src/res/upstream.json`.

The port adapts the upstream game rules, scene graphs and Russian translation.
Additional Russian strings are in `src/res/ru-extra.txt`; native interface text
is in `src/res/ui.json`. Native port source and generated game resources are
provided under MPL-2.0. Upstream notices remain in the reference source.
The upstream license does not permit replacing its covered source with an
MIT-only grant: MPL-2.0 sections 3.1 and 3.4 require retaining MPL terms and
the substance of license notices. Separately authored files may use other
terms where the necessary rights are held; this project retains MPL-2.0 for
the native port and generated game resources, subject to the third-party
exceptions below.

## UKNC platform and tools

The original standalone boot foundation, assembler conversion utilities, and emulator runner
foundation were copied from the local sibling `../mc0511-elite` project, then
adapted here. The game implementation was written for this port. Source files
under `tools/uknc-headless/` include the corresponding local runner changes.

UKNCBTL Qt emulator core:

- https://github.com/nzeemin/ukncbtl-qt
- Revision `3545c415756e0ec4e854599890792c663ac10bef`.
- LGPL-3.0; license in `tools/licenses/ukncbtl.txt`.
- The firmware file `uknc_rom.bin` is the image distributed by that upstream
  repository; its provenance is the original UKNC firmware, separate from the
  newly written port. Do not assume that the emulator's source license assigns
  ownership of the historical firmware.
- `src/res/font8x11.txt` contains 96 glyphs extracted from this firmware's
  loading-screen font by `tools/font_extract.py`, replacing the earlier Elite
  font. These glyphs share the historical firmware's provenance, not the port's
  newly written source license. Their table starts at PPU address 0120170;
  the extractor records and checks the bundled ROM's SHA-256.
- `make toolchain` retrieves the pinned source under `tmp/` and rebuilds the
  supplied headless and SDL runners. SDL2 is dynamically linked from the host.

Portable MACRO-11 assembler:

- Richard Krehbiel's assembler, https://github.com/shattered/macro11
- Revision `e35df877f996c9056a1a8c4ca919472b5ed8d0a4`.
- License in `tools/licenses/macro11.txt`.
- Two inherited memory-safety fixes are kept as readable patches in
  `tools/macro11-src/` and applied during toolchain builds.

Exact source revisions are machine-readable in `tools/sources.lock.json`.
Ordinary game builds use the checked-in resource extraction and locally built
tools. `make toolchain` fetches the pinned tool sources on first setup; binary
outputs and external checkouts are excluded from Git. The supplied RT-11 base
image and SYSMAC.SML remain explicit build inputs.


## Supplied RT-11 environment

The user supplied `orig/RT11BASE.DSK` (RT-11SJ V05.04 G) and `orig/loader/`.
These files are retained unchanged as reference/system inputs; their historical
system and tool licensing is separate from the port's MPL-2.0 source. The loader
example demonstrates `.LOOKU`, `.READW`, `.PURGE` and `.EXIT`; its SYSMAC.SML is
used to assemble the native RT-11 interface. The generated disk retains the base
system's boot sector, files and their extents.

`tools/rt11fs.py` and `tools/savlink.py` were copied from the local sibling
`../tang-uknc/tools/`. They provide the RT-11 volume and absolute-module SAV
handling. The FPGA-side `mnano/rt11sav.c` was consulted but is not part of the
runtime: this port runs under the real RT-11 monitor in the UKNC emulator.
