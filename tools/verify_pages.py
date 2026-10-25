"""Native opening/ending behavior and independent ROM raster checks."""
from test_support import Scenario, ROOT


def verify_pages(check):
    from PIL import Image

    def visual(s, name, snap):
        prefix = ROOT / f'tmp/{s.name}-{name}'
        image = Image.open(prefix.with_suffix('.bmp')).convert('RGB')
        image.save(prefix.with_suffix('.png'))
        check(not any(prefix.with_suffix('.overlay-plane').read_bytes()), name + ': full clear leaves no frame, tab, bar or focus pixels')
        rom = (ROOT / 'bin/ukncbtl/uknc_rom.bin').read_bytes()
        text = snap.data[s.s['SCREEN_BUF']:s.s['SCREEN_BUF'] + 1920]
        expected = bytearray(23040)
        for cell, code in enumerate(text):
            source = code + 160 if 64 <= code < 96 else code - 32 if code >= 96 else code
            offset = 0o20170 + (source - 32) * 11
            for y, bits in enumerate(rom[offset:offset + 11]):
                expected[(cell // 80 * 12 + y) * 80 + cell % 80] = bits
        check(prefix.with_suffix('.text-plane').read_bytes() == expected, name + ': original Cyrillic and uppercase Latin ROM glyphs render exactly')
        check(all(image.getpixel((col*8+bit, y)) == ((255,255,255) if expected[y*80+col] & (1<<bit) else (0,0,0)) for y in range(288) for col in range(80) for bit in range(8)), name + ': actual display is white text on a fully cleared black screen')
        check(snap.screen().splitlines()[23].endswith('V1.0.0'), name + ': exact release version is visible')
        for line in snap.screen().splitlines()[:23]:
            if line.strip():
                left = len(line) - len(line.lstrip())
                right = len(line) - len(line.rstrip())
                check(abs(left - right) <= 1, name + ': text line is centered')

    s = Scenario('release-splash', splash=True).snap('splash').shot('splash').run(300).snap('wait')
    for key in ['SPACE', '1', 'F1', 'F2', 'AP2']:
        s.key(key, 10)
    s.snap('ignored').key('ENTER', 50).snap('started').shot('started')
    r = s.execute()
    text = r['splash'].screen()
    for wanted in ['A DARK ROOM', 'CHATGPT CODEX', 'СЕРГЕЙ ЛЕМЕШЕВ', 'MICHAEL TOWNSEND',
                   'HTTPS://ADARKROOM.DOUBLESPEAKGAMES.COM', 'HTTPS://GITHUB.COM/DOUBLESPEAKGAMES/ADARKROOM',
                   'ПЕНЗА, 25 ОКТЯБРЯ 2026']:
        check(wanted in text, 'splash contains ' + wanted)
    check(r['wait'].screen() == text == r['ignored'].screen(), 'splash waits for Enter with no gameplay or incidental key actions')
    check(r['wait'].word('SECONDS') == 0 and r['wait'].word('TENTHS') == 0, 'game clocks have not begun on splash')
    check(r['started'].word('FIRE') == 0 and r['started'].word('WON') == 0 and 'РАЗЖЕЧЬ ОГОНЬ' in r['started'].screen(), 'Enter begins a fresh playable game')
    visual(s, 'splash', r['splash'])
    stop = Scenario('release-splash-exit', splash=True).key('STOP', 300).snap('exit').command('DIR').command('R DARKRM', 1100).snap('again').shot('again')
    q = stop.execute()
    check(q['exit'].word('PP_READY') == 0 and q['again'].word('PP_READY') == 1 and 'ПРИВЕТСТВУЮ ВСЕХ!' in q['again'].screen(), 'STOP on splash restores RT-11 and permits DIR/relaunch')
    visual(stop, 'again', q['again'])

    for beacon in [False, True]:
        t = Scenario('release-ending' + ('-beacon' if beacon else ''), save_writes=True)
        t.stock('fleet beacon', int(beacon)).stock('wood', 123).word('HULL', 20).call('LIFTOFF').run(10).shot('flight')
        t.word('ALTITUDE', 59).word('SPACE_CLOCK', 9).call('SPACE_TICK').run(25).snap('end').shot('end').run(300).snap('wait')
        t.key('ENTER', 10).key('SPACE', 10).key('7', 10).snap('ignored')
        t.key('F2', 40).key('ENTER', 600).key('F1', 40).key('ENTER', 600).snap('loaded').shot('loaded')
        t.key('1', 50).snap('new').shot('new')
        t.word('HULL', 20).call('LIFTOFF').word('ALTITUDE', 59).word('SPACE_CLOCK', 9).call('SPACE_TICK').run(20).key('2', 300).snap('exit').command('DIR').command('R DARKRM', 1100).snap('splash')
        r = t.execute()
        check(r['end'].word('WON') == 1 and r['end'].word('TAB') == 12, 'successful flight opens the ending')
        check(('МАЯК ТИХО ПУЛЬСИРУЕТ' if beacon else 'ЗВЕЗДЫ. КОРАБЛЬ ПОКИДАЕТ ЭТОТ МИР.') in r['end'].screen(), 'correct ending narrative remains intact')
        check('1: НОВАЯ ИГРА    2: ВЫХОД В ОС' in r['end'].screen().splitlines()[23], 'both ending choices are on the bottom row')
        for name in ['wait', 'ignored', 'loaded']:
            check(r[name].screen() == r['end'].screen(), name + ': only explicit ending choices leave the cleared page')
            check(all(r[name].word(k) == r['end'].word(k) for k in ['SECONDS','TENTHS','ALTITUDE','STOKE_CD','EVENT_TIME']), name + ': ending freezes gameplay')
        visual(t, 'end', r['end'])
        visual(t, 'loaded', r['loaded'])
        check(r['new'].word('WON') == 0 and r['new'].word('TAB') == 0 and r['new'].word('FIRE') == 0 and r['new'].stock('wood') == 0 and 'РАЗЖЕЧЬ ОГОНЬ' in r['new'].screen(), 'New Game resets ending, inventory and world state and returns to playable room')
        check(r['exit'].word('PP_READY') == 0 and 'ПРИВЕТСТВУЮ ВСЕХ!' in r['splash'].screen(), 'Exit to OS releases PPU and supports DIR/relaunch')
    print('centered uppercase splash, both cleared endings, pause, save/load, new game and OS exit: OK', flush=True)


if __name__ == '__main__':
    count = 0
    def check(ok, message):
        global count
        count += 1
        if not ok:
            raise AssertionError(message)
    verify_pages(check)
    print(f'PASS: {count} page checks')
