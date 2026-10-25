"""Symbol-aware scenarios against the actual UKNC CPU; no host game model."""
from pathlib import Path
import json,struct,subprocess,re
import syms
from rt11fs import Volume
ROOT=Path(__file__).resolve().parent.parent
CAT=json.loads((ROOT/'build/catalog.json').read_text())
class Scenario:
 def __init__(self,name,disk=None,save_writes=False,splash=False):
  source=disk or ROOT/'build/darkroom.dsk'
  self.disk_before=Path(source).read_bytes()
  self.save_writes=save_writes
  volume=Volume(source)
  self.protected={e.name:(e.block,e.length,bytes(volume.img[e.block*512:(e.block+e.length)*512])) for e in volume.read_dir()[1] if e.status&0o2000 and e.name!='SWAP.SYS' and not re.fullmatch(r'DRSAV[1-5]\.DAT',e.name)}
  swap=Volume(source).find('SWAP.SYS')
  self.swap_range=(swap.block*512,(swap.block+swap.length)*512) if swap else (0,0)
  (ROOT/'tmp').mkdir(exist_ok=True)
  self.disk=ROOT/'tmp'/f'{name}-run.dsk'
  self.disk.write_bytes(self.disk_before)
  self.name=name;self.s={k:int(v,8) for k,v in syms.table().items()};self.lines=['run 900','press 030','run 30','press 153','run 1100'];self.snaps={}
  if not splash:self.key('ENTER',50)
 def addr(self,label,offset=0):return self.s[label]+offset
 def word(self,label,value,offset=0):
  a=self.addr(label,offset);v=value&65535;self.lines.append(f'pokecpu {a:o} {v&255:o} {v>>8:o}');return self
 def byte(self,label,value,offset=0):self.lines.append(f'pokecpu {self.addr(label,offset):o} {value&255:o}');return self
 def stock(self,name,n,bag=False):return self.word('BAG' if bag else 'STORES',n,CAT['resources'][name])
 def building(self,name,n):return self.word('BUILDINGS',n,CAT['buildings'][name])
 def flag(self,name,n=1):return self.word('FLAGS',n,CAT['flags'].index(name)*2)
 def run(self,n=50):self.lines.append(f'run {n}');return self
 def key(self,key,wait=30):
  from uknc_control import keycode
  self.lines += [f'press {keycode(key)}',f'run {wait}'];return self
 def command(self,text,wait=400):
  for c in text.upper():self.key('SPACE' if c==' ' else c,2)
  return self.key('ENTER',wait)
 def snap(self,name):
  p=ROOT/'tmp'/f'{self.name}-{re.sub(r"[^a-zA-Z0-9_-]", "_", name)}.bin';self.snaps[name]=p;self.lines.append(f'dumpcpu 0 65536 {p}');self.lines.append(f'dump 0 0 65536 {p.with_suffix(".ppu")}');return self
 def shot(self,name):
  p=ROOT/'tmp'/f'{self.name}-{name}'
  self.lines += [f'screenshot {p}.bmp',f'dump 1 100000 23040 {p}.text-plane',f'dump 2 100000 23040 {p}.overlay-plane']
  return self
 def call(self,label,*regs):
  self.lines.append("callcpu "+format(self.s[label],"o")+" "+" ".join(format(v&65535,"o") for v in regs));return self
 def execute(self):
  (ROOT/'tmp').mkdir(exist_ok=True);p=ROOT/'tmp'/f'{self.name}.script';p.write_text('\n'.join(self.lines+['quit'])+'\n')
  r=subprocess.run([str(ROOT/'bin/ukncbtl/uknc-headless'),'--rom',str(ROOT/'bin/ukncbtl/uknc_rom.bin'),'--disk',str(self.disk),'--script',str(p)],capture_output=True,text=True,timeout=90)
  (ROOT/'tmp'/f'{self.name}.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise AssertionError(f'{self.name}: emulator failed; see tmp/{self.name}.log\n'+(r.stdout+r.stderr)[-1500:])
  # RT-11 may swap user memory while servicing monitor requests. This is OS
  # scratch, not a save. Every other byte, including directory/SAV/DAT, is fixed.
  after=self.disk.read_bytes();lo,hi=self.swap_range
  if self.save_writes:
   volume=Volume(self.disk)
   if after[:512]!=self.disk_before[:512]:raise AssertionError(f'{self.name}: boot sector changed')
   for name,(block,length,data) in self.protected.items():
    e=volume.find(name)
    if e is None or (e.block,e.length)!=(block,length) or bytes(volume.img[block*512:(block+length)*512])!=data:raise AssertionError(f'{self.name}: protected file changed: {name}')
   for e in volume.read_dir()[1]:
    if e.status&0o400:raise AssertionError(f'{self.name}: unclosed tentative file')
    if e.status&0o2000 and e.name not in self.protected and e.name!='SWAP.SYS' and not re.fullmatch(r'DRSAV[1-5]\.DAT',e.name):raise AssertionError(f'{self.name}: unexpected file {e.name}')
  elif after[:lo]!=self.disk_before[:lo] or after[hi:]!=self.disk_before[hi:]:
   raise AssertionError(f'{self.name}: disk write outside RT-11 SWAP.SYS')
  return {k:Snapshot(v.read_bytes(),self.s) for k,v in self.snaps.items()}
class Snapshot:
 def __init__(self,data,s):self.data=data;self.s=s
 def word(self,label,offset=0):return struct.unpack_from('<H',self.data,self.s[label]+offset)[0]
 def stock(self,name,bag=False):return self.word('BAG' if bag else 'STORES',CAT['resources'][name])
 def screen(self):
  chars='ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧЪ'
  b=self.data[self.s['SCREEN_BUF']:self.s['SCREEN_BUF']+1920]
  return '\n'.join(''.join(chars[v-64] if 64<=v<96 else chr(v-32) if 96<=v<128 else chr(v) for v in (c&127 for c in b[i:i+80])) for i in range(0,1920,80))
