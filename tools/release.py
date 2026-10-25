#!/usr/bin/env python3
"""Export clean and debug-only release disks without modifying the working disk."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from rt11fs import Volume
from build import ROOT
from debug_saves import compile_saves, install_debug_saves


def export(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    version = re.search(r'GAME_VERSION: .ASCIZ /([^/]+)/',
                        (ROOT / 'src/version.mac').read_text())[1]
    working = ROOT / 'build/darkroom.dsk'
    original = working.read_bytes()
    volume = Volume(working)
    for name in ['DARKRM.SAV', 'DARKRM.DAT']:
        entry = volume.find(name)
        if entry is None or bytes(volume.img[entry.block * 512:(entry.block + entry.length) * 512]) != (ROOT / 'build' / name).read_bytes():
            raise ValueError('Run make build before exporting: ' + name + ' differs')
    for slot in range(1, 6):
        name = f'DRSAV{slot}.DAT'
        if volume.find(name):
            volume.rm(name)
    # Remove deleted payloads too: an empty directory alone can retain private
    # save bytes in free extents. Keep every allocated system/game file intact.
    for entry in volume.read_dir()[1]:
        if entry.status & 0o1000:
            volume.img[entry.block * 512:(entry.block + entry.length) * 512] = bytes(entry.length * 512)
    clean = output / f'darkroom-{version.lower()}.dsk'
    volume.save(clean)
    debug_paths = compile_saves(volume, ROOT / 'build/debug')
    install_debug_saves(volume, debug_paths)
    debug = output / f'darkroom-{version.lower()}-debug.dsk'
    volume.save(debug)
    manifest = {'version': version, 'images': []}
    for path, slots in [(clean, []), (debug, [2, 3])]:
        exported = Volume(path)
        actual = [slot for slot in range(1, 6) if exported.find(f'DRSAV{slot}.DAT')]
        if actual != slots:
            raise AssertionError((path, actual, slots))
        manifest['images'].append({'file': path.name, 'save_slots': slots,
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f'{path}: save slots {slots or "all empty"}')
    if working.read_bytes() != original:
        raise AssertionError('release export modified working disk')
    (output / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return clean, debug


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build')
    export(parser.parse_args().out_dir)
