# Debug save source format

Edit [`src/res/debug-saves.json`](src/res/debug-saves.json), then run `make build`.
The build compiles two normal RT-11 saves using the current game binary:

| Slot | File inside the disk | Starting position |
| --- | --- | --- |
| 2 | `DK:DRSAV2.DAT` | Expedition preparation, with departure selected |
| 3 | `DK:DRSAV3.DAT` | Spaceship panel, with liftoff selected |

Load with **F1 / К1**, choose the slot with Up/Down, then press Enter. Press Enter
again on the restored panel to depart or launch. The presets start at home;
they are not snapshots of an expedition or flight already in progress.

## Build commands and existing saves

```sh
make build                         # Compile and include both debug presets
make run                           # Build with presets, then launch the emulator
make build -- --no-debug            # Omit generated debug saves
make run -- --no-debug              # Build without presets, then launch
make build ARGS=--no-debug          # Equivalent Make variable syntax
python3 tools/build.py --no-debug   # Direct internal builder option
```

GNU Make interprets flags itself: the first `--` ends its option parsing. Bare
`make build --no-debug` is not valid GNU Make syntax. The Makefile forwards the
second `--no-debug` to the builder for both `build` and `run`.

Default builds reserve and refresh slots **2 and 3**. Slots 1, 4 and 5 retain
their manual saves. If a manual save occupies slot 2 or 3, its bytes are backed
up as `tmp/player-save-backups/DRSAVn-<SHA256>.DAT` before the debug preset replaces
it. The backup can be imported into a disk with `tools/rt11fs.py`.

With `--no-debug`, generated presets are omitted even if the previous disk
contained them. Manual saves in **all five slots** are retained. Generated
presets have a marker in reserved header bytes; saving manually in the game
clears that marker, so a manual replacement is distinguishable from a preset.
This option does not disable the in-game save/load feature.

Generated files are in `build/debug/`; edit the source JSON rather than these
files. `make clean` preserves disks containing saves. Saves require the matching
native build, as described in [architecture.md](.Codex/docs/architecture.md).
Changing only this JSON regenerates the presets without changing the native
save compatibility identity or invalidating other saves.

## JSON structure and defaults

All numeric values are **decimal integers**, unlike octal assembly literals.
Use JSON numbers, not numeric strings or booleans. Inventory and state names
are case-sensitive internal identifiers; the game still displays Russian text.
JSON has no comments. Use each preset's `description` for author notes.

| Root parameter | Type / allowed value | Purpose and restrictions |
| --- | --- | --- |
| `version` | `1` | Source schema version. Other versions fail compilation. |
| `defaults` | Object | Shared scalar state values; accepts the fields in the state table below. |
| `slots` | Array of exactly two objects | Must contain slot 2 followed by slot 3. No extra slots or reversed order. |

These three root keys are required; unknown root keys fail compilation.
For scalar state, `defaults` is merged with each preset's `state`; the preset
wins when the same field appears in both. Inventory, buildings, jobs, flags and
perks are separate per-preset sections and do not inherit from `defaults`.

| Preset parameter | Type / range | Purpose and restrictions |
| --- | --- | --- |
| `slot` | Integer `2` or `3` | RT-11 save slot number; determines the opening panel. |
| `description` | String | Author-facing explanation. Not displayed or stored as game prose. |
| `seed` | Integer `1..65535` | Initial seed for the native world generator. Zero is forbidden. The save stores the PRNG state **after** map generation. |
| `state` | Object | Per-slot scalar overrides; only fields listed below are accepted. |
| `stores` | Object of resource name → count | Inventory at home, including passive equipment and spare expedition supplies. |
| `bag` | Object of resource name → count | Already-packed expedition items. Does not subtract from `stores`; both quantities are independent. |
| `buildings` | Object of building name → count | Existing village buildings; native caps apply. |
| `jobs` | Object of specialist name → count | Worker assignments. Unassigned settlers become `gatherer` / ЛЕСНИК automatically. |
| `flags` | Array of known flag names | Each named progression flag is set to `1`; omitted flags are `0`. |
| `perks` | Array of known perk names | Each named perk is enabled with value `1`; omitted perks are `0`. |
| `reveal_map` | Boolean | `false`: normal starting visibility from native `REVEAL`; `true`: every map cell is visible. Does not clear encounters or mark sites completed. |

