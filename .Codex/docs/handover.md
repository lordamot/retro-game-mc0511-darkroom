# Handover

## Resume checkpoint — 2026-10-25

Startup terminal mode corrected: tools/build.py replaces the supplied
SET TT NOSCOPE with SET TT SCOPE in the generated STARTS.COM, retaining QUIET,
USR/EXIT NOSWAP and the final R DARKRM. The original base disk remains unchanged.
Working, clean and debug disks all contain SET TT SCOPE,QUIET. SAV, DAT and
manual slot 5 are byte-identical to the preceding build, so this packaging fix
does not change the save build identity. Release verification now explicitly
checks the startup command in both exports.
`make build` and full `make verify` passed 3,814 checks, including boot, saves,
STOP/Help exits, DIR and repeated relaunch. See tmp/scope-full-verify.log.
Refreshed final images match tested exports byte for byte; build/release.json
records clean SHA-256 a7c4961941f960778dab82cb626f8a339aa6ba69140f861b5a0e249a15ba95cb
and debug SHA-256 35c5bf8338a9ac6ed8ca37a34d139cbb2d995cbc4dbdb07ac40789798d5797e6.

Release preparation: previous README moved to AI-DEVELOPERS.md. The new README
is solely Russian player documentation: premise, settlement, supplies, combat,
controls and saves, without late-game spoilers. Native screenshots are committed
as readme/base.png, readme/travel.png and readme/battle.png (640×288 PNG), captured
by tools/readme_shots.py. They were visually inspected; no image retouching.
The .gitignore now excludes built binaries/images, external checkouts and caches,
while retaining our runner code/patches, resources, screenshots, orig/RT11BASE.DSK
and orig/loader/source/SYSMAC.SML. Tool license copies moved into tracked
tools/licenses/; the technical guide explains fresh-checkout make toolchain.
An isolated Git index under tmp/ignore-audit.git checked the inclusion rules;
no repository was initialized at the project root and no commit/push was made.

src/compass.mac now draws КОМПАС and an eight-way bearing beside the travel map.
It scans the native target landmark and uses the original 2:1 axis threshold,
relative to current player coordinates rather than the browser's home tooltip.
It does not reveal fog or add saved state. Includes ЗДЕСЬ and absent-target
cleanup. Resident end is 123644 octal, leaving 92 bytes before SCENE_BASE.

Encounter selection needed no gameplay correction: the native terrain/distance
pools match all eleven upstream definitions. Expanded checks cover forests,
fields and barrens at boundaries 10/11/20/21, plus a continuous PRNG stream;
health and attack delays match loaded records. The first 768-roll boundary
sample found each eligible enemy, including six birds and six two-headed
creatures at distance 10 in fields. tools/verify_exploration.py replaces the old
two-pool check; counts are recorded in tmp/encounter-pools.json. The continuous
64-roll field stream also produced both variants (seven birds, three creatures).
`make build` and full `make verify` passed 3,812 checks; see
tmp/readme-full-verify.log and tmp/verification.json. Both release images were
refreshed and match the tested exports byte for byte; the bounded SDL launch
passed. Clean SHA-256: ff2e6be967823d5680945f0c85c4187196d9acd47252a67c32d170661457981b.
Debug SHA-256: 2cdb520ad58900eff9d5cfb45a7f9f9fac17e9e58f5336e1c4ab1d4f0c7a9b5a.
The working disk and manual slot 5 remained unchanged during verification.
README relative links, PNG decoding and the final Git inclusion list passed
local audits.

V1.0.0 release: startup now shows a centered, unframed credits splash before
START initializes the game. It contains the requested greeting, Sergey Lemeshev /
CHATGPT CODEX port credit, MICHAEL TOWNSEND / DOUBLESPEAK GAMES and contributors,
official game/source URLs, and Пенза / 25 октября 2026. All visible text is
uppercase. Enter begins the game; STOP restores RT-11. Latin capitals use the
original ROM 100–137 glyphs in game font bank 140–177; Cyrillic mapping is
unchanged. GAME_VERSION is exactly V1.0.0.

