---
name: uknc-darkroom
description: Build, change, and verify the native A Dark Room port in this UKNC MC0511 repository, including Russian resources, PDP-11 assembly, scene compilation, RT-11 SAV startup/exit, and emulator scenarios.
---

Read `AGENTS.md` and `.Codex/docs/handover.md` relative to the repository root.
Use `.Codex/docs/platform.md` for memory, video, keyboard, and timing changes;
use `.Codex/docs/fidelity.md` when comparing behavior with upstream.

## Development loop

1. Edit `src/` or a generator under `tools/`. The SAV, DAT and RT-11 disk must remain reproducible
   from readable sources. `build/darkroom.mac` is concatenated/relaxed output.
2. Run `make build`. Resolve assembler/linker errors before using symbol tools.
   `python3 tools/syms.py LABEL` gives the current address in octal.
3. Run the relevant scenarios, then `make verify` for a completed gameplay or
   platform change. Tests execute the assembled game on UKNCBTL.
4. For RT-11 or platform changes, test STOP and Help exits, `DIR`, repeated
   `R DARKRM`, PPU allocation reuse, and moved/missing/mismatched DAT files.
   Keep CPU monitor vectors intact; restore/free the PPU before `.EXIT`.
5. For a visible change, use `make shot` or a scenario screenshot and inspect it.
   `SCREEN_BUF` snapshots decode to logical Russian text; they do not establish
   that the palette or framebuffer looks correct.
   Keep the UKNC loading-screen font: 8×11 ROM glyphs, 12-scanline row pitch.
   `tools/font_extract.py` reproduces `src/res/font8x11.txt` from the pinned ROM;
   `tools/font_gen.py` compiles it. Verify Cyrillic mapping and actual pixels.
   For focus/shortcut changes, inspect the six-pixel square snake, static white/gray
   location frames, arrow selection, Enter actions, and cleanup across pages.
   Check top-right Help, room status spacing, and that compact tab frames use only
   blank font scanlines. Help and blocked shortcuts have no frame; hidden shortcuts are silent and inert.
   Gray recipes retain the full plane-1 glyph and duplicate it in plane 2. Verify
   Left/Right worker assignment, nonselectable automatic gatherers, and 56-pixel cooldown fills at non-multiples of eight,
   zero/full states, timer-specific durations, attack speed buffs and removal
   on view changes. Resource counts are not cooldowns and must remain numeric.
6. `make run` starts the interactive SDL player. `make shot` is headless; it is
   not a substitute for retaining the playable runner.

## Content and scene work

Compare with the pinned JavaScript in `orig/adarkroom/script/`, not an assumed
older release. Recipes and encounters are in `src/res/upstream.json`. Explicitly
run `make extract` only when regenerating that checked-in extraction.

Add untranslated text to `src/res/ru-extra.txt` as `English key|Russian text`.
Use `src/res/ui.json` for native interface strings. The compiler rejects missing
translations. The DAT header pairs the file with its SAV; change both together. All in-game prose must fit the KOI-7 font and scene row limits.

Keep scene prose within four rows, above choices/costs and the five-row event
log (rows 18–22). Notification producers must call `NOTIFY` immediately after
setting `NOTICE`; drawing must not consume or restart messages. Check independent
30-second current-message expiry, 15-second maximum fade after displacement,
and preservation of multiple events generated in one tick. Repeated identical
messages must leave only the first row bright; further arrivals must not refresh
old timers. Never reset all LOG_SHADE values to white on ordinary redraws.
Older entries dim immediately and fade through grayscale as they age; the newest
stays white for 25 seconds before its final fade. Check actual RGB pixels, first
glyph scanlines, unchanged text at different shades, white UI/footer, Help without a stocks sidebar and with frozen game/log timers, hidden-log
views, and palette restoration on RT-11 exit. Do not dither or erode the font.

Scene IDs and resource offsets are generated. Use `build/catalog.json` in tools;
use emitted `EV_*`, `R_*`, `B_*`, `F_*` constants in assembly. Keep effect hooks
explicit: a new onLoad/onChoose function must have an audited native mapping.

## Native test scenarios

`tools/test_support.py` supplies `Scenario`: set named state, send physical
scancodes, call native routines, and snapshot memory. Its `callcpu` facility is
implemented in the headless emulator, never in the released game. Use seeded
states to reach rare branches, but retain keyboard-only opening tests.

For persistence changes, run `tools/verify_saves.py` and the full suite. Validate
all five slots, overwrite/reboot, exact state/scene/PRNG/rollback, paused timers,
corrupt/truncated/incompatible files, disk-full preservation, UI cleanup and
RT-11 exits. Save-enabled scenarios must preserve boot/system/game files; never
write test saves into the release disk. Preserve manual slot files during build/clean.
Default builds reserve debug slots 2/3 from src/res/debug-saves.json; back up
manual replacements. --no-debug must omit old generated fixtures as well as new
ones, while preserving manual slots. Check native expedition departure and ship
liftoff from those presets, deterministic outputs, and document schema changes
in GAMESTATE.md. GNU Make forwards the custom flag as `make build -- --no-debug`
or `make run -- --no-debug`; the Python builder accepts it directly.

A test should assert a rule (atomic payment, a mine unlock, a returned bag,
a cooldown, a disk record), not merely repeat generator output. Hardware I/O
needs actual emulator evidence. A headless frame is 1/25 s, not 1/50 s.

Keep documentation honest about deliberate adaptations and unverified hardware.
Do not claim browser-identical behavior or real-machine validation from a boot
screenshot or a handful of injected states.
