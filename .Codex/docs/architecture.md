# Architecture

## Build and content

`src/darkroom.list` defines memory order. `tools/build.py` generates resource
tables and the font, concatenates assembly, iteratively shrinks provably local branches using assembler listings, invokes
MACRO-11 with the supplied `SYSMAC.SML`, links a classic `DARKRM.SAV`, and
creates `DARKRM.DAT` plus an 819,200-byte RT-11 floppy. `savlink.py` supplies
the transfer/stack/high-limit header and memory-usage bitmap. `rt11fs.py` copies
the supplied base volume, inserts the files, and appends `R DARKRM` to STARTS.COM.
The original boot/system files retain their locations. There are no fixed game
LBAs and no custom boot sector.

`tools/extract.mjs` evaluates upstream data declarations in a Node VM with
stubbed browser globals. It never starts the browser game. Functions become
readable `{js: ...}` objects in `src/res/upstream.json`. Normal builds use that
checked-in extraction; Node is needed only for explicit regeneration.

`tools/generate.py` compiles recipes, worker income, weapons, weights, landmarks,
and every event scene. `src/res/hook-audit.json` records 123 callback locations
and their reviewed implementations. Changed/added/removed callbacks fail the
build until reviewed. This ledger guards upgrades; it is not a proof that a JS
function was automatically translated correctly.

Russian translation lookup combines upstream `lang/ru/strings.js`, manual
additions in `ru-extra.txt`, and native `ui.json`. Missing translations fail the
build. Text is uppercase KOI-7, Ё becomes Е. Disk scene prose wraps at 76 columns
and must fit four rows. The bank has 273 upstream scenes and three native defeat
explanations. The logical display is 80×24.

## Runtime modules

| Module | Responsibilities |
| --- | --- |
| `rt11.mac` | SAV entry, memory request, DAT validation/file reads, cleanup and RT-11 exit |
| `main.mac` | State arrays, main loop, 10 Hz scheduler and cooldowns |
| `platform.mac` | Relocated PPU code, white palette, keyboard, clock, state restoration, PRNG |
| `screen.mac` | Text buffer, glyph rendering, changed-cell framebuffer updates |
| `decorations.mac` | Single-cell spinner, tab frames, recipe shading and pixel cooldown bars |
| `saves.mac` | Paused five-slot UI, RT-11 file transactions, validated state capture/restore |
| `compass.mac` | Live eight-way travel bearing without revealing fog |
| `pages.mac` | Startup splash, cleared endings, new game and OS exit |
| `travel-dialogs.mac` | Paused encounter/defeat explanations and explicit Enter acknowledgement |
| `notifications.mac` | Five copied message rows, current/old distinction, independent fade and expiry |
| `village.mac` | Fire, builder, recipes, discovery, jobs, production, population, random events |
| `world.mac` | Map, fog, supplies, bag capacities, exploration, death/return, flight |
| `events.mac` | Scene interpreter, choices, effects, loot, weapons, enemy attacks, status effects |
| `ui.mac` | Progressive tabs, paged menus, scene and map presentation, keyboard actions |

The main loop consumes the PPU clock in five-interrupt increments (one tenth of
a second). Village updates run each second; income every ten seconds. Keyboard
presses have a sequence number; held arrows repeat after a delay. Actions need
a new press. Drawing and game timing are separate. Only changed character cells
are written to video RAM.

At each 10 Hz tick the selected row's six-pixel snake moves one pixel around
the perimeter of a 6×6 square inside the character cell before its text. All
20 positions keep the six pixels connected, including corners and wraparound.
Their byte addresses are saved in FOCUS_OLD and explicitly erased. MAIN updates this independently of
text composition; read-only lists, the map, flight and endings have no spinner.
PUT_TAB records usable numbered labels; Help stays plain. TAB_UPDATE compares
new and old records before erasing changed frames. TAB_PIXELS paints static
one-pixel frames white for the current tab and gray for other usable tabs. Rows
1 and 2 contain the location tabs. Their top frame edges use the unused first
scanline of these labels; their bottoms use the inter-row blank scanline. Tests
check that all tab glyphs leave the top scanline empty. Help sits at column 72
of row 0, to the right of the selection count. Room fire/temperature status uses
rows 3/4, leaving row 5 blank before actions start on row 6. Event/store headings
remain on row 4. Hidden shortcuts test the same prerequisites as tab visibility
and return silently without changing location or selection.

