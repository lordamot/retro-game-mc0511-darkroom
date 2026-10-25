# Fidelity and adaptations

Reference: doublespeakgames/adarkroom revision
`1fada4620b6c66bd07bf15a3f1eb8223df8bc1d7`, including the Executioner/fabricator
content present in that revision. This is a native rewrite, not source-compatible
JavaScript. The following distinctions are intentional and should stay visible
to maintainers.

## Content and systems retained

| Area | Native treatment |
| --- | --- |
| Room | Fire, temperature, stranger/builder stages, cooldown and autonomous wood income |
| Village | Forest gathering, cart, traps/bait/drop table, huts, population, jobs, theft and random events |
| Economy | All 46 original recipe records and costs, building cost increments and maximums, ten worker roles with fractional income |
| World | 61×61 map, twelve placed landmark types/counts/radius ranges, roads, fog, diamond sight radius, scout and charts |
| Expedition | Original upgrade capacities, equipment, weighted bag, food/water, healing, death cooldown and loss of uncommitted discoveries |
| Encounters | All eleven encounter definitions; terrain/distance selection, hit chance, damage, cooldowns, ammunition and loot |
| Story scenes | All 273 scene records, Russian prose, choice costs, probability branches and loot |
| Perks | Combat, stealth, sight, food and water perks, including repeated-unarmed-use milestones |
| Late game | Mines, ship discovery, Executioner wings/command, blueprints, fabricator and advanced combat statuses |
| Ship | Alloy hull/engine upgrades, four-direction movement, increasing debris, 60-second ascent, crash cooldown, normal/beacon endings |

The callback ledger records 123 upstream function locations. Native mappings
cover entry/choice rewards, flags and perks, village disasters and delayed
gambles, availability rules, and special enemy effects. A changed function
requires explicit review; regenerating tables alone is not a gameplay port.

## Target-specific changes

- **Interface:** an 80×24 Russian uppercase text screen, paged keyboard menus,
  and a 41×11 map viewport replace DOM buttons, mouse actions and browser layout.
  Ё is rendered as Е. Short notifications and introductory status messages are
  condensed; scene prose is translated and wrapped. Five notification rows show
  the newest message first, with 30-second current-message expiry, a maximum
  15-second fade once superseded, and oldest-first eviction. Upstream uses a
  spatial gradient and clears messages pushed below
  it, rather than timed expiry. The native log dims older entries immediately,
  then fades in hardware grayscale steps (255, 128, 96, black), preserving
  glyphs. The newest stays white until its final five seconds. The log is hidden
  during help, flight, endings and travel acknowledgement dialogs. There is no archived
  notification scrollback or translated browser settings.
  A six-pixel snake follows a square within one cell before the selected row.
  Solid white/gray frames distinguish the current location from other available
  numbered tabs; Help stays plain, and hidden shortcuts are silent. Unavailable
  recipes are gray. Worker counts use `< N >` with Left/Right controls. Cooldowns
  become 56-pixel shrinking white bars; quantities stay numeric. Room/outside
  titles follow original fire/hut thresholds, and fire/temperature descriptions
  update with state changes.
- **Saves:** five explicit native RT-11 files replace browser persistence. F1/К1
  loads and F2/К2 saves; the slot window pauses gameplay. Saves capture the full
  native continuation state, including the current scene and expedition rollback,
  and are tied to the matching build. There is no automatic save or load.
- **Quantities:** signed 16-bit stock values saturate at 30,000. Bag weights use
  tenths. Time and combat cooldowns use tenth-second ticks. The original uses
  JavaScript numbers and independent browser timers.
- **Map:** landmark counts and Manhattan radius constraints are retained, but
  terrain is sampled from the base distribution rather than upstream's sticky
  outward spiral. Landmark positions are uniformly sampled within allowed
  Manhattan bands, instead of upstream's radius-first/clamped procedure. Roads
  use horizontal-then-vertical paths. Random sequences are native xorshift. The travel compass shows an eight-way
  bearing beside the viewport without revealing fog. It uses the original 2:1
  axis threshold but follows the current traveler, rather than the browser
  tooltip's fixed bearing from home.
- **Events:** home panels share the room event pool except the forest panel.
  Eligible events are checked after a random candidate is selected, so some
  intervals produce no event. This changes event frequency relative to filtering
  the whole browser event pool first. Only one wanderer return timer is stored.
- **Combat:** ASCII menus replace attack animations. Enemy statuses are visible
  as Russian labels. Single-key auto-attack picks the first ready carried weapon;
  weapons remain individually selectable. Each enemy encounter first pauses on
  its actual scene description until Enter activates БОЙ. Combat then runs in
  real time. Defeat pauses on a black framed explanation with ЖАЛЬ, including
  distinct hunger/thirst causes and the loss of supplies and rescue home.
- **Flight:** 40×19 text-cell geometry, up to 64 moving debris records and integer
  cell speeds replace pixel collision boxes and animation interpolation. Engines
  improve movement, not ascent duration. This preserves the objective and upgrade
  roles, not the browser's exact difficulty curve.
- **Presentation:** browser music, sound library, smooth browser fades, stars, particle effects,
  theme switches, browser accessibility options and visual animation are absent.
  The native game is silent. The UI stays white on black, with gray disabled recipes and inactive tab
  frames; the event log uses grayscale fading without theme switches.

## Deliberate exclusions

No browser import/export, local-storage state, prestige/new-run cache, previous-run
score history, online scoring, achievements service, analytics, marketing events,
donation controls, language picker, or other browser integrations. The prestige
cache scenes remain in the bank for source completeness but no cache landmark
is placed and `Prestige.collectStores` has no native persistence equivalent.
There is no numeric scoring screen; the endings finish the current session.

## Evidence and open validation

`make verify` runs the assembled game on the actual UKNCBTL CPU/PPU/FDD core.
It exercises a natural opening through keypresses and uses controlled RAM states
for later progression and edge cases. It reads all scene records through RT-11 `.READW` and the
floppy firmware, checks the white/black framebuffer, and verifies each scenario
ordinary scenario disks change only within RT-11's SWAP.SYS scratch file. Save
scenarios additionally allow the five slot files and their directory metadata,
while preserving all system/game files. The release disk hash
does not change. STOP and Help exits restore RT-11; tests run DIR and relaunch
the SAV repeatedly, check PPU release, and exercise data-file failures. See `tmp/verification.json` for the current result.

The tests do not constitute an exhaustive campaign or every branch taken through
normal player input. Extended balancing, every rare random-event combination,
and real UKNC hardware require further playtesting. Do not describe the port as
an exact reproduction or claim hardware validation from emulator results.


Help clears the stock sidebar and pauses gameplay and notification clocks.
The ЖИТЕЛИ panel displays ЛЕСНИК as a read-only remainder outside the menu;
only specialist jobs accept Left/Right assignment.
