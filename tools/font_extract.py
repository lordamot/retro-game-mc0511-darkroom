#!/usr/bin/env python3
"""Extract the bundled UKNC firmware font as readable 8x11 KOI-7 glyphs."""
import argparse
import hashlib
from pathlib import Path

ROM_SHA256 = 'a5bfbcefa5c1d533b0aa4d86d9f95855b68f93fcdb4c681a7dff1b48e55dfe74'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom', type=Path, default=Path('bin/ukncbtl/uknc_rom.bin'))
    ap.add_argument('--out', type=Path, default=Path('src/res/font8x11.txt'))
    args = ap.parse_args()
    rom = args.rom.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
        ap.error('unknown firmware revision; font address/mapping must be audited first')
    # UKNCBTL qscreen.cpp's standard font: PPU 0120170, ROM base 0100000.
    # 224 glyphs, codes 040..377, 11 consecutive bytes each, bit 0 at left.
    lines = [
        '# UKNC firmware 8x11 font; extracted by tools/font_extract.py.',
        '# ROM SHA-256: ' + ROM_SHA256,
        '# PPU address 0120170 (ROM offset 020170), 11 bytes per glyph.',
        '# Punctuation/digits: ROM 040..077; Cyrillic uppercase: ROM 340..377.',
        '# Game codes 100..137 map to ROM 340..377 (KOI-7 Cyrillic order).',
        '# Game codes 140..177 map to ROM 100..137 for Latin capitals.',
        '# Eleven rows per glyph; # is lit, . is dark, left to right.',
    ]
    cyrillic = 'ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧЪ'
    for code in range(32, 128):
        source = code + 160 if 64 <= code < 96 else code - 32 if code >= 96 else code
        offset = 0o20170 + (source - 32) * 11
        label = cyrillic[code - 64] if 64 <= code < 96 else chr(code - 32) if code >= 96 else chr(code)
        lines += ['', f'char {code:03o} {label}']
        lines += [''.join('#' if row & (1 << x) else '.' for x in range(8))
                  for row in rom[offset:offset + 11]]
    args.out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'-> {args.out}: 96 firmware glyphs, 8x11')

if __name__ == '__main__':
    main()