SHADE_RECIPE checks temperature, recipe caps and the current scaled cost. It
marks unavailable labels/counts with bit 7 in the text diff cache. FLUSH masks
that attribute before font lookup and duplicates intact glyphs into plane 2,
selecting gray palette index 6. Removing the attribute restores white. These
entries stay selectable so costs and ordinary action feedback remain available.

Worker and packing rows show `< N >` for editable quantities. Left/Right
remove/add one worker or return/take one item between home stores and the bag.
Holding an arrow repeats the adjustment; stock, zero and capacity limits still
apply. Enter does nothing on these quantity rows, and Space no longer unpacks
items. Enter still activates the departure row, and 7 departs from any packing
row. Gatherers remain the automatic unassigned count. Up/Down browse all lists,
automatically changing pages as needed; horizontal ten-row jumps are removed.
Other list actions retain their existing Enter/Space controls, while map/flight
arrows retain movement. The footer and Help describe the new packing controls.
Vitals show plain ВЕС: carried/capacity, without the former (0,1) annotation;
the numeric weight values are unchanged.

LOCATION_TITLE uses fire state for the room and the pinned hut thresholds
0/1/4/8/14/more for outside and worker panels. Other home panels use their own
names. The outside shortcut becomes ДЕРЕВНЯ when huts exist. Room status shows
five fire/temperature descriptions instead of numbers; stoking, cooling and
temperature changes publish their actual description immediately. The initial
light-spilling message occurs only on the first fire, as the builder arrives.

REGISTER_BAR binds visible cooldown rows to live timer addresses and their
durations. BARS_DRAW runs at 10 Hz and fills 56×3 pixels at columns 48–54,
scanlines 4–6 within each row. Width is ceil(56 * remaining / duration), clamped
to 56; zero paints black. The multiply/divide uses the full register pair, since
120-second cooldowns exceed a 16-bit numerator. BAR_USED clears old bar rows on
view/page changes without touching text. The animation pass erases old focus pixels, updates bars, then draws the new
focus. Bars also clear stale rows before text FLUSH to preserve gray quantities.

Fire/gather/traps use 100/600/900 ticks; departure/launch use 1200. ATTACK records
its actual perk/stimulant-adjusted duration in WEAPON_SPAN, outside COOLDOWNS,
so ending a buff does not rescale an already-running bar. Resource quantities,
building counts, healing supplies and ship upgrade levels remain numeric.

Combat adds a read-only АТАКА ПРОТИВНИКА row at row 7, above the player's
weapon menu. Its bar reads ENEMY_CLOCK at 10 Hz, using ENEMY_SPAN captured at
scene entry and each normal/frenzied attack restart. BARS_DRAW reads that span
live so a restart between text redraws immediately uses the right scale;
expiring frenzy leaves the current wait's scale intact. Stun replaces the row
label with ПРОТИВНИК ОГЛУШЕН and pauses the same clock; meditation's existing
status also explains its paused wait. Both successful and missed enemy attacks
publish immediate log feedback. The bar is absent after death, during an
explosion wait, and in the save/load modal. ENEMY_SPAN is persisted with combat
state. Current combat scene prose fits row 6, above this new row.

The lit-room heading is ОЧАГ; the extinguished-room heading remains
ТЕМНАЯ КОМНАТА.

The repeat-key handler waits until MAIN has dispatched a fresh key sequence;
otherwise a tick arriving before dispatch could turn one arrow press into two.

Notification producers set `NOTICE` to their string and immediately call
`NOTIFY`, which preserves registers and copies up to 78 characters into resident
`LOG_TEXT`. Do not defer capture until DRAW: several events can occur in one
tick. The five 80-byte slots and five remaining-age words live inside the
startup-cleared state. `LOG_TICK` runs at 10 Hz even on screens hiding the log,
and marks the display dirty when a message expires. The log uses rows 18–22;
row 23 remains the keyboard hint. Help, flight and endings hide it.

NOTIFY caps the displaced top row's remaining lifetime at 150 ticks (15 seconds),
leaving all other timers untouched. Current/old is determined by position,
including repeated identical text. DRAW_LOG publishes `LOG_SHADE` as well as text.
Every old row is immediately medium gray (128), then dark gray (96) for its final
7.5 seconds. The newest stays white for 25 seconds, medium gray for 2.5 seconds,
then dark gray until expiry. Normal once-per-second redraws advance shades even
with no input; a new message dirties the display immediately. The PPU applies
the shades through per-row palette/brightness tags, independent of the character
diff cache. See platform.md for the scanline layout and restoration contract.
Only hidden-log views reset all shades to white. Doing that at the start of
ordinary redraws lets the asynchronous PPU briefly brighten old messages again.

