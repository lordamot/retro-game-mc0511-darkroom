"""Physical-key acknowledgement, pause, defeat and persistence scenarios."""
from test_support import Scenario, ROOT, CAT


def verify_travel(check):
    from PIL import Image
    import struct
    import syms
    scene_base = int(syms.table()["SCENE_BASE"], 8)

    bank = (ROOT / "build/DARKRM.DAT").read_bytes()
    compact_ok = True
    for scene in CAT["scenes"]:
        start = scene["block"] * 512
        header = struct.unpack_from("<16H", bank, start)
        if not header[13]:
            compact_ok &= header[2] == 0
            continue
        def prose(pointer):
            return bank[start + pointer - scene_base:].split(b"\0")[0]
        lines = prose(header[13]).splitlines()
        compact_ok &= len(lines) <= 4 and all(len(line.strip()) <= 44 for line in lines)
        compact_ok &= b" ".join(prose(header[1]).split()) == b" ".join(prose(header[13]).split())
        compact_ok &= len(prose(header[0])) <= 44
    check(compact_ok, "all encounter and defeat dialogs fit the compact frame without losing prose")

    clocks = ['HP', 'ENEMY_HP', 'ENEMY_CLOCK', 'ENEMY_SPAN', 'SPECIAL_CLOCK',
              'STATUS_TIME', 'POISON_CLOCK', 'STIM_TIME', 'SHIELD_TIME',
              'TENTHS', 'SECONDS', 'EVENT_TIME', 'STOKE_CD', 'DEATH_CD', 'SEED']

    def frozen(a, b, context):
        check(all(a.word(k) == b.word(k) for k in clocks), context + ': game and combat clocks freeze')
        off = a.s['LOG_AGE']
        check(a.data[off:off + 10] == b.data[off:off + 10], context + ': event-log ages freeze')

    def visual(scenario, name, snapshot, button):
        prefix = ROOT / f'tmp/{scenario}-{name}'
        im = Image.open(prefix.with_suffix('.bmp')).convert('RGB')
        im.save(prefix.with_suffix('.png'))
        border = {(x, y) for x in range(128, 512) for y in [71, 216]}
        border |= {(x, y) for x in [128, 511] for y in range(71, 217)}
        button_border = {(x, y) for x in range(280, 360) for y in [191, 204]}
        button_border |= {(x, y) for x in [280, 359] for y in range(191, 205)}
        check(all(im.getpixel(p) == (255, 255, 255) for p in border | button_border), name + ': window and button have complete white frames')
        check(all(im.crop(box).getbbox() is None for box in [(0,0,640,71),(0,217,640,276),(0,71,128,217),(512,71,640,217)]), name + ': black background has no old heading, stocks or log')
        # Prove the frames and animated selection leave every ROM glyph intact,
        # including the accent on Й in БОЙ and wrapped defeat prose.
        data, syms = snapshot.data, snapshot.s
        text = data[syms['SCREEN_BUF']:syms['SCREEN_BUF'] + 1920]
        expected = bytearray(23040)
        for cell, code in enumerate(text):
            glyph = syms['FONT'] + ((code & 127) - 32) * 11
            for y in range(11):
                expected[(cell // 80 * 12 + y) * 80 + cell % 80] = data[glyph + y]
        check(prefix.with_suffix('.text-plane').read_bytes() == expected, name + ': original font pixels survive modal framing')
        overlay = prefix.with_suffix('.overlay-plane').read_bytes()
        dots = {(x, y) for x in range(288, 296) for y in range(192, 203)}
        pixels = {(col * 8 + bit, y) for y in range(288) for col in range(80)
                  for bit in range(8) if overlay[y * 80 + col] & (1 << bit)}
        check(pixels <= border | button_border | dots, name + ': no stale tab, cooldown or cursor pixels remain')
        check(button in snapshot.screen().splitlines()[16], name + ': correct acknowledgement button is visible')
        check(snapshot.screen().splitlines()[23].rstrip().endswith('V1.0.0'), name + ': exact-case version footer remains visible')

    # Native seed 12 selects the bird on the second near-field step. The first
    # step cannot encounter an enemy yet; the held-key repeat opens the prompt
    # inside TICK, which must return without attacking or taking a third step.
    s = Scenario('travel-arrival', save_writes=True).stock('cured meat', 10, True).call('EMBARK')
    s.flag('ship').word('LAST_FIGHT', 1).word('SEED', 12).byte('WORLD_MAP', 1, 1861).byte('WORLD_MAP', 1, 1862)
    s.lines += ['keydown 133', 'run 80', 'keyup 133', 'run 5']
    s.snap('arrival').shot('arrival').run(200).snap('waited')
    for key in ['SPACE', 'LEFT', 'RIGHT', 'UP', 'DOWN', '1', '2', '7', 'AP2']:
        s.key(key, 10)
    s.run(31).snap('ignored').shot('ignored')
    s.key('F2', 40).key('ENTER', 600).snap('saved').shot('saved')
    s.key('F1', 40).key('ENTER', 600).snap('loaded').shot('loaded')
    result = s.execute()
    arrival = result['arrival']
    bird = next(x['id'] for x in CAT['scenes'] if x['group'] == 'encounters' and x['event'] == '2')
    check(arrival.word('SCENE_ID') == bird and arrival.word('TR_MODE') == 1 and arrival.word('POS_X') == 32, 'held travel opens a bird encounter inside TICK without moving again')
    check(arrival.word('HP') == 10 and arrival.word('ENEMY_HP') == 4 and arrival.word('ENEMY_CLOCK') == 20, 'encounter begins with full health and the untouched enemy delay')
    body = arrival.word('SCENE_BASE', 26)
    text = arrival.data[body:].split(b'\0')[0]
    original = arrival.data[arrival.word('SCENE_BASE', 2):].split(b'\0')[0]
    visible = b' '.join(arrival.data[s.s['SCREEN_BUF'] + row * 80 + 18:][:44].strip() for row in range(9,13))
    check(b' '.join(visible.split()) == b' '.join(text.split()) == b' '.join(original.split()) and 'ПРИГОТОВЬТЕСЬ К БОЮ!' in arrival.screen(), 'encounter dialog repeats the actual scene description and fight prompt')
    for name in ['waited', 'ignored', 'saved', 'loaded']:
        check(result[name].word('TR_MODE') == 1 and result[name].word('POS_X') == 32 and result[name].stock('cured meat', True) == 9, name + ': only acknowledgement can leave the encounter')
        frozen(arrival, result[name], name)
    visual(s.name, 'arrival', arrival, 'БОЙ')
    visual(s.name, 'loaded', result['loaded'], 'БОЙ')

    # Reboot into the saved prompt, then let the native enemy deal a fatal hit.
    # Keeping Enter held through that hit must not dismiss the defeat dialog.
    d = Scenario('travel-defeat', s.disk, save_writes=True).key('F1', 40).key('ENTER', 600)
    d.snap('restored').shot('restored').run(150).snap('restored-wait')
    d.word('SCENE_BASE', 10, 6).word('SCENE_BASE', 100, 10)
    d.lines += ['keydown 153', 'run 120', 'keyup 153', 'run 31']
    d.snap('defeat').shot('defeat').run(200).snap('defeat-wait')
    for key in ['SPACE', 'AP2', 'RIGHT', '7']:
        d.key(key, 10)
    d.snap('ignored').key('F2', 40).key('ENTER', 600).snap('saved').shot('saved')
    d.key('ENTER', 50).snap('home').shot('home')
    defeated = d.execute()
    check(defeated['restored'].word('TR_MODE') == 1 and defeated['restored'].word('ENEMY_CLOCK') == 20, 'reboot/load restores the pending encounter, not active combat')
    frozen(defeated['restored'], defeated['restored-wait'], 'rebooted encounter')
    loss = defeated['defeat']
    check(loss.word('TR_MODE') == 2 and loss.word('DEATHS') == 1 and loss.word('AWAY') == 0, 'Enter starts combat; a lethal enemy attack opens defeat until a fresh Enter')
    check(loss.stock('cured meat', True) == 0 and loss.stock('cured meat') == 0 and loss.word('FLAGS') == 0, 'defeat loses the bag and rolls back expedition discoveries')
    check(loss.word('DEATH_CD') == 1200 and 'ПОРАЖЕНИЕ' in loss.screen() and 'КОЧЕВНИКИ' in loss.screen(), 'defeat explains the loss and rescue and starts the normal recovery wait')
    for name in ['defeat-wait', 'ignored', 'saved']:
        check(defeated[name].word('TR_MODE') == 2, name + ': defeat requires fresh Enter')
        frozen(loss, defeated[name], name)
    visual(d.name, 'defeat', loss, 'ЖАЛЬ')
    visual(d.name, 'saved', defeated['saved'], 'ЖАЛЬ')
    check(defeated['home'].word('TR_MODE') == 0 and defeated['home'].word('TAB') == 0 and defeated['home'].word('DEATHS') == 1, 'fresh Enter returns to the room without repeating death handling')
    home = Image.open(ROOT / 'tmp/travel-defeat-home.bmp').convert('RGB')
    check(home.crop((128, 216, 512, 217)).getbbox() is None, 'returning home removes the modal frame completely')

    reboot = Scenario('travel-defeat-reboot', d.disk).key('F1', 40).key('ENTER', 600).snap('restored').shot('restored')
    reboot.run(100).snap('waited').key('ENTER', 50).snap('home')
    rr = reboot.execute()
    check(rr['restored'].word('TR_MODE') == 2 and rr['restored'].word('DEATHS') == 1, 'reboot/load preserves the defeat explanation')
    frozen(rr['restored'], rr['waited'], 'rebooted defeat')
    visual(reboot.name, 'restored', rr['restored'], 'ЖАЛЬ')
    check(rr['home'].word('TR_MODE') == 0 and rr['home'].word('DEATHS') == 1, 'loaded defeat can be acknowledged exactly once')

    for cause in ['hunger', 'thirst']:
        t = Scenario('travel-' + cause).stock('cured meat', 0 if cause == 'hunger' else 3, True).call('EMBARK')
        for offset in [1861, 1862, 1863]:
            t.byte('WORLD_MAP', 15, offset)
        if cause == 'hunger':
            t.word('MOVES', 1).key('RIGHT', 10).snap('warning').key('RIGHT', 10).key('RIGHT', 50)
        else:
            t.word('WATER', 0).key('RIGHT', 10).snap('warning').key('RIGHT', 50)
        t.snap('defeat').shot('defeat').run(100).snap('waited')
        if cause == 'thirst':
            t.key('STOP', 300).snap('exit').command('DIR').command('R DARKRM', 1100).snap('relaunch')
        else:
            t.key('ENTER', 50).snap('home')
        q = t.execute()
        check(q['warning'].word('TR_MODE') == 0 and q['warning'].word('AWAY') == 1, cause + ': first deprivation warning does not end the expedition')
        check(q['defeat'].word('TR_MODE') == 2 and q['defeat'].word('DEATHS') == 1 and q['defeat'].stock('cured meat', True) == 0, cause + ': actual movement exhaustion opens defeat and loses supplies')
        check(('ОТ ГОЛОДА' if cause == 'hunger' else 'ОТ ЖАЖДЫ') in q['defeat'].screen(), cause + ': explanation states the actual cause')
        frozen(q['defeat'], q['waited'], cause)
        visual(t.name, 'defeat', q['defeat'], 'ЖАЛЬ')
        if cause == 'thirst':
            check(q['exit'].word('PP_READY') == 0 and q['relaunch'].word('PP_READY') == 1 and q['relaunch'].word('TR_MODE') == 0, 'STOP from defeat restores RT-11, DIR and a clean relaunch')
        else:
            check(q['home'].word('TR_MODE') == 0 and q['home'].word('TAB') == 0, 'hunger defeat acknowledgement returns to the room')
    print('travel acknowledgement, frozen clocks, combat/hunger/thirst defeat, frame cleanup and saved dialogs: OK', flush=True)


if __name__ == '__main__':
    count = 0
    def check(ok, message):
        global count
        count += 1
        if not ok:
            raise AssertionError(message)
    verify_travel(check)
    print(f'PASS: {count} travel checks')
