# UKNC and RT-11 platform

All addresses below are **octal** unless explicitly marked decimal. MACRO-11
also defaults to octal; decimal constants in source have a trailing dot.

## CPU memory and SAV startup

| Region | Use |
| --- | --- |
| 000000–000777 | RT-11 vectors, communication area and initial stack; not game code |
| 001000–`RESIDENT_END` | SAV entry, game code/state, map arrays, resource tables and font |
| `RESIDENT_END`–123777 | Free resident margin |
| 124000–125777 | Scene window, up to 1024 decimal bytes (also persisted in slots) |
| 126000 | Headless `callcpu` return breakpoint, test-only scratch |
| 126776 | Headless scratch stack, below the normal game stack |
| 127000–127777 | Descending game stack; initial SP = 130000 |
| 130000 and above | Leave available to RT-11, its USR, handlers and monitor |

Read current symbol addresses with `tools/syms.py`. Do not copy old listing
addresses. The SAV has start 001000 and initial SP 001000. RT_ENTRY saves that
SP and uses `.SETTO #130000` before switching to the game stack. Insufficient
memory returns to the monitor with a diagnostic before touching the PPU.
The ordinary SAV load occupies about 42 KiB; it does not load the scene bank.

**Never replace CPU vector 0100 or allocate the old standalone stack at 157000.**
All CPU monitor vectors remain installed, including its timer and EMT service.
The startup/exit model follows the supplied `orig/loader/source/LOADER.MAC` and
its SYSMAC library. RT-11 requests preserve registers other than R0 according to
DEC's [Programmer's Reference Manual](https://www.bitsavers.org/pdf/dec/pdp11/rt11/v5.0_Mar83/AA-H378B-TC_5.0_PgmRefMan.pdf).

## PPU, video and input

The CPU allocates PPU RAM through firmware channel K2 (command 1), uploads the
position-independent code (20), and runs it (30). Extra allocated space holds
the backup of PPU 02300–07027, including the firmware display tables and chain
pointers. It is reserved in the allocation, not emitted into the SAV.

Before takeover, the PPU entry saves its timer/keyboard vector addresses and
drawing registers. It preserves its caller's registers/PSW and raises priority
while changing tables. Internal references stay PC-relative after relocation.
The custom keyboard ISR at vector 0300 and clock ISR at 0100 publish key code,
press sequence, 50 Hz clock and held key into CPU RAM. Firmware floppy timer
housekeeping remains active. CPU terminal input interrupts are disabled during
play; the original terminal CSR is retained for exit.

Video is 640×288, with 80 bytes per scanline and the firmware's original 8×11
glyphs. Twelve scanlines per text row give 24 rows, with one blank scanline
between rows. `src/res/font8x11.txt` contains the ROM glyphs: punctuation/digits
from codes 040–077 and uppercase Cyrillic from 340–377, remapped to the game's
KOI-7 codes 100–137. Codes 140–177 map to ROM 100–137 for Latin capitals in credits, URLs and
the V1.0.0 version label. The compiler encodes Latin A–Z into 141–172; the
version renderer maps its ASCII V into that bank. The renderer writes all eleven glyph rows, including blanks
when replacing a character. Palette index 0 is black; plane 1 selects
index 2, configured with 07400 for bright white. Only changed cells are drawn.
SDL stretches the raw image to a 4:3 window; raw screenshots are 640×288.

Each text row now has 56 bytes of PPU display tags starting at 02410: a palette
tag on scanline 0, ten ordinary tags, and a parameter tag on blank scanline 11
for the next row. The four-word tags are eight-byte aligned. Parameters therefore
take effect before the next glyph's first pixel (including Й's accent). The
complete table remains within the existing PPU backup/restore range.

Video plane 2 carries UI decorations and gray glyph attributes. Palette index 4
is white and index 6 (both CPU-accessible planes) is gray (`03417` in each row's
high palette word). Bit 7 in SCREEN_BUF/SCREEN_OLD marks disabled recipe cells;
FLUSH retains their original plane-1 glyph and duplicates it into plane 2.
Color-only changes participate in the character diff cache. Ordinary text clears
its previous overlay bytes when redrawn. Log glyphs remain exclusively plane 1.

Numbered tabs occupy text rows 1 and 2, with static 1-pixel frames in padding
cells, the unused first scanline of each tab glyph, and the blank scanline after
each row. The native font is unchanged; verification checks the empty first
scanline for every tab label. Active frames use plane 2 alone; inactive
frames use both planes. Frame records are compared before erasing old geometry,
so ordinary redraws do not blink. Help and blocked navigation have no frame.
The selected row has six connected pixels moving at 10 Hz around a 6×6 square
within column 1, leaving the label at column 2 untouched. Cooldown bars occupy 56×3 pixels at
x=384–439. Stale bars are cleared before FLUSH so they cannot erase gray counts.
All decorations stay below video offset 155000, leaving the expedition snapshot
untouched. No full overlay-plane clear runs per frame.

The PPU timer reads five CPU `LOG_SHADE` words, clamps uninitialized values,
and updates only rows 18–22. Palette index 2 uses YRGB 7 or 15, with all RGB
attenuation bits equal, producing grayscale 96/128/223/255 and black. No extra
video planes or pixel masks are needed for log fading. Palette changes affect unchanged glyphs
without invalidating SCREEN_OLD. Hidden-log views publish white shades; the
footer's parameter tag always resets white. Original RT-11 palette/display tags
are restored with the rest of the PPU backup on exit.