Normal menus use rows 6–13, crafting costs 14–17, and the store summary 6–16.
The centered map is 41×11 cells at rows 6–16. Scene prose uses rows 5–8,
choices 10–14 and costs 15–17; combat menus use rows 8–16. Pagination keeps
all actions accessible. Full-screen help, flight geometry and endings retain
their original layouts. Keep new content above the log and enforce prose limits
in the generator rather than silently truncating a scene.

## Scene format

Each bank record starts on a 512-byte boundary. `SCENE_DIR` contains file-relative block and
sector count pairs; `build/catalog.json` connects IDs to upstream group/event/
scene names. Pointers are native CPU addresses based at decimal 43008 (0124000).
Loading another scene invalidates every old pointer into that window.
Block 0 of DARKRM.DAT holds a 48-byte pairing header (magic, format version,
load address, scene count, scene block count and SHA-256 of the scene bank).
Its exact expected bytes are compiled into the SAV. Startup checks size/header
through RT-11 before changing the display. The fingerprint prevents mixing
builds; it is not a runtime checksum of every scene read. Records begin at
file block 1, so the current file is 282 blocks for 279 records (the splash and beacon ending occupy two blocks).

The header has sixteen 16-bit words:

| Byte offset | Meaning |
| --- | --- |
| 0, 2 | Title and body string pointers |
| 4, 6 | Enemy health, damage |
| 8, 10 | Attack delay in tenths, hit percentage |
| 12, 14, 16 | Loot, entry effects, choices |
| 18, 20 | Special attack kind, home/away group marker |
| 22, 24 | Special delay in tenths, explosion damage |
| 26 | Compact dialog body pointer (combat and native defeat records) |
| 28–30 | Reserved |

Lists start with a count. Loot entries are resource offset/min/max/chance.
Costs are resource offset/quantity pairs. An effect is opcode/argument/argument.
A choice contains text pointer, costs, effects, cumulative-probability branches,
availability kind and argument. A branch target of 65535 closes the event.
The generator rejects an oversized scene or overflowing disk.

Effects implement dungeon clearing, visited markers, water, roads, flags, perks,
healing, map charts, resource rewards, beggars, huts, delayed gambles, broken
traps, fire, casualties and thieves. Combat callbacks are explicit native status
logic. There is no JS interpreter in the game.

## Inventory and expeditions

`STORES` holds home inventory, `BAG` carried items, `LOOT` current scene loot.
Costs are validated completely before payment. Worker half units accumulate
without floating point. Individual workers consume all required inputs before
producing their output. Positive stock changes saturate at 30,000.

At departure, map, fog, completion bytes and progression flags are snapshotted.
The large arrays use unused video-plane space above the visible framebuffer.
Returning transfers the bag to stores and commits discoveries. Death restores
the snapshot and discards the bag. Outposts refill once per expedition. There
are five manual RT-11 save slots that also retain this rollback snapshot. The
RT-11 monitor remains resident and its CPU vectors are never replaced.

Every combat scene opens TR_MODE=1 before simulation resumes. The framed black
view repeats its scene title/prose, adds ПРИГОТОВЬТЕСЬ К БОЮ! and a framed БОЙ
button. A fresh Enter clears the dialog without making a player attack. TICK
continues only focus animation while a travel dialog is open, including frozen
game/log/cooldown clocks. It also checks TR_MODE after village updates and held
movement, so a same-tick encounter cannot take an enemy attack before the prompt.
Opening consumes key events queued during disk I/O; holding Enter cannot carry
through a later defeat. F1/F2 and STOP keep their global meanings; other keys
cannot bypass acknowledgement. Resume rebases the clock to avoid catch-up.

Defeat still rolls back discoveries, loses the bag, returns home and sets the
120-second cooldown exactly once. It then reads a native defeat/hunger/thirst
explanation through channel 0 and opens TR_MODE=2 with ЖАЛЬ. The three prose
records are compiled from ui.json, appended after the stable upstream IDs, and
kept on disk to preserve resident memory. Modal prose wraps at 44 columns, with continuation lines indented to column 18.
Combat records retain the original wide body at offset 2 for the active fight
and carry the same prose rewrapped for the dialog at offset 26. TR_MODE and the current scene window are
saved normally, so loading either prompt continues waiting for acknowledgement.
Both transitions clear all visible planes/cache, including old focus and bars.
Only the dialog and exact-case version footer remain on black. FRAME_RECT is
shared with the save picker. Both frames occupy x=128–511, y=71–216: 60% of
the screen width and centered on both axes. The travel button borders sit outside all 11 glyph
scanlines to preserve Й's accent. These scenes are never entered by game choices.