Successful flight clears both planes and displays the standard or beacon ending
on black without heading, tabs, flight pixels or log. The bottom row has
1: НОВАЯ ИГРА and 2: ВЫХОД В ОС, with version at right. Ending clocks freeze.
New Game resets the stack and calls START; Exit uses RT_EXIT. F1/F2 preserve the
ending page across save/reboot/load. `src/pages.mac` owns these flows. Three
new DAT records follow the defeat records: splash 276, ending 277, beacon 278.
Long ending strings moved out of resident memory. Current SAV is 43,008 bytes /
84 blocks; DAT is 144,384 bytes / 282 blocks for 279 records. Resident end is
123260 octal, leaving 336 bytes before SCENE_BASE. START calls SV_CLEAR and
keeps its synchronized blank cache, avoiding a redundant 1,920-cell blank redraw
after acknowledging the splash or choosing New Game.

`make release` / `tools/release.py` exports darkroom-v1.0.0.dsk (all slots empty)
and darkroom-v1.0.0-debug.dsk (only generated slots 2/3), plus release.json with
SHA-256 hashes. It clears deleted save payloads in free extents and leaves the
working disk/manual saves untouched. Ordinary --no-debug still preserves manual
saves as before. `verify_pages.py` covers splash/ending pixels, keys, pause,
restart, persistence and OS relaunch; `verify_release.py` covers both exports,
protected files, cleared free space, empty-slot UI and loading the two presets.
Scenario acknowledges the splash by default; pass splash=True for startup tests.
Explicit R DARKRM relaunches require Enter to begin. `make shot` shows the splash.
Inspected screenshots: tmp/release-splash-splash.png, tmp/release-ending-end.png,
and tmp/release-ending-beacon-end.png. Focused page/release checks and the bounded
SDL launch passed. `make build` and full `make verify` passed all 2,081 checks;
see tmp/v1-full-verify.log and tmp/verification.json. Both final images in build/
match the natively verified exports byte for byte; build/release.json records
their checksums. Clean SHA-256: 71c15dd330daa857ccc4c6b2c4fd02b5b648d28289218bd6287e48d4586cfb1f.
Debug SHA-256: 2cf769add4a529dda62e94f008229afce029218550062b4aaed4b89b2aeae957.
The working disk remained unchanged during verification; manual slot 5 retains
5db56289963a5ea72dddacc0328812258d9c21766afdb44fc34b01fad965dd9e.
The fire-notification scenario explicitly resets TEMP_TIME to isolate cooling
from a simultaneous temperature/stranger notice after the faster startup.

Modal windows now use 48 columns (384 pixels, 60% screen width) and are centered
on both axes. Save/load progress has a 384×72 frame at (128,108), a centered
operation label and a 336-pixel fill. The picker and travel prompts share the
384×146 frame at (128,71); text wraps at 44 columns and the acknowledgement
button remains centered. Original combat prose stays wide; DAT header offset 26
points to its compact equivalent (native defeat records reuse their body).
Load staging starts at 117000 but SV_ADVANCE skips rows 9–14, walks rows 15–22,
then wraps before row 23 to row 0. The PPU hides only rows 0–8 and 15–22 before
acknowledging; the progress window and exact-case footer stay visible. The
17 hidden rows have 16,320 word positions for the 13,056-word padded candidate.
Shared immutable recipe cost lists and common frame code keep resident end at
123756 octal (18 bytes before SCENE_BASE); SAV is still 43,008 bytes / 84 blocks,
DAT 276 records / 277 blocks. Do not grow resident data without reclaiming space.
Focused checks passed: 101 save checks and 91 travel checks. Inspected actual
screenshots: tmp/save-progress-load-late.png, tmp/save-slots-empty.png,
tmp/travel-arrival-arrival.png and tmp/travel-defeat-defeat.png. The bounded
SDL dummy-driver launch passed. `make build` and full `make verify` passed:
1,937 checks; see tmp/center-full-verify.log and tmp/verification.json. The release
disk remained unchanged (SHA-256 0d4576b2c9908ef9c7abacbc33812f20ac78667fc414f7bc1f23a4aa1536083a);
manual slot 5 retains SHA-256 5db56289963a5ea72dddacc0328812258d9c21766afdb44fc34b01fad965dd9e.