CPU video ports are 176640/176642; PPU-side window ports include 177010/177014.
Plane offsets below 100000 alias CPU RAM. Never draw there. The expedition
snapshot starts at **video-plane offset** 155000 and occupies 5582 word positions
across the two data planes. This is above the visible 23,040-byte image in each
plane, and is unrelated to CPU address 155000. It does not overwrite RT-11.

## File reads and clean exit

The disk retains the supplied RT-11 filesystem, boot sector and system files.
Its generated STARTS.COM uses `SET TT SCOPE,QUIET` before `R DARKRM`, preserving
the base disk's USR/EXIT NOSWAP settings. The original base image is not edited.
RT_ENTRY opens `DK:DARKRM.DAT` on channel 0 with `.LOOKU`. It checks the block
count and reads/compares the pairing header before PPU takeover. Each scene is
then fetched by `.READW` using its **file-relative** block, buffer and word count.
Scene reads retry the same whole record up to three times after an RT-11 error;
exhaustion still restores the terminal and returns to the monitor. This covers
transient firmware/FDD errors observed during repeated native reads.
The file can move to other physical sectors without rebuilding the SAV.

STOP/Escape, Help's exit action, and runtime read errors share cleanup:

1. Run the PPU restoration entry with interrupts masked during restoration.
2. Restore its firmware timer/keyboard vectors, saved display tables and drawing
   registers, then stop publishing game state into CPU RAM.
3. Release the allocated PPU block using firmware command 2.
4. Clear the restored terminal through its output register and restore the CPU
   terminal CSR.
5. `.PURGE` channel 0, restore the initial stack, and `.EXIT` into RT-11.

Missing/incompatible data and memory failures occur before graphics takeover.
Normal quit has no reset, reboot, forced monitor jump or hidden emulator action.
The monitor's original console colors are restored; white-on-black is the game
palette only. Repeated launch tests confirm PPU allocation reuse and working
keyboard, directory commands and disk reads after exit.

## Timing and tests

UKNCBTL SystemFrame is 1/25 second with two 50 Hz interrupts. The game tick is
1/10 second. SDL throttles play to 25 frames/second and accelerates firmware/RT-11
startup. Headless execution is unthrottled; host time is not game time.

`callcpu` is emulator-only: it saves CPU state, uses its separate scratch stack
and return breakpoint, executes the routine with optional R0–R5 inputs, then
restores the CPU. Full system frames keep RT-11, PPU and FDD interrupts working.
It is not used to exit: exit tests send real STOP/Enter keys and issue RT-11
commands. There is no debug-call interface in the released SAV.

Validated with the supplied RT-11SJ V05.04 G image and bundled UKNCBTL core.
Physical UKNC hardware and other RT-11 builds/configurations remain unverified.

RT-11 can temporarily write user-memory pages to `SWAP.SYS` when loading its
USR for monitor requests, as described in the Programmer's Reference Manual
linked above (page 1–15). The larger SAV now exercises this normal OS path;
blocks 14–15 changed during verification, both inside SWAP.SYS. This is not game
persistence. Scenario tests boot disposable disk copies and assert that every
byte outside the existing SWAP.SYS extent stays unchanged, including SAV, DAT,
directory and system files. The generated release image remains untouched.

## Save/load staging and RT-11 writes

The five DRSAVn.DAT files are the only game-written files. They use normal RT-11
channel 1 services; channel 0 remains open for DARKRM.DAT. SV_AREA is separate
from RT_AREA. Missing files are distinguished from device errors using LOOKUP's
error byte 52 (code 1 means not found). A new tentative file is committed with
CLOSE only after every block and its header have been written. Failed ENTER or
WRITW leaves the existing slot permanent and usable.

Loading starts temporary staging at video offset 117000, below snapshot offset
155000. SV_ADVANCE walks row 8, skips rows 9–14, walks rows 15–22, then wraps
to row 0 before reaching the footer. The 17 hidden rows provide 16,320 video
word positions; the padded candidate currently needs 13,056. Each video word spans planes 1/2, providing enough capacity for the full
state/scene/snapshot payload without changing CPU scene/stack addresses. SV_HIDE
and SV_ACK form a CPU/PPU handshake: the timer masks palette words on rows 0–8 and 15–22
before copying begins. It skips log palette updates while hidden. Rows 9–14
and the version footer remain visible throughout validation. Commit occurs only after complete file
validation. The CPU then clears staged pixels before requesting palette restore.
This path never replaces monitor vectors or restores stale hardware registers
from a save file.

Before the first save/load monitor request, SV_BUSY clears both visible planes
and replaces the picker with a centered 384×72-pixel frame at (128,108), a
centered Russian operation label and a progress outline at x=144–495, y=156–165.
SV_PROGRESS draws directly to plane 1 because SCREEN_BUF/SCREEN_OLD are disk
scratch during transfers. Its 336-pixel fill advances after each successful data
block; the final portion is reserved for header/CLOSE on save or validation and
commit on load. The progress pixels never overlap candidate or rollback data.
Success and error cleanup both erase the bar before resuming play or the picker.
SV_CLEAR resets the character cache to spaces matching the cleared planes,
avoiding a redundant full-screen blank rasterization before showing progress.

Save-enabled test scenarios allow directory/free-space changes for DRSAV1.DAT
through DRSAV5.DAT and check that boot bytes and every pre-existing system/game
file retain their contents and extents. Other scenarios retain the strict rule
that only SWAP.SYS may change; the released build disk is never used as a test
write target.