## Opening and endings

After PPU takeover, SPLASH reads the native credits page from DAT and draws
centered, unframed text on black. Enter clears it and enters START; STOP returns
to RT-11. No game timers or world initialization run before acknowledgement.
The original web author and contributor credits link to the official game and
source, following the [Doublespeak credits](https://press.doublespeakgames.com/adr/index.html).

Successful flight calls END_OPEN, which clears both planes and reads either the
standard or fleet-beacon ending. DRAW_PAGE replaces the entire layout, with no
top heading, tabs, log or leftover flight pixels. TAB=12 pauses simulation.
The bottom row contains 1: НОВАЯ ИГРА and 2: ВЫХОД В ОС, plus V1.0.0 at right.
New Game resets the stack and runs START; Exit uses the normal RT_EXIT cleanup.
F1/F2 still work, and saving/loading preserves the ending's disk page directly.
All three pages are native scene records with body at header offset 2; they are
exempt from the ordinary four-row prose limit. Long ending/credit text is disk
resident. Latin capitals use the original ROM glyphs in the separate font bank.

## Manual save files

F1/К1 and F2/К2 are global input actions, including during scenes, combat, flight
and endings. They open a framed five-slot window without changing TAB/SELECTED.
TICK still animates the cursor but skips all game/log simulation while SV_MODE
is nonzero. Slot selection is separate from game selection. AP2/Escape cancels;
Enter saves/loads and closes on success. A missing file is ПУСТО, an existing
file ЕСТЬ СОХРАНЕНИЕ; other lookup failures show a distinct read-error state.
The top row reserves columns 30–41 for the selection counter and 44–79 for
К1 ЗАГРУЗИТЬ, К2 СОХРАНИТЬ and 0 ПОМОЩЬ.

Each DRSAVn.DAT has a 512-byte header followed by a padded word stream containing
STATE_START..STATE_END, SEED, all 1024 scene bytes, and 5582 words from video
155000 (both rollback planes). The current format occupies 52 disk blocks.
SV_REGIONS defines that stream for capture and restore. The header includes
magic/version, size, a SHA-256 build identity, sub-tick phase and two 16-bit
running checksums over the phase and padded payload. The identity is generated
from all assembly/resource modules plus scene data; incompatible builds reject
old files rather than reinterpret their pointers or layout.

Channel 1 and SV_AREA are independent of the scene channel/request area. SAVE
uses ENTER, WRITW and CLOSE; CLOSE makes the completed file permanent and replaces
an existing unprotected slot. PURGE aborts a failed tentative write. See DEC's
[Programmer's Reference, ENTER](https://www.bitsavers.org/pdf/dec/pdp11/rt11/v5.0_Mar83/AA-H378B-TC_5.0_PgmRefMan.pdf).
LOAD checks the header and complete checksum before committing any game state.
The candidate is staged in unused-at-that-moment visible video starting 117000,
skipping centered display rows 9–14 and wrapping to row 0 before the footer.
The PPU hides rows 0–8 and 15–22 and acknowledges before staging starts,
leaving the centered progress window and footer visible. All staging stays below
the rollback area at 155000. Failed loads
therefore leave all persistent state intact; successful commit performs only
memory copies. In both cases staged pixels/cache are cleared before unmasking.
Log brightness is recomputed; transient overlays/menu/notice pointers are reset,
and clock/key baselines are rebased to current hardware time. Scene data is
restored directly, so entry effects and loot are not rerolled.

The build carries manual slots into its new disk before replacing the image
atomically. Default builds refresh slots 2 and 3 with native-compiled JSON debug
presets; replaced manual files receive content-addressed backups under tmp.
With --no-debug, generated presets are removed and all manual slots are retained.
The clean command retains a disk containing player saves. Debug state authoring,
header markers, cache behavior and constraints are in [GAMESTATE.md](../../GAMESTATE.md).
Native verification checks all slot files, reboot/overwrite, byte-exact restored
state, rollback planes, damaged/incompatible/truncated files, full-disk failures,
modal pause/cancel, ordinary scene reads after load, and preservation on rebuild.
