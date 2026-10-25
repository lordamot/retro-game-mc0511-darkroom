#!/usr/bin/env python3
"""Build a native bootable UKNC disk, entirely from the local readable sources."""
from pathlib import Path
import argparse, subprocess, sys, json, re, hashlib
from rt11fs import Volume
from savlink import link
ROOT = Path(__file__).resolve().parent.parent

def run(*args):
    subprocess.run([str(a) for a in args],cwd=ROOT,check=True)

def carry_slots(source,volume,staging):
    """Keep manual saves; generated debug slots are refreshed or omitted."""
    from debug_saves import is_debug_save
    if not Path(source).exists():return
    previous=Volume(source)
    for slot in range(1,6):
        name=f'DRSAV{slot}.DAT';entry=previous.find(name)
        if entry:
            data=bytes(previous.img[entry.block*512:(entry.block+entry.length)*512])
            if is_debug_save(data):continue
            path=Path(staging)/name
            path.write_bytes(data)
            volume.put(name,path)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-debug',action='store_true',help='omit generated saves in slots 2 and 3; retain manual saves')
    args=parser.parse_args(argv)
    (ROOT/'build').mkdir(exist_ok=True)
    run(sys.executable,'tools/generate.py')
    run(sys.executable,'tools/font_gen.py','src/res/font8x11.txt','--out','build/font.mac','--force')
    modules = [p.split('#')[0].strip() for p in (ROOT/'src/darkroom.list').read_text().splitlines()]
    identity=hashlib.sha256()
    for p in modules:
        if p:identity.update((ROOT/p).read_bytes())
    identity.update((ROOT/'build/scenes.bin').read_bytes())
    digest=identity.digest()
    (ROOT/'build/save-id.mac').write_text(' .BYTE '+','.join(str(v)+'.' for v in digest[:16])+'\n .BYTE '+','.join(str(v)+'.' for v in digest[16:])+'\n')
    from branches import Branches
    branches=Branches([(p,(ROOT/p).read_text()) for p in modules if p])
    for attempt in range(20):
        (ROOT/'build/darkroom.mac').write_text(branches.render())
        run('bin/macro11/macro11','-m','orig/loader/source/SYSMAC.SML','-yus','-ysl','64','-o','build/darkroom.obj','-l','build/darkroom.lst','build/darkroom.mac')
        if not branches.shrink((ROOT/'build/darkroom.lst').read_text()):break
    else:raise SystemExit('branch relaxation did not converge')
    print(f'{len(branches.short)} short branches after {attempt+1} assembler passes')
    link(str(ROOT/'build/darkroom.obj'),str(ROOT/'build/DARKRM.SAV'),stack=0o1000)
    raw=(ROOT/'build/DARKRM.SAV').read_bytes()
    scene_base=int(re.search(r'SCENE_BASE = ([0-7]+)',(ROOT/'src/defs.mac').read_text())[1],8)
    if len(raw)>scene_base:raise SystemExit(f'resident exceeds scene window: {len(raw)}')
    bank=(ROOT/'build/scenes.bin').read_bytes()
    (ROOT/'build/DARKRM.DAT').write_bytes(bank)
    volume=Volume(ROOT/'orig/RT11BASE.DSK')
    volume.put('DARKRM.SAV',ROOT/'build/DARKRM.SAV')
    volume.put('DARKRM.DAT',ROOT/'build/DARKRM.DAT')
    # Enable screen-terminal editing in the generated copy, retaining QUIET
    # and the supplied USR/EXIT settings. Never edit the original base disk.
    e=volume.find('STARTS.COM')
    startup=bytes(volume.img[e.block*512:(e.block+e.length)*512]).split(b'\0')[0].rstrip(b'\r\n')
    startup=startup.replace(b'SET TT NOSCOPE',b'SET TT SCOPE')
    startup+=b'\r\nR DARKRM\r\n'
    (ROOT/'build/STARTS.COM').write_bytes(startup)
    volume.put('STARTS.COM',ROOT/'build/STARTS.COM')
    debug_paths={}
    if not args.no_debug:
        from debug_saves import compile_saves
        debug_paths=compile_saves(volume,ROOT/'build/debug')
    carry_slots(ROOT/'build/darkroom.dsk',volume,ROOT/'build')
    if debug_paths:
        from debug_saves import install_debug_saves
        install_debug_saves(volume,debug_paths)
    volume.save(ROOT/'build/darkroom.new.dsk')
    (ROOT/'build/darkroom.new.dsk').replace(ROOT/'build/darkroom.dsk')
    print(f'Built RT-11 build/darkroom.dsk: DARKRM.SAV {len(raw)} bytes, DARKRM.DAT {len(bank)} bytes')
if __name__=='__main__':main()