Travel now pauses before every combat scene on a framed black dialog containing
the actual encounter description, ПРИГОТОВЬТЕСЬ К БОЮ! and a БОЙ button. Fresh
Enter starts the fight without an automatic player attack. Defeat clears the
screen and shows a framed explanation with ЖАЛЬ; combat, hunger and thirst have
distinct prose. Native rollback, lost supplies and return home still occur once;
the recovery cooldown stays frozen until acknowledgement. Held/queued keys cannot
skip these prompts. F1/F2 and STOP remain available; save/reboot/load preserves
the pending dialog. `travel-dialogs.mac` owns TR_MODE and composition. FRAME_RECT
is shared with the save picker and preserves all ROM glyph pixels.
The new defeat prose lives in three native DAT records appended after the 273
upstream scenes (276 records / 277 blocks total), authored through ui.json.
Resident end is 123744 octal, leaving 28 bytes before SCENE_BASE; SAV stays at
43,008 bytes / 84 blocks. Avoid increasing resident data without reclaiming space.
Focused checks: 90 travel checks and 868 existing layout/combat/edge checks pass.
Screenshots inspected: tmp/travel-arrival-arrival.png,
tmp/travel-defeat-defeat.png, tmp/travel-hunger-defeat.png and
tmp/travel-thirst-defeat.png. `tools/verify_travel.py` is also in the full suite.
`make build` and `make verify` pass: 1,931 checks, with the release disk unchanged.
Log: tmp/travel-full-verify.log. Held-repeat entry is explicitly tested inside
TICK. The disk relocation/error tests now derive the last record and file limit
from the current catalog/symbols instead of assuming the old 273-record bank.
The bounded SDL dummy-driver launch passed; manual slot 5 retains its prior hash.

Packing controls now use Left to return one item to home stores and Right to
take one into the bag. All packing quantities show `< N >`, including zero.
Held arrows repeat the transfer within native stock/capacity limits. Enter and
Space are inert on packing item rows; Enter on ОТПРАВИТЬСЯ and the existing 7
shortcut still depart. The shared horizontal ten-row jumps are removed from all
lists; Up/Down continues across pages. Worker adjustments and map/flight movement
retain their existing arrow behavior. Help and footers match the new controls.
Vitals now show ВЕС: carried/capacity without (0,1); weight values are unchanged.
Focused packing/worker verification passed 30 checks. Inspected screenshots:
tmp/packing-arrows-one.png, tmp/list-arrows-page.png and tmp/list-arrows-help.png.
Current resident end is 123200 octal, leaving 384 bytes before SCENE_BASE.
`make build` and full `make verify` pass: 1,834 checks, release disk unchanged;
see tmp/packing-arrows-full-verify.log and tmp/verification.json. The bounded
SDL dummy-driver launch passed; manual slot 5 retains its previous hash.

Combat now has a read-only АТАКА ПРОТИВНИКА row (row 7) with a live 56-pixel
enemy cooldown above the player weapons. ENEMY_SPAN captures the actual wait
at scene entry and each attack restart, including frenzy. The renderer reads
that span live; frenzy expiry cannot stretch an existing short wait. Stun uses
ПРОТИВНИК ОГЛУШЕН on that row, and meditation retains its visible status while
the clock pauses. Enemy misses now log ПРОТИВНИК ПРОМАХНУЛСЯ immediately.
Enemy death/explosion, leaving combat and modal transitions clean up the bar.
The lit-room heading is now ОЧАГ, as requested. Focused verification passed
66 checks; see tmp/enemy-cooldown-focused.log. Inspected screenshots include
tmp/enemy-cooldown-later.png, tmp/enemy-cooldown-miss.png,
tmp/enemy-cooldown-stun.png, tmp/enemy-cooldown-meditation.png and
tmp/location-fire-room.png. Resident end is now 123314 octal (308 bytes free).
`make build` and full `make verify` pass: 1,812 checks, release disk unchanged;
see tmp/enemy-cooldown-full-verify.log and tmp/verification.json. The bounded
SDL dummy-driver launch passed, and manual slot 5 retains its earlier hash.

