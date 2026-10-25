# Tools and reproducibility

Run commands from the repository root. Build and test artifacts are local to
`build/` and `tmp/`. Nothing installs packages or writes outside the project.

## Normal use

```sh
make build
make run
make release
make shot
make verify
python3 tools/syms.py HP FIRE SCENE_BASE RESIDENT_END
python3 tools/uknc_control.py keys
python3 tools/uknc_control.py play ENTER --wait 100 --shot tmp/fire.png
```

`make build` produces DARKRM.SAV, DARKRM.DAT and the RT-11 disk image.
`make run` requires a working graphical session and the SDL2 runtime. It invokes
`bin/ukncbtl/uknc-play` with the built floppy and bundled ROM, not a screenshot
command. STOP/Escape exits the game to RT-11; closing the window exits the emulator.
The generated STARTS.COM sets `TT SCOPE,QUIET`, retains the USR/EXIT NOSWAP
settings and runs `R DARKRM`. At the prompt, type `R DARKRM`
to play again, or `DIR` to inspect the volume. `--no-autoboot` leaves firmware selection to
the user; `--frames N` permits a bounded launcher smoke test.

For unattended smoke testing of SDL initialization only:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy bin/ukncbtl/uknc-play \
  --rom bin/ukncbtl/uknc_rom.bin --disk build/darkroom.dsk --frames 2