Every preset key above is required, including empty objects/arrays such as
`"bag": {}` and `"flags": []`. Unknown preset keys fail compilation.
Missing inventory/building/job entries mean zero. Unlisted flags and perks are
disabled. Runtime state starts cleared before the configured values are applied.

## Scalar state parameters

These are the complete supported keys for `defaults` and `state`. Other native
symbols, arrays, addresses and pointers cannot be supplied through `state`.

| Parameter | Accepted values | Purpose / restrictions |
| --- | --- | --- |
| `FIRE` | `0..4` | `0` out, `1` smoldering, `2` flickering, `3` burning, `4` roaring. The presets use `4`. |
| `TEMPERATURE` | `0..4` | Room temperature, coldest through hottest. The presets use `4`; crafting needs a warm room. |
| `BUILDER` | `0..4` | Builder arrival/recovery stage; `4` is fully recovered. These home presets support the arrived builder stages, not the native negative “not arrived” sentinel. |
| `FOREST` | `0` or `1` | Whether the forest/outside location is unlocked. |
| `POP_DELAY` | `1..32767` | Seconds until the initial population-arrival interval elapses. Its elapsed counter starts at zero; later intervals are chosen by the native game. |
| `EVENT_DELAY` | `1..32767` | Seconds until the initial random-event interval elapses. Its elapsed counter starts at zero. |
| `SCENE_ID` | Exactly `65535` | No active scene. These presets do not author scene pointers, enemies or an active encounter. |
| `THRUSTERS` | `1..30000` | Engine upgrade count. Movement is `min(5, floor(THRUSTERS / 4) + 1)` cells per accepted arrow action. The preset's `5` engines give `2` cells; the cap is reached at `16`. |
| `TAB` | Slot 2: `6`; slot 3: `7` | Zero-based panel identifier: expedition preparation or spaceship. Other starting panels fail compilation. |
| `SELECTED` | `0..63`; spaceship `0..2` | Zero-based selected action. Use `0` for expedition departure; ship actions are `0` hull repair, `1` engine upgrade, `2` liftoff. The native menu resets an out-of-range expedition selection to zero. |
| `POPULATION` | `0..80` | Total settlers. Cannot exceed four settlers per existing hut or be lower than the sum of specialist assignments. |
| `HP` | `1..85` | Current health. Must not exceed the maximum computed from home armor. Departure refills health to that maximum. |
| `WATER` | `1..110` | Current water. Must not exceed the maximum computed from home water equipment. Departure refills water to that maximum. |
| `HULL` | `0..30000` | Repaired ship hull points. Slot 3 requires at least `1`; the shipped preset uses `50`. Zero is appropriate before discovering/repairing the ship. |

The merged state must explicitly contain `TAB`, `SELECTED`, `HP`, `WATER`,
`POPULATION` and `SCENE_ID`. Other omitted scalar fields remain zero, so retain
the provided positive `POP_DELAY`, `EVENT_DELAY` and `THRUSTERS` defaults for
normal behavior. `HULL` is intentionally omitted for slot 2 and therefore zero.

The first-expedition preset additionally requires a positive `compass` count in
home stores. The spaceship preset requires the `ship` flag and positive hull.
Unlocking the ship without repairing its hull will not produce a launchable save.

## Resources, equipment and weight

Every `stores` and `bag` quantity must be an integer in **`0..30000`**. Unknown
resource names fail compilation. Names come from `build/catalog.json`, generated
from the checked-in upstream data. The current resource names and purposes are:

| Names | Purpose |
| --- | --- |
| `wood`, `fur`, `meat`, `scales`, `teeth`, `cloth`, `leather` | Village production, construction and crafting materials. |
| `cured meat` | Expedition food and healing; also consumed by miners. |
| `iron`, `coal`, `steel`, `sulphur` | Industrial crafting and production materials. |
| `bullets`, `energy cell` | Ammunition for weapons requiring them. |
| `medicine`, `hypo`, `stim` | Healing and combat consumables. |
| `bait`, `torch`, `charm` | Traps, exploration gates and applicable encounter/crafting costs. |
| `bone spear`, `iron sword`, `steel sword`, `rifle`, `laser rifle`, `plasma rifle`, `energy blade`, `disruptor`, `bolas`, `grenade`, `bayonet`, `glowstone` | Carried weapons and combat tools. Pack weapons and their required ammunition in `bag` to use them on an expedition. |
| `alien alloy` | Ship hull/engine upgrades and applicable advanced crafting. |
| `compass` | Unlocks expedition preparation; keep it in `stores`. |
| `waterskin`, `cask`, `water tank`, `fluid recycler` | Passive water capacity upgrades; keep in `stores`. |
| `rucksack`, `wagon`, `convoy`, `cargo drone` | Passive carrying capacity upgrades; keep in `stores`. |
| `l armour`, `i armour`, `s armour`, `kinetic armour` | Passive maximum-health upgrades; keep in `stores`. Kinetic armor also supports the native shield action. |
| `hypo blueprint`, `kinetic armour blueprint`, `plasma rifle blueprint`, `disruptor blueprint`, `glowstone blueprint`, `stim blueprint` | Advanced recipe prerequisites. Counts do not themselves unlock the fabricator or its wings. |
| `water`, `hp` | Resource identifiers used by native content. They are not substitutes for scalar `WATER` and `HP`; setting inventory counts does not refill those vitals. |
| `fleet beacon` | Special ending-related item. Not required for the normal spaceship preset. |

Passive equipment affects capacities only when present in **home stores**.
Multiple copies do not stack; one is enough. Higher upgrades take precedence:

| Derived value | Native progression |
| --- | --- |
| Maximum HP | Base `10`; `l armour` → `15`; `i armour` → `25`; `s armour` → `45`; `kinetic armour` → `85` |
| Maximum water | Base `10`; `waterskin` → `20`; `cask` → `30`; `water tank` → `60`; `fluid recycler` → `110` |
| Bag capacity | Base `100`; `rucksack` → `200`; `wagon` → `400`; `convoy` → `700`; `cargo drone` → `1100` |

Weight uses the native integer units: most items weigh **10** per item, a bone
spear **20**, iron sword **30**, steel sword/rifle/laser rifle/plasma rifle **50**,
bolas **5**, bullets **1**, and energy cells **2**. Values are compiled from
`upstream.json`'s weights, scaled by ten. The complete packed bag must fit the
capacity; compilation fails if it is overweight or its native sum overflows.
Home stores have no bag-weight limit.

Slot 2 packs 12 cured meat, 2 torches, 1 bone spear and 2 medicine: **180 / 200**
weight units. Extra food, torches and equipment remain at home. Items in `bag`
are already packed; do not also subtract them from the listed `stores` values.
The compiler marks positive `stores`/`bag` entries as discovered (`SEEN`). Recipe
visibility is then evaluated by the native game; it does not unlock every recipe.

## Buildings and jobs

All omitted buildings are absent. Counts are nonnegative integers with these
native caps, enforced by the compiler:

| Building name | Maximum | Purpose |
| --- | --- | --- |
| `trap` | `10` | Trap collection capacity. |
| `cart` | `1` | Improved wood gathering. |
| `hut` | `20` | Four settlers of housing per hut. |
| `lodge` | `1` | Hunter and trapper jobs. |
| `trading post` | `1` | Trading location. |
| `tannery` | `1` | Tanner job. |
| `smokehouse` | `1` | Charcutier job. |
| `workshop` | `1` | Crafting location and relevant recipes. |
| `steelworks` | `1` | Steelworker job. |
| `armoury` | `1` | Armourer job. |

Each specialist count is a nonnegative integer; the **sum must not exceed
`POPULATION`**. This also bounds every individual count to at most 80. The
compiler rejects `gatherer` in `jobs`: ЛЕСНИК is calculated as population minus
the sum of assigned specialists. Job names and their native prerequisites are:

| Job name | Prerequisite | Production role |
| --- | --- | --- |
| `hunter` | `lodge` | Fur and meat. |
| `trapper` | `lodge` | Converts meat to bait. |
| `tanner` | `tannery` | Converts fur to leather. |
| `charcutier` | `smokehouse` | Converts meat and wood to cured meat. |
| `iron miner` | `ironmine` flag | Consumes cured meat to mine iron. |
| `coal miner` | `coalmine` flag | Consumes cured meat to mine coal. |
| `sulphur miner` | `sulphurmine` flag | Consumes cured meat to mine sulphur. |
| `steelworker` | `steelworks` | Converts iron and coal to steel. |
| `armourer` | `armoury` | Converts steel and sulphur to bullets. |

The compiler validates names/counts and total population; it does **not** infer
or add a job's prerequisites. Supply the buildings/flags yourself. Ongoing input
consumption and production use the normal native rules after loading.

## Flags and perks

These arrays contain names only, not numeric values or objects. A name sets the
corresponding native word to `1`. Unknown names fail compilation; repeated names
have no additional effect.

| Flag | Purpose |
| --- | --- |
| `ship` | Enables the spaceship location. |
| `ironmine`, `coalmine`, `sulphurmine` | Unlock their mining jobs. |
| `executioner` | Unlocks the executioner/fabricator progression. |
| `engineering`, `medical`, `martial` | Records the corresponding executioner wing progress. |
| `cityCleared` | Records the city-cleared progression milestone. |
| `thieves` | Sets the native theft progression word to stage `1`; this is not a quantity of resources. |

| Perk | Native effect |
| --- | --- |
| `gastronome` | Doubles food healing. |
| `scout` | Increases the map reveal radius from 2 to 4, including initial visibility when `reveal_map` is false. |
| `evasive` | Reduces the enemy's hit chance by one fifth, with integer rounding. |
| `precise` | Increases player attack hit chance from 80% to 90%. |
| `barbarian` | Adds half the base damage to eligible melee attacks. |
| `stealthy` | Reduces eligible random encounter checks from 20% to 10%. |
| `slow metabolism` | Consumes expedition food every four moves instead of every two. |
| `desert rat` | Consumes water every two moves instead of every move. |
| `boxer` | Doubles unarmed damage. |
| `martial artist` | Triples unarmed damage; stacks with other enabled unarmed perks. |
| `unarmed master` | Doubles unarmed damage and halves the unarmed attack cooldown. |

Perks do not supply equipment/resources or implicitly enable other perks.

## Generated state and validation

`tools/debug_saves.py` resolves the **current** assembler symbols, boots a
disposable RT-11 disk, and applies each JSON state at a stopped main-loop
boundary. It then calls the real `MAP_INIT`, `CAPACITIES`, `WEIGH`,
`SNAPSHOT_WORLD`, and `SV_SAVE` routines. It does not reimplement the game world
generator or native save serializer in Python.

The native calls generate the world and village position, derived capacities,
packed weight, PRNG continuation and expedition rollback snapshot. Scene memory
is cleared because neither checkpoint has an active scene. Timers, cooldowns,
event logs, enemies, flight debris, visited-site state and temporary UI state
start cleared. `reveal_map` controls visibility, not exploration completion.
The native save contains the complete supported state, including the generated
map and rollback data, in the same format as a manual save.

The compiler checks field names, integer ranges, resource/building/job names,
building caps, population/housing, specialist totals, seed, starting panel,
required compass/ship/hull, native save success, bag weight and HP/water limits.
A failure does not replace the existing release disk. It does not simulate a
campaign to prove every combination historically reachable; these are deliberate
debug checkpoints.

Outputs are cached only when their hashes match the current SAV, DAT, source
JSON and compiler. Recompilation from the same inputs produces identical slot
files. Native compiler scripts/logs are under `tmp/debug-save-compiler/`.

Run `python3 tools/verify_debug_saves.py` after building to load both slots and
start an expedition and flight through physical keys. `make verify` includes
these checks plus the complete native regression suite.