Save/load now clears the slot picker before disk I/O and shows СОХРАНЕНИЕ... or
ЗАГРУЗКА... with a full-width progress bar. The bar occupies scanlines 84–93,
above load staging's hidden rows, and advances from actual completed blocks.
It reaches full only after CLOSE or validated load commit. Shared cleanup
removes all progress pixels on success and failure. SV_CLEAR seeds the cleared
character cache with spaces so the status appears without redrawing blanks.
`tools/verify_saves.py` covers physical-key progress, clean center pixels, frozen
timers, staging visibility, increasing fill, zero/full boundaries and cleanup.
Screenshots: tmp/save-progress-save-early.png, tmp/save-progress-save-late.png,
tmp/save-progress-load-late.png. Current resident end is 123114 octal, leaving
436 bytes before SCENE_BASE; SAV is 43,008 bytes / 84 blocks.
`make build` and `make verify` pass: 1,774 checks, including all persistence and
RT-11 exit/relaunch scenarios; see tmp/save-progress-full-verify.log. The release
disk remained unchanged during verification, and the existing manual slot 5
retains SHA-256 5db56289963a5ea72dddacc0328812258d9c21766afdb44fc34b01fad965dd9e.
A bounded SDL dummy-driver launch also passed. Actual busy, completed and error
screenshots were inspected. The focused run's shared temporary disk collided
with the full suite; the full suite subsequently completed all save tests in
isolation and is the authoritative result.

Latest small UI change: GAME_VERSION in src/version.mac is
`v.2026-10-25-2 beta`, shown right-aligned on row 23 in every game view, including
Help and save/load. DRAW_VERSION is shared by normal and modal composition.
The firmware font now includes codes 140–177 (Latin lowercase), preserving the
existing 64 glyphs and adding 32 original ROM glyphs. The combat hint is shorter
so the full hint and version fit with a separating space. Focused room/Help/modal
checks and the full suite pass; see tmp/version-verify.log.
Version screenshots: tmp/version-footer-room.png and tmp/version-footer-save.png.
UI regression probes now read the committed LOG_TEXT for fire notifications;
SCREEN_BUF may be mid-composition at a frame boundary. Worker-count and attack-bar
captures allow one additional settling frame to avoid inspecting reset menu/bar
scratch state during that same boundary.

The latest task adds baked debug saves and source-format documentation:

- `src/res/debug-saves.json` defines slot 2 (first expedition, TAB 6 / selection 0)
  and slot 3 (spaceship, TAB 7 / selection 2). Slot 2 has a valid 180/200 packed
  bag, first-expedition passive gear and home reserves. Slot 3 has hull 50,
  engines 5, ship/mining flags and 1,000 spare alloy.
- `tools/debug_saves.py` validates the JSON, resolves current symbols, and uses
  native MAP_INIT/CAPACITIES/WEIGH/SNAPSHOT_WORLD/SV_SAVE on a disposable disk.
  It verifies native capacity/vital limits and caches byte-verified outputs in
  build/debug. No host map generator or host native-save serializer was added.
- Default `make build` / `make run` refresh slots 2/3. Any manual save displaced
  there is backed up under tmp/player-save-backups. Other manual slots survive.
  Reserved header marker DRDEBUG1 distinguishes generated presets; manual native
  saves clear it. `make build -- --no-debug` and `make run -- --no-debug` omit
  generated presets, including those in the previous disk, and preserve all
  manual slots. ARGS=--no-debug and the direct Python flag are also supported.
  GNU Make requires the first -- before a custom goal/flag.
- GAMESTATE.md is the full schema/reference: every supported JSON field, ranges,
  default merge, resources, building caps, jobs, flags/perks, native-derived data,
  weight limits, compatibility and build/save-preservation behavior.
- Focused verification: 21 checks pass, including physical load/departure/move,
  launch/steer, native map landmarks, deterministic recompilation, filtering and
  Make forwarding. The actual no-debug build removed both presets; a default
  build restored them. Existing manual slot 5 remains byte-for-byte unchanged
  (SHA-256 5db56289963a5ea72dddacc0328812258d9c21766afdb44fc34b01fad965dd9e).
  Full verification passes; see tmp/debug-full-verify.log. Default debug fixtures
  are baked into the release image. An older capped-cart test now resets the
  independent income timer before comparing purchase counts; added directory
  entries had exposed its previous timing assumption.

