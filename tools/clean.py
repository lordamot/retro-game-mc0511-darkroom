#!/usr/bin/env python3
"""Remove generated build files, retaining a disk that contains player saves."""
from pathlib import Path
import shutil
from rt11fs import Volume

def clean(directory):
 directory=Path(directory)
 disk=directory/'darkroom.dsk'
 preserve=disk.exists() and any(Volume(disk).find(f'DRSAV{i}.DAT') for i in range(1,6))
 if not directory.exists():return
 for path in directory.iterdir():
  if preserve and path==disk:continue
  if path.is_dir():shutil.rmtree(path)
  else:path.unlink()
 if preserve:print(f'Kept {disk}: contains player save slots')
 else:directory.rmdir()

if __name__=='__main__':clean(Path(__file__).resolve().parent.parent/'build')
