# A Dark Room for the UKNC / MC0511

Read `.Codex/docs/handover.md` first, then the relevant architecture or fidelity
notes. This is a native PDP-11 game, not a browser wrapper. `make build` must
produce `build/DARKRM.SAV`, `build/DARKRM.DAT` and an RT-11
`build/darkroom.dsk`; `make run` must launch that disk in the playable SDL
UKNC emulator. Keep both commands working.

## Scope and conventions

- Game text is Russian with uppercase KOI-7 glyphs on white-on-black video.
  The bottom-right GAME_VERSION constant in src/version.mac preserves its exact
  V1.0.0 spelling using the original ROM Latin capital glyphs.
  Older event-log entries fade through native grayscale. Unavailable recipes and
  inactive location frames are gray; other text stays white.
  Use the original UKNC firmware 8×11 font in `src/res/font8x11.txt`; retain the
  80×24 layout with a 12-scanline row pitch.
  Code, comments, documentation, and collaboration are English.
- Preserve the upstream game systems and data where practical. Five manual
  save/load slots are required: DK:DRSAV1.DAT through DK:DRSAV5.DAT. No analytics,
  web services, or browser UI are required. Preserve manual saves during builds;
  default debug builds reserve slots 2/3, backing up any manual replacements.
  `src/res/debug-saves.json` compiles through native routines at build time.
  `make build -- --no-debug` and `make run -- --no-debug` omit generated presets
  and preserve all manual slots. See GAMESTATE.md for the complete JSON schema.
- Work inside this repository. Host tool builds go under `tmp/`, binaries under
  `bin/`. Do not install host packages. Never push or commit without a request.
- Keep tools as reusable CLIs under `tools/`. Project skills belong in
  `.agents/skills/`; the user explicitly requested these.
- Do not copy the Elite project's game logic, stale status reports, or unrelated
  rules. Its reusable platform/tooling methodology is the reference.

## Implementation

- `src/darkroom.list` is assembly and memory order. RT-11 loads `RT_ENTRY` at
  octal `001000`. Keep the SAV header/bitmap valid, preserve monitor vectors,
  and use `.SETTO` before claiming game memory. `build/` is generated.
- Scene reads use `.LOOKU` / `.READW` on `DK:DARKRM.DAT`, never physical LBAs.
  Validate the DAT header before PPU takeover; exit with `.PURGE` and `.EXIT`.
- Preserve the supplied `orig/RT11BASE.DSK` and loader reference. Modify only
  a generated copy. Keep its boot/system files in place and append `R DARKRM`
  to STARTS.COM so `make run` still starts the game.
- STOP/Escape and Help → Enter must restore the PPU display/interrupt state,
  free its allocation, restore the terminal CSR and return to a usable prompt.
- `src/res/upstream.json` is the checked-in extraction from the pinned upstream.
  `tools/extract.mjs` regenerates it. Russian additions are in
  `src/res/ru-extra.txt`; native interface text is in `src/res/ui.json`.
- `tools/generate.py` emits recipes, worker rules, weapons, and disk scenes.
  New JS hook behavior needs an explicit compiler mapping and native effect;
  do not silently drop new functions or replace content with placeholders.
- `make verify` runs native emulator checks, not a host reimplementation of the
  game. Inspect screenshots when changing text, layout, video, or input.
- `tools/test_support.py` and `tools/syms.py` resolve the CURRENT listing. Never
  copy numeric addresses from an earlier build into tests.
- The selected interactive row uses a six-pixel snake moving around a 6×6 square
  in plane 2 inside the single character cell before its label. Preserve plane-1 glyphs and erase old dots.
  Usable numbered tabs have static 1-pixel frames: white for the current tab,
  gray for the others; Help and unavailable shortcuts have no frame. Hidden
  location shortcuts are silent and inert. Decorations stay below offset 155000.
  Disabled recipe glyphs use bit 7 in SCREEN_BUF and duplicate the intact glyph
  into plane 2 (palette index 6, gray). Clear stale bars before repainting text.
  Cooldown bars are 56 individual pixels wide, never character-sized steps; use
  live timers and the duration captured when an attack started. Keep quantities
  numeric. Worker assignments use Left/Right and `< N >`; gatherers are automatic.
- After setting `NOTICE`, call `NOTIFY` immediately. Five event rows occupy
  screen rows 18–22. The current message lasts at most 30 seconds; when displaced,
  its remaining lifetime is capped at 15 seconds and it dims immediately. Never
  restart other rows' fade timers or publish temporary white shades during a
  normal redraw. Keep ordinary
  content above them; scene prose is limited to four rows. Help, flight and
  endings use their full layouts and hide the log.
  LOG_SHADE controls per-row PPU palette/brightness tags. Preserve the original
  font pixels, keep fading inside rows 18–22, and restore white on hidden-log views.

- F1/К1 opens load; F2/К2 opens save. The modal freezes gameplay and event-log
  time. Enter uses the selected slot; AP2/Escape cancels. Save only at main-loop
  input boundaries. Include STATE_START..STATE_END, SEED, the scene window and
  both expedition rollback planes. Exclude monitor/PPU state and rebase clocks.
- Saves use channel 1 with a dedicated request area. ENTER/WRITW/CLOSE commits a
  completed new file; PURGE aborts failures without deleting the prior slot.
  Validate version/build identity, length and checksum before applying a load.
  Candidate staging starts at video offset 117000 and must end below 155000.
  Wait for the PPU hide acknowledgement before staging, and clear staging pixels
  before restoring the display. Keep channel 0 available for scene reads.

## Hardware and assembler traps

- MACRO-11 defaults to octal. Use a trailing dot for decimal literals, including
  8 and 9. Expressions evaluate left to right; use angle brackets explicitly.
- An even-register `MUL` overwrites the next register. `DIV` needs an even pair.
  A `MOV` changes condition codes. Branch immediately on the flags intended.
- A global label ends the scope of numeric local labels. `01$` equals `1$`.
- The build starts with long branches, then iteratively shrinks branches proven
  in range by the current assembler listing. Macro-entry targets remain long.
  Inspect the
  generated listing when debugging; source and generated instruction counts
  differ. A residual `G` relocation is an unresolved symbol, not valid code.
- The PPU block is relocated by firmware. Internal addresses must be PC-relative;
  immediate CPU addresses used through the video window are intentionally fixed.
- CPU address 0100 belongs to RT-11. Leave all monitor vectors intact. The
  previous standalone boot's vector patch and high stack would corrupt RT-11.
- CPU video plane offsets below 0100000 are CPU RAM. Drawing there corrupts code.
- A headless `run N` frame is 1/25 second, with two 50 Hz interrupts. Game ticks
  are 1/10 second. Do not infer game speed from host wall time.
- RT-11 reads use a dedicated request area/channel. A scene is loaded at 0124000;
  pointers into that window expire when the next scene is loaded.
- `callcpu` is an emulator-only test facility. It uses scratch stack 0126776 and
  return breakpoint 0126000. These must stay outside game allocations.

## Project skill

Use `.agents/skills/uknc-darkroom/SKILL.md` for build, content, and emulator work
in this repository. See `.Codex/docs/tools.md` for the actual commands.