The latest save/load and interface changes are implemented:

- PC F1 maps to UKNC К1 (load), F2 to К2 (save). Both shortcuts sit between
  ВЫБОР and ПОМОЩЬ. A framed selector shows five empty/occupied slots; Up/Down
  selects, Enter performs the operation, Tab/AP2 or Escape cancels.
- `src/saves.mac` uses normal RT-11 channel 1 files `DK:DRSAV1.DAT` through
  `DRSAV5.DAT`, each 52 blocks. Saves contain the full state region, PRNG, active
  scene and expedition rollback planes. The modal freezes game time and resumes
  the stored sub-tick phase. Loads stage and validate everything before commit.
  File length, format/build identity and two running checksums reject unsuitable
  data without modifying persistent state. Save replacement uses ENTER/CLOSE;
  failed allocation/writes preserve the old permanent slot.
- `make build` carries manual slot files into the replacement disk atomically
  (with the default debug-slot reservation described above).
  `make clean` keeps a disk containing slots. Saves require the matching build;
  the compatibility identity includes native sources and generated resources.
- ЛЕСНИК is now a read-only count above the specialist menu, never selectable.
  Left/Right transfers settlers between this remainder and selected jobs.
- Help clears the stocks sidebar and pauses gameplay and notification timers.
  Leaving it resumes without catching up the paused interval.
- Exhaustive reads exposed transient RT-11/FDD errors. DISK_READ now retries
  a whole record up to three times before its existing clean error exit.
  Experimental test-helper changes were removed; callcpu retains its original
  behavior. All scene records remain checked byte-for-byte through native I/O.

The preceding interface changes remain in place:

- Unavailable recipes remain visible in gray, including reached caps (a built
  cart), missing materials and a cold builder. Labels and numeric quantities
  keep their original font pixels. White returns as soon as the recipe is usable.
- The selected interactive row has a six-pixel connected snake moving one pixel
  per 10 Hz tick around a 6×6 square inside the cell before its label. All 20
  positions, corners and wraparound preserve six pixels and untouched glyphs.
- Available numbered locations have static 1-pixel frames: current white,
  others gray. Compact header rows 1 and 2 use blank font scanlines for borders.
  Plain `0 ПОМОЩЬ` is at column 72 of row 0, right of the selection count.
  Room fire/temperature descriptions occupy rows 3/4, with row 5 empty before
  selectable actions on row 6.
  Frames do not disappear during ordinary redraws. Hidden shortcuts are silent,
  leave selection/location unchanged, and cannot open an empty locked panel.
- Editable worker counts show `< N >`; Left/Right decrease/increase them.
  Enter is inert there. Gatherers remain the automatic unassigned count.
- The main heading follows the current panel. Room titles follow fire state;
  outside/worker titles follow upstream hut thresholds 0/1/4/8/14/more. The
  outside shortcut becomes ДЕРЕВНЯ once huts exist. Fire and temperature now
  have descriptions, including ОГОНЬ ПОЛЫХАЕТ, in room status and immediate
  change notifications. The first-light message is no longer repeated on stokes.

Latest `make verify`: **1,931 checks passed**, including five-slot
save/reboot/overwrite, byte-exact state and rollback restoration, corruption and
full-disk rejection, Help pause, nonselectable gatherers, all 276 scene reads,
all gameplay systems and RT-11 exits/DIR/relaunches. The release disk was unchanged.
Report: `tmp/verification.json`; log: `tmp/travel-full-verify.log`.
Release SHA-256: `03f5ef313f4bb4290a5d833b1f21d541ade215da5ac93d0dedde49466db69b41`.
A bounded SDL dummy-driver launch passed, and `uknc-play --keymap` confirms
F1 010 / F2 011. This is initialization/mapping validation, not interactive play.

Current SAV: 43,008 bytes / 84 blocks. `RESIDENT_END=123744`,
`SCENE_BASE=124000` (octal): **28 bytes of resident margin remain**.
`tools/branches.py` now iteratively shortens provably in-range branches from
assembler listings (828 short branches in this build), reclaiming room for
native saves without moving the scene window or stacks. `syms.py` skips macro
conditional-expression values when resolving bare labels before RT-11 macros.

