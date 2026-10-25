#!/usr/bin/env python3
"""Compile JSON presets through native map/capacity/snapshot/save routines.

No host gameplay implementation or copied assembly addresses. The build supplies
a disposable RT-11 volume; only the two resulting slot files are imported back.
"""
import hashlib
import json
import struct
import subprocess
from pathlib import Path

import syms
from rt11fs import Volume

ROOT = Path(__file__).resolve().parent.parent
MARKER = b'DRDEBUG1'
# Deliberate authoring surface for the two home checkpoints. Live scene/combat
# pointers, scheduler state and derived capacities must not be authored as JSON.
STATE_RANGES = {
    'FIRE': (0, 4), 'TEMPERATURE': (0, 4), 'BUILDER': (0, 4),
    'FOREST': (0, 1), 'POP_DELAY': (1, 32767), 'EVENT_DELAY': (1, 32767),
    'SCENE_ID': (65535, 65535), 'THRUSTERS': (1, 30000),
    'TAB': (6, 7), 'SELECTED': (0, 63), 'POPULATION': (0, 80),
    'HP': (1, 85), 'WATER': (1, 110), 'HULL': (0, 30000),
}


def is_debug_save(data):
    # Native SV_SAVE zeros the whole header, removing this marker on a manual save.
    return data[80:88] == MARKER and data[88:89] in (b'\x02', b'\x03')


def contents(volume, name):
    entry = volume.find(name)
    if entry is None:
        raise ValueError(f'native compiler did not create {name}')
    return bytes(volume.img[entry.block * 512:(entry.block + entry.length) * 512])


