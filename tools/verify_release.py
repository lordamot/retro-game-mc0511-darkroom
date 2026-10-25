"""Release disks contain only authorized saves and boot as native RT-11 games."""
from test_support import Scenario, ROOT
from rt11fs import Volume
from debug_saves import contents, is_debug_save
from release import export


def verify_release(check):
    source = ROOT / 'build/darkroom.dsk'
    before = source.read_bytes()
    clean, debug = export(ROOT / 'tmp/release-check')
    check(source.read_bytes() == before, 'release export preserves the complete working disk and manual saves')
    working = Volume(source)
    for path, slots in [(clean, []), (debug, [2, 3])]:
        volume = Volume(path)
        startup = contents(volume, 'STARTS.COM').split(b'\0')[0].splitlines()
        check(startup[0] == b'SET TT SCOPE,QUIET' and b'R DARKRM' in startup, path.name + ': autostart enables SCOPE terminal mode before running the game')
        check([n for n in range(1, 6) if volume.find(f'DRSAV{n}.DAT')] == slots, path.name + ': exact released save-slot inventory')
        for entry in working.read_dir()[1]:
            if entry.status & 0o2000 and not entry.name.startswith('DRSAV'):
                check(contents(volume, entry.name) == contents(working, entry.name), path.name + ': preserves ' + entry.name)
        check(all(not any(volume.img[e.block * 512:(e.block + e.length) * 512]) for e in volume.read_dir()[1] if e.status & 0o1000), path.name + ': free space contains no deleted manual-save payload')
    for n in [2, 3]:
        check(is_debug_save(contents(Volume(debug), f'DRSAV{n}.DAT')), 'release debug slot is a generated preset')
    c = Scenario('release-clean-disk', clean).key('F1', 40).snap('slots').shot('slots')
    r = c.execute()['slots']
    check(r.screen().count('ПУСТО') == 5, 'clean release boots and all five slots are visibly empty')
    d = Scenario('release-debug-disk', debug).key('F1', 40).snap('slots').key('DOWN', 5).key('ENTER', 600).snap('expedition')
    d.key('F1', 40).key('DOWN', 5).key('DOWN', 5).key('ENTER', 600).snap('ship')
    r = d.execute()
    check(r['slots'].screen().count('ЕСТЬ СОХРАНЕНИЕ') == 2 and r['slots'].screen().count('ПУСТО') == 3, 'debug release exposes only the two presets')
    check(r['expedition'].word('TAB') == 6 and r['expedition'].stock('compass') == 1, 'exported expedition preset loads natively')
    check(r['ship'].word('TAB') == 7 and r['ship'].word('HULL') == 50, 'exported spaceship preset loads natively')
    print('clean/debug release packaging, empty free space, boot and preset loads: OK', flush=True)


if __name__ == '__main__':
    count = 0
    def check(ok, message):
        global count
        count += 1
        if not ok:
            raise AssertionError(message)
    verify_release(check)
    print(f'PASS: {count} release checks')