Save-window evidence: `tmp/save-slots-empty.png`, `tmp/save-slots-full.png`.
Help/worker evidence: `tmp/help-pause-open.png`, `tmp/worker-controls-one.png`.
Latest layout/animation evidence: `tmp/square-cursor.png`,
`tmp/square-cursor.gif` (a full 20-frame cycle), `tmp/square-cursor-phases.png`
and `tmp/compact-header.png` (all locations unlocked).
Other visual evidence is in `tmp/disabled-recipes-built.bmp`,
`tmp/worker-controls-one.bmp`, `tmp/location-fire-roaring.bmp`,
`tmp/location-fire-village.bmp` and `tmp/decorations-page.bmp`, plus selected PNG
copies. These are temporary artifacts regenerated by the verification scenarios.
Older orbit/underline GIFs describe the previous UI and are no longer current.
No commits or pushes were made (this workspace has no Git metadata).

Read AGENTS.md and the project skill before further work. `make build` produces
`build/DARKRM.SAV`, `build/DARKRM.DAT` and `build/darkroom.dsk`. `make run` launches
the actual SDL UKNC player, booting the supplied RT-11 system and STARTS.COM's
`R DARKRM`. STOP/Escape or Help → Enter returns to a usable monitor prompt;
DIR and subsequent launches remain verified. Game text is uppercase Russian in
the original firmware 8×11 KOI-7 glyphs, 80×24 cells with 12-scanline pitch.

`decorations.mac` implements the spinner, frame records, gray recipe attributes
and existing 56-pixel cooldown bars. Palette index 4 is white and 6 is gray.
Disabled glyphs retain plane 1 and duplicate the same pixels in plane 2, using
bit 7 of SCREEN_BUF/SCREEN_OLD as the diff-cache attribute. Snapshot decoding
masks this bit. Stale bars must clear before FLUSH so they cannot erase gray
quantity pixels. TAB_UPDATE compares composed/previous records before erasing
frames; unchanged redraws never erase them. Frames use padding cells, the tab glyphs' unused first scanline and the blank
inter-row scanline. Verification checks that every current tab glyph leaves
that first scanline empty; plane-1 font pixels remain intact.

Cooldowns still use 56 individual pixels and live timers at 10 Hz, with captured
attack duration in WEAPON_SPAN. Counts and ship upgrades remain numeric. Tests
cover widths 56/55/28/27/2/1/0, 120-second timers, key-triggered waits, buff expiry,
and clearing stale overlays when switching to gray quantity lists.

`notifications.mac` provides five newest-first event rows at screen rows 18–22,
with the current message expiring after 30 seconds and displaced messages
fading within at most 15 more seconds. Every producer calls NOTIFY immediately after
setting NOTICE, so simultaneous events survive. Messages are copied, not kept as
scene pointers. Menus/costs and the 41×11 map fit above the log. Help, flight and
endings hide it; Help pauses timers, while flight and endings continue them. Regression checks inspect real log pixels,
ordering, overflow, repeated messages, timed expiry and panel changes.
Older messages now dim immediately to medium gray and fade through dark gray.
Only the first row is current, even when several messages have identical text.
Further arrivals never restart old timers; regular redraws never temporarily
publish white shades for old rows. Repeated physical stove keypresses cover this.
The newest stays white for 25 seconds before its final fade to expiry. LOG_SHADE is consumed
by the PPU timer; per-row display tags change brightness without touching glyphs
or the character diff cache. Help/flight/endings and the footer remain white.
Tests compare actual RGB values and glyph masks, including first-line accents.
The larger SAV also exercises normal RT-11 swapping. Scenario disks are disposable
copies. Ordinary tests permit writes only inside SWAP.SYS; save scenarios also
allow the five slot files and verify all boot/system/game files remain intact.
The release image is never used as a test write target; see platform.md.

The user's reference methodology is `../mc0511-elite`: readable assembly,
local build tools, real emulator verification, reusable agent guidance, and a
playable runner. No sibling directory is needed to build this port.

## What to read