```

The dummy driver proves neither window appearance nor keyboard interaction.
`make shot` uses the headless runner; it creates `tmp/start.png` when Pillow is
available. Verification requires Pillow for framebuffer color inspection.

## Rebuilding host tools

```sh
make toolchain
python3 tools/build_toolchain.py --only macro11
python3 tools/build_toolchain.py --only headless
```

The script clones pinned revisions from `tools/sources.lock.json` under `tmp/`,
applies the two assembler patches, builds with Make/GCC/G++, and copies binaries
and licenses into `bin/`. The `headless` option rebuilds both emulator runners.
SDL2 runtime ABI declarations are supplied in `sdl2_min.h`, so no SDL development
headers are required. A fresh clone needs Git/network access. Subsequent builds
reuse the local source directories. For a clean source rebuild, remove those
specific generated directories under `tmp/` first.

The included binaries were built for Linux x86-64. Another host architecture
needs a local tool build and may need changes to the SDL runtime linker name.

## Upstream extraction

The readable `src/res/font8x11.txt` is extracted from the bundled UKNC ROM,
using its original loading-screen font. To reproduce it, run:

```sh
python3 tools/font_extract.py
```

The extractor checks the ROM fingerprint before reading the glyph table at
PPU 0120170 (file offset 020170). Regular builds compile the checked-in text
resource with `tools/font_gen.py`; they do not extract the ROM each time.
Verification compares the opening framebuffer against the ROM's exact glyphs.

Scenario screenshots also write `.text-plane` and `.overlay-plane` files with
the visible 23,040 bytes of planes 1 and 2. Verification checks firmware glyphs
independently from the animated focus dots and shortcut underlines. Relaunch
comparisons remove the overlay so a different animation phase is not mistaken
for missing or stale text.

Scenarios run disposable `tmp/<name>-run.dsk` copies. RT-11 may write temporary
memory to its existing SWAP.SYS file; `Scenario.execute()` checks that no bytes
outside that extent change. The release image under `build/` stays untouched.

`orig/adarkroom` is the pinned reference checkout. The entire external checkout is ignored; the extracted native resources remain versioned.
The checked-in `src/res/upstream.json` makes regular builds offline and independent
of Node. To deliberately regenerate it from the reference, use:

```sh
make extract
make build
```

Node.js is required for extraction. If the reference checkout is absent, clone
the URL in `tools/sources.lock.json` to `orig/adarkroom` and check out the recorded
commit before extracting. Do not silently track a moving branch.

Changed callbacks trigger the `hook-audit.json` guard. Audit their target
semantics before updating that ledger. Missing translations are listed in
`build/missing-translations.json` and cause a failed build.

## Emulator scenarios

`tools/test_support.py` supplies `Scenario` for physical keys, symbol-addressed
RAM changes, native routine calls, dumps and screenshots. `tools/verify.py`
groups meaningful gameplay invariants. A scenario log is `tmp/NAME.log`, its
script is `tmp/NAME.script`; snapshots are 64 KiB CPU RAM files.

Raw runner commands include:

```text
run 900
press 030
run 30
press 153
run 1100
screenshot tmp/game.bmp
dumpcpu 0 65536 tmp/game.bin
quit
```

`run` takes frame counts (25 per simulated second). Keycodes and addresses are
octal. `callcpu ADDRESS [R0 R1 R2 R3 R4 R5]` runs a native subroutine with a
scratch stack and return breakpoint. It advances real PPU/FDD hardware during
the call. See [platform.md](platform.md) for its limits.

## Failures

- Missing tools: rebuild with `make toolchain`, retaining the error log.
- Failed assembly or object relocation: fix source, not generated files.
- Stale symbols: rebuild; `syms.py` rejects listings older than source/tools.
- Missing video/audio driver: run from a graphical session, or use headless
  verification for work that does not require an interactive window.
- Slow firmware startup in another emulator: select disk 1 and press ВВОД.
- Missing/incompatible DAT: keep the matching DARKRM.SAV and DARKRM.DAT on
  the current DK: volume. Startup prints a diagnostic and returns to RT-11.
- Disk error: the game uses the monitor's file handler and its retries. A returned
  read error restores the console and exits. A nonresponding device can still
  block within the OS handler; there is no host-side I/O bypass.


## RT-11 image and SAV tools

```sh
python3 tools/rt11fs.py ls build/darkroom.dsk
python3 tools/rt11fs.py get build/darkroom.dsk DARKRM.SAV tmp/check.SAV
python3 tools/savlink.py build/darkroom.obj tmp/check.SAV --stack 1000
```

`rt11fs.py put`/`rm` change their input image: use a copy under `build/` or `tmp/`,
never the supplied original. The build preserves the base boot/system extents,
adds normal files, and edits STARTS.COM. `savlink.py` supports this single absolute
module, applies internal relocations, rejects unresolved globals, and writes the
RT-11 SAV header and load bitmap. SYSMAC.SML supplies the real monitor macros.

`Scenario.command('DIR')` and `Scenario.command('R DARKRM')` type Latin RT-11
commands through physical UKNC key events. The SDL player uses the same logical
Latin mapping. Snapshot files include CPU `.bin` and PPU `.ppu` memory for checking
restoration. `rt11_roundtrip()` verifies exit using keys, not a forced CPU jump.

`RUN DARKRM` uses the current DK: volume and is the portable command when copying
both game files to another volume. `R DARKRM` defaults to SY:; the generated boot
disk uses it because DK: and SY: are the same there. The scene file is explicitly
looked up on DK:. See DEC's [System Internals Manual, RUN/R loading](https://www.bitsavers.org/pdf/dec/pdp11/rt11/v5.6_Aug91/AA-PD6NA-TC_RT-11_System_Internals_Manual_Aug91.pdf).

## Save/load development

F1 maps to UKNC К1 (010), F2 to К2 (011). `uknc-play --keymap` reports the actual
mapping; `uknc_control.py` accepts F1/F2 or K1/K2. The modal uses arrows and Enter;
Tab/AP2 or Escape cancels. Ordinary Escape still exits to RT-11.

Default `make build` and `make run` refresh debug slots 2/3 from
`src/res/debug-saves.json`. Other manual saves carry forward; replaced manual
slot 2/3 files are backed up under `tmp/player-save-backups/`. Use
`make build -- --no-debug` / `make run -- --no-debug` (or `ARGS=--no-debug`) to
omit generated presets and preserve all manual slots. The Python builder accepts
`--no-debug` directly. `make clean` retains a disk containing slots. Save files
from a changed build are retained but rejected by the compatibility check. Copy
the whole disk or extract DRSAVn.DAT with rt11fs.py for backups.

`python3 tools/verify_saves.py` runs focused native persistence scenarios.
`python3 tools/verify_travel.py` checks encounter/defeat acknowledgement, paused
clocks, physical combat/hunger/thirst deaths, framed glyphs, saved/rebooted dialogs
and STOP/DIR/relaunch. The full suite includes these scenarios.
`Scenario(..., save_writes=True)` allows slot creation/replacement and verifies
all protected system/game files and boot data. Keep the default strict disk
check for non-save tests.

`tools/branches.py` starts with long branches and shrinks only ranges proven by
the current assembly listing; it repeats until stable. Macro-entry branch targets
remain long because macro expansions use their own listing line numbers.
`syms.py` ignores macro IF expression values when resolving a bare routine label
before a monitor macro; those values are not instruction addresses.


`tools/debug_saves.py` compiles JSON through native MAP_INIT/CAPACITIES/WEIGH,
SNAPSHOT_WORLD and SV_SAVE on a disposable disk. Cached files under build/debug
are verified by hash; reserved-header markers distinguish presets from manual
saves. `python3 tools/verify_debug_saves.py` exercises real load/departure/liftoff,
filtering, Make option forwarding and deterministic recompilation. See
[GAMESTATE.md](../../GAMESTATE.md) for the full authoring schema.

## Release packaging and full-screen pages

`make release` builds normally, then exports `build/darkroom-v1.0.0.dsk` with
all slots empty and `build/darkroom-v1.0.0-debug.dsk` with only generated slots
2/3. `tools/release.py --out-dir PATH` exports the current matching SAV/DAT disk
to another directory. It strips all manual saves and clears free extents, while
preserving the working disk. `release.json` records version, slots and SHA-256.

`tools/verify_pages.py` checks splash/ending keys, frozen clocks, original ROM
glyphs, full framebuffer cleanup, restart, persistence and RT-11 exit/relaunch.
`tools/verify_release.py` checks both exported images, free-space clearing, all
protected files, empty slot UI and native loading of debug presets. Both run in
`make verify`. Scenario normally acknowledges the splash before test actions;
use `Scenario(..., splash=True)` to test startup itself. After an explicit
`command('R DARKRM')`, acknowledge the splash with `key('ENTER',50)` as needed.
`uknc_control.py boot` / `make shot` leave the splash visible; `play` acknowledges
it before executing the requested game keys.

## Player documentation and exploration checks

`README.md` is the Russian player guide; technical documentation moved to
`AI-DEVELOPERS.md`. `python3 tools/readme_shots.py` captures base, travel and
battle PNGs directly from native emulator scenarios into `readme/`. It avoids
late-game unlocks and checks that no late-game labels leak into the captions'
screens. The map/battle use a prepared early expedition; the home view follows
physical opening keys and real game ticks. No screenshot retouching is used.

`tools/verify_exploration.py` covers the live eight-way compass without altering
fog, all three roaming-enemy terrain pools at distances 10/11/20/21, original
health/attack-delay data, and a continuous near-field random stream. Its report
is `tmp/encounter-pools.json`; both checks run in `make verify`.

The release `.gitignore` excludes `bin/`, `build/`, `tmp/`, external checkouts,
compiled artifacts and upstream-style editor/cache files. It retains the
supplied base RT-11 disk and SYSMAC.SML required for a source build. Tool license
copies live under `tools/licenses/`, outside ignored binary output directories.
