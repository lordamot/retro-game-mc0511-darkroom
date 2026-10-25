"""Load the baked JSON presets and start their actions using physical keys."""
import subprocess

from debug_saves import contents, is_debug_save, compile_saves
from rt11fs import Volume
from test_support import Scenario, ROOT, CAT


def verify_debug_saves(check):
    volume = Volume(ROOT / 'build/darkroom.dsk')
    for slot in (2, 3):
        check(volume.find(f'DRSAV{slot}.DAT') is not None, f'debug slot {slot} is baked into the disk')
        check(is_debug_save(contents(volume, f'DRSAV{slot}.DAT')), f'debug slot {slot} is identifiable for no-debug builds')
    expedition = Scenario('debug-expedition').key('F1', 40).key('DOWN', 5).key('ENTER', 600)
    expedition.snap('ready').shot('ready').key('ENTER', 20).snap('away').shot('away').key('UP', 10).snap('moved')
    result = expedition.execute()
    ready, away = result['ready'], result['away']
    check(ready.word('TAB') == 6 and ready.word('SELECTED') == 0, 'slot 2 opens with expedition departure selected')
    check(ready.stock('compass') == 1 and ready.stock('l armour') == 1 and ready.stock('rucksack') == 1 and ready.stock('waterskin') == 1, 'slot 2 has navigation and first-expedition passive gear')
    check(ready.stock('cured meat', True) >= 10 and ready.stock('torch', True) >= 1 and ready.stock('bone spear', True) == 1, 'slot 2 has packed food, light and a weapon')
    check(ready.word('BAG_WEIGHT') <= ready.word('CAPACITY'), 'slot 2 backpack fits the native weight limit')
    check(away.word('AWAY') == 1 and away.word('TAB') == 10 and away.word('HP') == away.word('MAX_HP') and away.word('WATER') == away.word('MAX_WATER'), 'Enter starts a supplied expedition at full health and water')
    check(result['moved'].word('POS_Y') == 29 and result['moved'].word('MOVES') == 1, 'expedition accepts a physical movement key')
    world = ready.data[expedition.s['WORLD_MAP']:expedition.s['WORLD_MAP'] + 3721]
    check(world[1860] == 16 and set(range(3, 15)) <= set(world), 'debug map contains the native village and all landmark types')

    ship = Scenario('debug-spaceship').key('F1', 40).key('DOWN', 5).key('DOWN', 5).key('ENTER', 600)
    ship.snap('ready').shot('ready').key('ENTER', 20).snap('flying').shot('flying').key('LEFT', 5).snap('steered')
    result = ship.execute()
    ready, flying = result['ready'], result['flying']
    check(ready.word('TAB') == 7 and ready.word('SELECTED') == 2 and ready.word('FLAGS', CAT['flags'].index('ship') * 2) == 1, 'slot 3 opens with an unlocked spaceship and liftoff selected')
    check(ready.word('HULL') == 50 and ready.word('THRUSTERS') == 5 and ready.stock('alien alloy') >= 100, 'slot 3 has repaired hull, engines and spare alloy')
    check(flying.word('TAB') == 11 and flying.word('FLIGHT_HULL') > 0, 'Enter launches the spaceship')
    check(result['steered'].word('SHIP_X') < flying.word('SHIP_X'), 'flight accepts a physical steering key')

    # Test the real build filtering with both a generated and a manual slot.
    from build import carry_slots
    source = Volume(ROOT / 'build/darkroom.dsk')
    manual = bytearray(contents(source, 'DRSAV2.DAT'))
    manual[80:89] = bytes(9)  # Native manual saves clear reserved header bytes.
    manual_path = ROOT / 'tmp/debug-manual-slot.DAT'
    manual_path.write_bytes(manual)
    source.put('DRSAV2.DAT', manual_path)
    source_path = ROOT / 'tmp/debug-filter-source.dsk'
    source.save(source_path)
    filtered = Volume(ROOT / 'orig/RT11BASE.DSK')
    carry_slots(source_path, filtered, ROOT / 'tmp')
    check(contents(filtered, 'DRSAV2.DAT') == bytes(manual), 'no-debug preserves a manual replacement in a debug slot')
    check(filtered.find('DRSAV3.DAT') is None, 'no-debug does not carry an old generated preset forward')
    for target in ('build', 'run'):
        command = subprocess.check_output(['make', '-n', target, '--', '--no-debug'], cwd=ROOT, text=True)
        check('tools/build.py  --no-debug' in command, f'make {target} forwards --no-debug internally')
    # Removing only the cache must reproduce identical files through native code.
    output = ROOT / 'tmp/debug-reproducible'
    paths = compile_saves(Volume(ROOT / 'build/darkroom.dsk'), output)
    for slot, path in paths.items():
        check(path.read_bytes() == contents(volume, f'DRSAV{slot}.DAT'), f'debug slot {slot} compiles reproducibly')
    from PIL import Image
    for name in ('debug-expedition-ready', 'debug-expedition-away', 'debug-spaceship-ready', 'debug-spaceship-flying'):
        Image.open(ROOT / f'tmp/{name}.bmp').save(ROOT / f'tmp/{name}.png')
    print('baked debug presets: expedition/flight through real keys, filtering, make flags and reproducibility: OK', flush=True)


if __name__ == '__main__':
    count = 0
    def check(ok, message):
        global count
        count += 1
        if not ok:
            raise AssertionError(message)
    verify_debug_saves(check)
    print(f'PASS: {count} debug-save checks')