1. `AGENTS.md` — invariants, source layout and common PDP-11 mistakes.
2. [architecture.md](architecture.md) — gameplay modules and scene format.
3. [platform.md](platform.md) — memory, video, PPU, disk and input.
4. [fidelity.md](fidelity.md) — scope and deliberate adaptations.
5. [tools.md](tools.md) — reproducible commands and troubleshooting.

The project skill is `.agents/skills/uknc-darkroom/SKILL.md`. Its paths are relative
to the repository root. Code and documentation are English; all target-screen
text is Russian in the KOI-7 font.

## Verification and limits

Run `make verify` after gameplay changes. It records `tmp/verification.json`,
per-scenario scripts/logs, RAM snapshots, and selected framebuffer captures.
Opening progression uses physical keypresses. Most later tests deliberately
seed state and call native routines through an emulator-only `callcpu` command.
Every scene is also read through RT-11 `.READW` and the real emulated FDD.
The suite also checks monitor/PPU state restoration, directory commands, three
launches, PPU memory reuse, physically moved data and startup-error paths.

These checks establish more than a boot screenshot, but do not establish a
complete unassisted campaign, every probabilistic outcome, browser-identical
balance, or physical-machine compatibility. Long-session playtesting and a real
UKNC are useful next validation targets. Manual saves supersede the earlier
no-persistence scope at the user’s explicit request.

## Build pitfalls already resolved

- MACRO-11 silently truncated very long generated directives. Tables now use
  at most eight words or 24 bytes per line. Keep this invariant.
- Forward string aliases were not safely resolved by this assembler. UI names
  are labels at the actual string definition, not forward equates.
- Numeric local labels cannot jump across a new global label.
- The standalone build's 0100 vector patch and stack at 157000 are gone.
  RT-11 owns those locations. Current CPU vectors must remain untouched.
- Startup explicitly invalidates SCREEN_OLD after clearing the framebuffer.
  A relaunch through RUN otherwise retained stale diff-cache contents and hid
  most text. Regression tests compare actual first/relaunch framebuffers.
- PPU palette index 2 needs 07400 for bright white, not a visually similar gray.
- Paths in inherited assembler patches were machine-specific. They now name
  source basenames and apply noninteractively to the pinned checkout.
- Test snapshot names are sanitized because the emulator script format splits
  arguments on whitespace.
- REPEAT_KEY must defer a fresh key sequence to MAIN before repeating it;
  otherwise a tick arriving before key dispatch can turn one arrow press into two.
- `callcpu DRAW` is unsafe if the paused CPU was already inside DRAW: its global
  menu scratch state is not reentrant. UI tests should switch panels with actual
  keypresses and let MAIN draw. Isolated BARS_DRAW calls with seeded live timers
  are used for exact pixel-width checks.
- A screenshot can catch an animation pass between erasing old dots and drawing
  the last new dot. FOCUS_COUNT can then be zero temporarily; check the visible
  single-cell geometry as well as completed frames, not just that scratch count.
  Capture previews after the initial screen composition has finished.

Generated files and temporary evidence can be rebuilt, but `build/darkroom.dsk`
may now contain player saves. Use `make clean`, which preserves such a disk.
Do not edit the extracted data to hide an upstream behavior mismatch; update the
native implementation and the documented callback audit deliberately.


## RT-11 source and build details

`orig/RT11BASE.DSK` is case-sensitive on Linux; the supplied filename is uppercase.
Do not alter it. The generated image is a filesystem-preserving copy with the
SAV, DAT and modified STARTS.COM. `orig/loader/source/SYSMAC.SML` is used directly
by the assembler. `rt11fs.py` and `savlink.py` came from `../tang-uknc/tools/`.
That project's FPGA-side SAV wrapping was reference material only; this game
uses native RT-11 file services and returns through `.EXIT`.

The old `src/boot.mac` and raw-sector scene loader have been removed. Scene
pointers now use 124000, not 140000, and the normal stack is 130000. `callcpu`
uses 126000/126776 so focused tests cannot corrupt the monitor. See platform.md.

The DAT header includes its build fingerprint and is checked before takeover.
Distribute the matching SAV and DAT together on DK:. A filename alone is not
an asset package. There is no hardcoded physical-sector dependency.
