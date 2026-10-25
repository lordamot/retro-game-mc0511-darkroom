# Keyboard

No Russian host keyboard layout is needed. Game controls use UKNC scancodes;
the SDL player maps Latin letter keys logically for RT-11 commands such as
`R DARKRM` and `DIR`. The game itself does not require typing words.

| Context | Keys | Action |
| --- | --- | --- |
| Menus | Up / Down | Previous / next item |
| Menus | Left / Right | Previous / next page of ten |
| Menus | Enter | Perform selected action |
| Home | 1 / 2 | Room / forest |
| Home | 3 / 4 / 5 | Buildings / crafting / trade |
| Home | 6 | Jobs; Left removes, Right assigns; Enter is inert |
| Home | 7 | Expedition packing; press 7 again to depart |
| Home | 8 / 9 | Ship / fabricator, once discovered |
| Home | 0 | Help |
| Help | Space | Full home stocks and learned perks |
| Room / forest | Space | Stoke / gather wood |
| Packing | Enter / Space | Pack one / return one item to stores |
| World | Arrows | Walk one cell; held arrows repeat |
| World | Enter | Inspect current landmark |
| World | Space / 0 | Eat / open carried inventory |
| Carried inventory | Enter / Space | Discard selected item / eat |
| Combat | Enter | Selected weapon or healing action |
| Combat | Space | First equipped, ready weapon with ammunition |
| Combat | 1 / 2 | Eat meat / use medicine |
| Loot | Enter / Space | Take one selected item / take all that fits |
| Flight | Arrows | Move horizontally or vertically |
| Lists | Tab (UKNC АР2) | Back to the previous context |
| Normal game screens | F1 / К1, F2 / К2 | Open load / save window |
| Save/load window | Up / Down, Enter | Select one of five slots, then load/save |
| Save/load window | Tab / АР2, Escape / STOP | Cancel and resume |
| Normal game screens | Escape / UKNC STOP | Exit to RT-11; no automatic save |
| Help | Enter | Exit to RT-11 |
| Emulator | Close window | Quit the emulator |

Tabs unlock with progression. Story choices cannot be dismissed with АР2;
choose an offered route or leave action. Fight before taking an enemy's loot.
The packing menu includes an explicit departure action as well as the 7 shortcut.
Discarding items in the field destroys them. Returning to the village transfers
the surviving bag to stores; death loses the bag and uncommitted world discoveries.

The on-screen footer describes the current context. Native hardware uses ВВОД
for Enter and АР2 for Tab. STOP/Escape restores the system console and exits;
it is not a pause command. The simulation continues in ordinary menus and pauses in Help and save/load windows.
At the RT-11 prompt, `R DARKRM` starts a fresh game; use F1 to load a slot.
Keep DARKRM.DAT and DRSAV1.DAT–DRSAV5.DAT on DK:.

A six-pixel snake follows a square inside one character before the selected row.
It follows menu pages and disappears on read-only lists. Static white/gray frames
mark the current and other usable locations. Hidden shortcuts do nothing silently;
blocked shortcuts have no frames. The slot window uses the same selection snake.

White 56-pixel bars replace countdown numbers for fire, gathering, traps,
attacks, departure after death, and launch after a crash. A full bar is the full
wait; an empty bar means ready. The fill shrinks with pixel precision within
seven character cells. Quantities and upgrade levels stay numeric.


In ЖИТЕЛИ, ЛЕСНИК is a read-only count outside the selectable jobs. Assigning
a specialist takes a gatherer; removing a specialist returns one.