def state_image(config, preset, symbols, catalog):
    """Resolve declared state only; native routines derive the map and capacities."""
    start, end = symbols['STATE_START'], symbols['STATE_END']
    state = bytearray(end - start)

    def word(label, value, offset=0):
        if type(value) is not int or not 0 <= value <= 65535:
            raise ValueError(f'{label}: expected an unsigned 16-bit integer')
        address = symbols[label] + offset - start
        if not 0 <= address <= len(state) - 2:
            raise ValueError(f'{label}: outside saved state')
        struct.pack_into('<H', state, address, value)

    for key, value in (config['defaults'] | preset['state']).items():
        if key not in STATE_RANGES:
            raise ValueError(f'unknown scalar state field: {key}')
        low, high = STATE_RANGES[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{key}: expected an integer in {low}..{high}')
        word(key, value)
    for section, label, names in [('stores', 'STORES', catalog['resources']),
                                   ('bag', 'BAG', catalog['resources']),
                                   ('buildings', 'BUILDINGS', catalog['buildings'])]:
        for name, value in preset[section].items():
            if name not in names or type(value) is not int or not 0 <= value <= 30000:
                raise ValueError(f'invalid {section} entry: {name}={value}')
            word(label, value, names[name])
            if section in ('stores', 'bag') and value:
                word('SEEN', 1, names[name])
    workers = list(json.loads((ROOT / 'src/res/upstream.json').read_text())['workers'])
    assigned = 0
    for name, count in preset['jobs'].items():
        if name not in workers[1:] or type(count) is not int or count < 0:
            raise ValueError(f'invalid specialist assignment: {name}={count}')
        word('JOBS', count, workers.index(name) * 2)
        assigned += count
    population = struct.unpack_from('<H', state, symbols['POPULATION'] - start)[0]
    if assigned > population:
        raise ValueError('more assigned workers than population')
    word('JOBS', population - assigned)
    upstream = json.loads((ROOT / 'src/res/upstream.json').read_text())
    for recipe in sum(upstream['recipes'].values(), []):
        if recipe['key'] in catalog['buildings'] and preset['buildings'].get(recipe['key'], 0) > recipe['maximum']:
            raise ValueError(f'building exceeds native cap: {recipe["key"]}')
    if population > 4 * preset['buildings'].get('hut', 0):
        raise ValueError('population exceeds four settlers per hut')
    for section, label in [('flags', 'FLAGS'), ('perks', 'PERKS')]:
        for name in preset[section]:
            if name not in catalog[section]:
                raise ValueError(f'unknown {section} entry: {name}')
            word(label, 1, catalog[section].index(name) * 2)
    if type(preset['seed']) is not int or not 1 <= preset['seed'] <= 65535:
        raise ValueError('map seed must be a nonzero 16-bit integer')
    if type(preset['reveal_map']) is not bool:
        raise ValueError('reveal_map must be boolean')
    fields = config['defaults'] | preset['state']
    required = {'TAB', 'SELECTED', 'HP', 'WATER', 'POPULATION', 'SCENE_ID'}
    if not required <= fields.keys():
        raise ValueError(f'missing state fields: {sorted(required - fields.keys())}')
    if fields['TAB'] != {2: 6, 3: 7}[preset['slot']]:
        raise ValueError('slot 2 must open expedition preparation; slot 3 must open the spaceship')
    if preset['slot'] == 2 and not preset['stores'].get('compass', 0):
        raise ValueError('the first expedition needs a compass in home stores')
    if preset['slot'] == 3 and ('ship' not in preset['flags'] or not fields.get('HULL') or fields['SELECTED'] > 2):
        raise ValueError('spaceship preset needs the ship flag, hull and a valid ship action')
    return state


def compile_saves(volume, output, source=ROOT / 'src/res/debug-saves.json'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path(source).read_text())
    if set(config) != {'version', 'defaults', 'slots'}:
        raise ValueError('expected version, defaults and slots at the JSON root')
    if type(config['version']) is not int or config['version'] != 1 or [p['slot'] for p in config['slots']] != [2, 3]:
        raise ValueError('debug presets must define version 1 and slots 2, 3')
    for preset in config['slots']:
        if set(preset) != {'slot', 'description', 'seed', 'state', 'stores', 'bag', 'buildings', 'jobs', 'flags', 'perks', 'reveal_map'}:
            raise ValueError('unexpected or missing preset fields')
        if not isinstance(preset['description'], str):
            raise ValueError('preset description must be a string')
        if type(preset['slot']) is not int:
            raise ValueError('slot must be an integer')
    symbols = {k: int(v, 8) for k, v in syms.table().items()}
    catalog = json.loads((ROOT / 'build/catalog.json').read_text())
    states = [state_image(config, preset, symbols, catalog) for preset in config['slots']]
    # Cache only byte-verified outputs for this exact binary, JSON and compiler.
    fingerprint = hashlib.sha256()
    for path in [ROOT / 'build/DARKRM.SAV', ROOT / 'build/DARKRM.DAT', Path(source), Path(__file__)]:
        fingerprint.update(path.read_bytes())
    identity = fingerprint.hexdigest()
    manifest_path = output / 'manifest.json'
    paths = {slot: output / f'DRSAV{slot}.DAT' for slot in (2, 3)}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('identity') == identity and all(
            path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'].get(path.name)
            for path in paths.values()
        ):
            return paths

    temporary = ROOT / 'tmp/debug-save-compiler'
    temporary.mkdir(parents=True, exist_ok=True)
    disk = temporary / 'compiler.dsk'
    volume.save(disk)
    commands = ['run 900', 'press 030', 'run 30', 'press 153', 'run 1100', 'press 153', 'run 50']

    def poke(address, data):
        for offset in range(0, len(data), 256):
            commands.append(f'pokecpu {address + offset:o} ' +
                            ' '.join(f'{b:o}' for b in data[offset:offset + 256]))

    def word(label, value):
        poke(symbols[label], struct.pack('<H', value))

    def call(label):
        commands.append(f'callcpu {symbols[label]:o}')

    for preset, state in zip(config['slots'], states):
        poke(symbols['STATE_START'], state)
        poke(symbols['SCENE_BASE'], bytes(1024))
        word('SEED', preset['seed'])
        word('SV_MODE', 2)
        word('SV_PHASE', 0)
        word('SV_ERROR', 0)
        call('MAP_INIT')
        if preset['reveal_map']:
            poke(symbols['MAP_SEEN'], bytes([1]) * 3721)
        call('CAPACITIES')
        call('WEIGH')
        call('SNAPSHOT_WORLD')
        word('SV_SLOT', preset['slot'] - 1)
        call('SV_NAME')
        call('SV_SAVE')
        commands.append(f'dumpcpu 0 65536 {temporary}/slot{preset["slot"]}.bin')
    script = temporary / 'compile.script'
    script.write_text('\n'.join(commands + ['quit']) + '\n')
    result = subprocess.run([str(ROOT / 'bin/ukncbtl/uknc-headless'), '--rom',
                             str(ROOT / 'bin/ukncbtl/uknc_rom.bin'), '--disk', str(disk),
                             '--script', str(script)], capture_output=True, text=True, timeout=90)
    (temporary / 'compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'native debug-save compilation failed; see {temporary}/compile.log')
    compiled = Volume(disk)
    for slot, path in paths.items():
        memory = (temporary / f'slot{slot}.bin').read_bytes()
        read = lambda label: struct.unpack_from('<H', memory, symbols[label])[0]
        preset = next(p for p in config['slots'] if p['slot'] == slot)
        weight = sum(count * struct.unpack_from('<H', memory, symbols['WEIGHTS'] + catalog['resources'][name])[0]
                     for name, count in preset['bag'].items())
        if read('SV_MODE') or read('SV_ERROR') or weight > read('CAPACITY') or weight != read('BAG_WEIGHT'):
            raise ValueError(f'slot {slot}: native save failed or backpack is overweight')
        if read('HP') > read('MAX_HP') or read('WATER') > read('MAX_WATER'):
            raise ValueError(f'slot {slot}: health/water exceeds native equipment capacity')
        data = bytearray(contents(compiled, path.name))
        if len(data) != symbols['SV_BLOCKS'] * 512:
            raise ValueError(f'slot {slot}: incorrect native save length')
        data[80:88] = MARKER
        data[88] = slot
        path.write_bytes(data)
    manifest_path.write_text(json.dumps({'identity': identity, 'files': {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()
    }}, indent=2) + '\n')
    print('Compiled native debug saves: slot 2 expedition, slot 3 spaceship')
    return paths


def install_debug_saves(volume, paths):
    for slot, path in paths.items():
        name = f'DRSAV{slot}.DAT'
        if volume.find(name):
            previous = contents(volume, name)
            if not is_debug_save(previous):
                backup = ROOT / 'tmp/player-save-backups' / f'DRSAV{slot}-{hashlib.sha256(previous).hexdigest()}.DAT'
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(previous)
                print(f'Backed up manual debug-slot save to {backup.relative_to(ROOT)}')
        volume.put(name, path)
