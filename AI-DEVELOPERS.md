# A Dark Room — Электроника МС-0511 / УКНЦ

A native PDP-11 port of [A Dark Room](https://github.com/doublespeakgames/adarkroom)
by Michael Townsend and doublespeak games. The game runs as a classic RT-11 `DARKRM.SAV` program, with a
`DARKRM.DAT` scene file. The supplied 800 KiB disk boots RT-11 and runs it. Its interface and story are Russian, in uppercase Cyrillic,
with the UKNC loading screen's original 8×11 font, white on black after startup.
Five manual save slots are available through F1/К1 (load) and F2/К2 (save).
STOP/Escape returns to RT-11; in a save/load window it cancels the window.

```sh
make build     # DARKRM.SAV, DARKRM.DAT and darkroom.dsk under build/
make run       # build and launch the playable SDL UKNC emulator
make release   # export V1.0.0 clean and debug-only disks
make shot      # headless boot; tmp/start.png
make verify    # native emulator regression scenarios
```

`make run` opens a window, automatically selects the floppy in the UKNC firmware,
and lets RT-11 run the assembled game via `STARTS.COM`. It needs a graphical desktop and the SDL2 runtime.
Host tools are built locally with `make toolchain` and excluded from Git. Building the disk needs Python 3.10+;
verification also needs Pillow. Rebuilding the host tools needs Git, Make, GCC/G++,
patch, and network access on the first build. No system packages are installed by
the build scripts. See [tool instructions](.Codex/docs/tools.md).

For a fresh source checkout, run `make toolchain` before `make build`. This
fetches the pinned assembler/emulator sources into ignored `tmp/` and installs
local binaries/firmware under ignored `bin/`. The checked-in extraction in
`src/res/upstream.json` is sufficient for ordinary game builds; the upstream
checkout `orig/adarkroom/` is excluded from Git and needed only for `make extract`
or fidelity audits. Keep the immutable `orig/RT11BASE.DSK` and required
`orig/loader/source/SYSMAC.SML` as build inputs. Other loader examples, binaries
and images are excluded. Source patches, runner code, resources and `readme/*.png`
remain versioned; release disks are published separately from source control.

## Running from RT-11

Copy **both** `build/DARKRM.SAV` and `build/DARKRM.DAT` to the current `DK:`
volume, then type:

```text
RUN DARKRM
```

Press **STOP** on the UKNC or **Escape** in the SDL player to return to the
RT-11 prompt from normal game screens. Alternatively, open **0 — Help** and press
**Enter** on the exit action. You can then run `DIR`, other programs, or
`RUN DARKRM` again. On the supplied boot volume, `R DARKRM` also works. Each launch shows the credits splash; press Enter to begin, then F1 to continue a saved game. The normal RT-11 console palette
is restored on exit; the game UI stays white on black with a fading gray event log.

The build uses the provided `orig/RT11BASE.DSK` (RT-11SJ V05.04 G). Its system
files and boot sector are retained. The supplied disk and `orig/loader/` stay
unchanged. Other RT-11 configurations and physical hardware remain untested.

The bottom-right version label comes from `GAME_VERSION` in
[src/version.mac](src/version.mac). Edit that constant when changing the release
identifier; the current release displays `V1.0.0` with original ROM Latin capitals.

## Playing

Press **Enter** on the opening splash, then **Enter** to light the fire. Keep the room warm, gather wood when the forest
opens, and let the stranger recover. Buildings, jobs, crafting, trading,
expeditions, and later discoveries appear as you progress.

- **Up / Down:** select an action; **Enter:** activate it.
- **Left / Right:** decrease/increase `< N >` in Jobs and expedition packing.
- **1–9:** switch unlocked panels; **0:** help, or inventory while exploring.
- **Help:** clears the stocks sidebar and pauses gameplay while open.
- **Help → Space:** browse all home stocks and learned perks.
- **Space:** context action: stoke/gather,
  attack, eat on the map, or take available loot.
- **Arrows on the map or in flight:** move. **Tab** maps to UKNC **АР2**, back.
- **F1 / К1 — load; F2 / К2 — save:** choose one of five slots with Up/Down,
  then Enter. The window pauses gameplay; Tab/Escape cancels.
- **Escape / UKNC STOP:** exit to RT-11. Close the window to stop the emulator.

Displayed cooldowns use fixed 56-pixel white bars (seven character cells), shrinking with
pixel precision to empty when ready. Item/building quantities remain numbers.
Bag weight is displayed in
tenths to include light ammunition. See [KEYBOARD.md](KEYBOARD.md) for all controls.

A six-pixel snake follows a square before the selected interactive row. Location
tabs have static white/gray frames; unavailable recipes are gray. Hidden shortcuts
are silent. Help and save/load shortcuts sit on the top row.

Save slots are actual RT-11 files `DK:DRSAV1.DAT` through `DK:DRSAV5.DAT`, inside
`build/darkroom.dsk`. Each captures the current location, inventory, map, combat,
flight, timers, event history, random generator and expedition rollback state.
Selecting an occupied save slot replaces it. Loading rejects damaged files and
files from a different game build before changing current progress. There is no
automatic save. Default builds reserve slots **2 and 3** for debug checkpoints:
slot 2 is ready for the first expedition; slot 3 is ready to launch the spaceship.
Both open with their departure/liftoff action selected. Other manual slots carry
forward. A manual save replaced in slot 2/3 is backed up under
`tmp/player-save-backups/`.

Use `make build -- --no-debug` or `make run -- --no-debug` to omit generated
presets and retain all manual slots. `ARGS=--no-debug` is equivalent. GNU Make
requires the first `--` before the custom flag. `make clean` retains a disk
containing saves. Back up the disk image to keep a separate copy.

Edit [src/res/debug-saves.json](src/res/debug-saves.json) to change the presets.
[GAMESTATE.md](GAMESTATE.md) documents every parameter, range, prerequisite,
weight limit, generated field and save-preservation rule.

`make release` produces two distributable images without changing saves on the
working disk:

- `build/darkroom-v1.0.0.dsk`: all five save slots empty.
- `build/darkroom-v1.0.0-debug.dsk`: only generated expedition/ship slots 2/3.

Deleted save payloads are cleared from free disk space. Checksums are recorded in
`build/release.json`. Successful flight clears the screen for the ending; the
bottom row offers **1: New Game** and **2: Exit to OS**. New Game resets progress;
manual save files remain available.

## Implemented scope

The port includes the room and builder progression, forest and traps, population,
ten worker roles, production chains, crafting and trade, random village events,
the 61×61 world, exploration and supplies, twelve weapons, combat and perks,
mines, ruins and other landmarks, the Executioner branches and fabricator,
spaceship upgrades, a sixty-second debris flight, and both ending texts.

The compiler retains **273 scenes**, **46 building/crafting/trading/fabrication
recipes**, and their branching costs, loot and progression hooks from the pinned
upstream revision. Scene content is read from floppy as needed; the game logic
runs on the emulated UKNC CPU. No JavaScript engine or host-side game simulation
is used during play.

This is a hardware adaptation, not a browser-identical implementation. The map
terrain generator and flight geometry differ; the presentation uses paged keyboard
menus and condensed notifications. Browser music, visual transitions, online
services, and persistent prestige/score history are absent. Native quantities cap
at 30,000. See the detailed [fidelity notes](.Codex/docs/fidelity.md).

The event log shows five recent messages, newest first. Each arrival immediately
turns the previous current message gray and caps its remaining lifetime at
15 seconds. Older messages continue fading without restarting. The newest stays
white for 25 seconds, then fades before disappearing at 30 seconds. A new message
pushes the oldest out when all five rows are occupied.
The log stays visible across normal panels and encounters. Help and endings pause
its timers; flight hides the log while simulation continues.

## Development

The boot, video, cross-toolchain and emulator workflow follow the sibling
`../mc0511-elite` project. This repository builds independently of that directory.

| Location | Purpose |
| --- | --- |
| `src/*.mac`, `src/darkroom.list` | Native CPU/PPU assembly and module order |
| `src/res/` | Russian text, font, extracted upstream data, callback review ledger |
| `tools/` | Build, SAV linking, RT-11 volume tools, extraction, symbols and verification |
| `bin/` | Assembler, emulator runners, UKNC firmware, licenses |
| `orig/` | Pinned game source, supplied RT-11 base disk and loader reference |
| `.Codex/docs/` | Architecture, hardware, fidelity, tools and handover |
| `.agents/skills/uknc-darkroom/` | Reusable project development skill |
| `build/`, `tmp/` | Generated disk/listings and test evidence |

Start with [AGENTS.md](AGENTS.md) and the [handover](.Codex/docs/handover.md).
`make verify` covers actual boot/keyboard input, the monochrome framebuffer,
recipes, worker transactions, world landmarks, inventory, expedition rollback,
all RT-11 scene reads, weapons, milestones, the ending, console restoration,
`DIR` after exit, repeated launches, and data-file error handling. Focused tests seed RAM
and call native routines; they are not a complete unassisted playthrough.
Physical UKNC hardware has not been tested.

Upstream and tool revisions and licensing are recorded in
[THIRD_PARTY.md](THIRD_PARTY.md) and [tools/sources.lock.json](tools/sources.lock.json).


In ЖИТЕЛИ, ЛЕСНИК is the read-only pool of unassigned settlers. Left/Right on
a speciality returns people to that pool or takes people from it.
