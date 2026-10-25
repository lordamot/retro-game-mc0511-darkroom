"""Native RT-11 save/load regression scenarios; no host gameplay model."""
import hashlib,struct,subprocess
from pathlib import Path
from test_support import Scenario,ROOT,CAT
from rt11fs import Volume

def file_bytes(path,name):
 v=Volume(path);e=v.find(name)
 return bytes(v.img[e.block*512:(e.block+e.length)*512]) if e else None

def verify_progress(check,disk):
 from PIL import Image
 s=Scenario('save-progress',disk,save_writes=True)
 for mode,key in [('save','F2'),('load','F1')]:
  s.key(key,40).snap(mode+'-before').key('ENTER',60).snap(mode+'-early').shot(mode+'-early')
  s.run(120).snap(mode+'-late').shot(mode+'-late').run(420).snap(mode+'-done').shot(mode+'-done')
 r=s.execute()
 for mode in ['save','load']:
  widths=[]
  for phase in ['early','late']:
   name=mode+'-'+phase;snap=r[name]
   im=Image.open(ROOT/f'tmp/save-progress-{name}.bmp').convert('RGB')
   im.save(ROOT/f'tmp/save-progress-{name}.png')
   border=[(x,y) for x in range(144,496) for y in [156,165]]+[(x,y) for x in [144,495] for y in range(157,165)]
   check(all(im.getpixel(pt)==(255,255,255) for pt in border),f'{name}: progress outline stays centered inside the dialog')
   fill=[im.getpixel((x,160))==(255,255,255) for x in range(152,488)]
   width=sum(fill);widths.append(width)
   check(0<width<336 and fill==[True]*width+[False]*(336-width),f'{name}: progress is a contiguous partial fill during disk I/O')
   check(all(im.crop(box).getbbox() is None for box in [(0,0,640,108),(0,180,640,276),(0,108,128,180),(512,108,640,180)]),f'{name}: centered dialog has a clean black exterior throughout staging')
   outer={(x,y) for x in range(128,512) for y in [108,179]}|{(x,y) for x in [128,511] for y in range(108,180)}
   check(all(im.getpixel(pt)==(255,255,255) for pt in outer),f'{name}: 60-percent-wide frame is centered on both axes')
   check(im.crop((264,120,376,131)).getbbox() is not None,f'{name}: operation label stays visible')
   check(snap.word('SV_MODE')==(1 if mode=='load' else 2),f'{name}: operation is still in progress')
   check(snap.word('SV_ACK')==(1 if mode=='load' else 0),f'{name}: load staging is hidden while progress remains visible')
   check(all(snap.word(k)==r[mode+'-before'].word(k) for k in ['TENTHS','SECONDS','STOKE_CD','LOG_AGE']),f'{name}: gameplay and event-log clocks stay frozen')
  check(widths[1]>widths[0],f'{mode}: real block transfers visibly advance the bar')
  done=r[mode+'-done']
  check(done.word('SV_MODE')==0 and done.word('SV_ERROR')==0 and done.word('SV_HIDE')==0 and done.word('SV_ACK')==0,f'{mode}: successful completion restores normal display')
  im=Image.open(ROOT/f'tmp/save-progress-{mode}-done.bmp').convert('RGB')
  check(im.crop((144,165,496,166)).getbbox() is None,f'{mode}: completion erases the progress outline')
 # Exercise boundary geometry directly while the modal keeps MAIN idle. This
 # also proves the last fill pixels are reachable only at the completion step.
 p=Scenario('save-progress-edges',disk).key('F2',40).call('SV_BUSY').shot('zero')
 for name,step in [('pending',p.s['SV_BLOCKS']),('full',p.s['SV_BLOCKS']+1)]:
  p.word('SV_BLOCK',step).call('SV_PROGRESS').shot(name)
 p.execute()
 for name,expected in [('zero',0),('pending',None),('full',336)]:
  im=Image.open(ROOT/f'tmp/save-progress-edges-{name}.bmp').convert('RGB')
  width=sum(im.getpixel((x,160))==(255,255,255) for x in range(152,488))
  check(width==expected if expected is not None else 0<width<336,f'{name}: progress reserves its final portion for successful commit')

def verify_saves(check):
 from PIL import Image
 # Verification must also work after the player has created release-disk slots.
 # Remove slots only from this disposable test copy, never the release disk.
 blank=Volume(ROOT/'build/darkroom.dsk')
 for slot in range(1,6):
  name=f'DRSAV{slot}.DAT'
  if blank.find(name):blank.rm(name)
 blank_path=ROOT/'tmp/save-empty-base.dsk';blank.save(blank_path)
 s=Scenario('save-slots',blank_path,save_writes=True).key('F2',40).snap('empty').shot('empty').run(150).snap('paused').key('AP2').snap('cancelled').shot('cancelled')
 for slot in range(5):
  s.stock('wood',100+slot).key('F2',40)
  for _ in range(slot):s.key('DOWN',5)
  s.key('ENTER',600).snap('save'+str(slot))
 s.key('F1',40).snap('full').shot('full').key('AP2').key('STOP',300).snap('exit').command('DIR').snap('dir')
 r=s.execute();disk=s.disk
 check(r['empty'].screen().count('ПУСТО')==5,'five missing files are shown as empty slots')
 version=(ROOT/'build/DARKRM.SAV').read_bytes()[s.s['GAME_VERSION']:s.s['GAME_VERSION']+s.s['GAME_VERSION_LENGTH']].decode('ascii')
 check(r['empty'].screen().splitlines()[23].endswith(version),'version remains visible in the save/load window')
 check(r['empty'].word('SECONDS')==r['paused'].word('SECONDS') and r['empty'].word('TENTHS')==r['paused'].word('TENTHS'),'slot window freezes game time')
 check(r['cancelled'].word('SV_MODE')==0,'AP2 cancels without changing location')
 im=Image.open(ROOT/'tmp/save-slots-empty.bmp').convert('RGB')
 border={(x,y) for x in range(128,512) for y in [71,216]}|{(x,y) for y in range(71,217) for x in [128,511]}
 check(all(im.getpixel(pt)==(255,255,255) for pt in border),'slot picker has a solid one-pixel white frame')
 check(all(Image.open(ROOT/'tmp/save-slots-cancelled.bmp').getpixel(pt)==(0,0,0) for pt in border),'cancelling removes the complete modal frame')
 for slot in range(5):
  data=file_bytes(disk,f'DRSAV{slot+1}.DAT')
  check(data is not None and len(data)==s.s['SV_BLOCKS']*512,f'slot {slot+1}: real named RT-11 file has the full expected size')
  wood=struct.unpack_from('<H',data,512+s.s['STORES']-s.s['STATE_START'])[0]
  check(wood==100+slot,f'slot {slot+1}: independent saved inventory')
  check(r['save'+str(slot)].word('SV_MODE')==0 and r['save'+str(slot)].word('SV_ERROR')==0,f'slot {slot+1}: Enter completes the save')
 check(r['full'].screen().count('ЕСТЬ СОХРАНЕНИЕ')==5,'all five files are detected as occupied')
 check(r['exit'].word('PP_READY')==0,'STOP still restores RT-11 after file writes')
 verify_progress(check,disk)
 q=Scenario('save-reboot',disk,save_writes=True).key('F1',40).key('DOWN',5).key('DOWN',5).key('ENTER',600).snap('loaded').stock('wood',999).key('F2',40).key('DOWN',5).key('DOWN',5).key('ENTER',600).snap('overwritten')
 got=q.execute()
 check(got['loaded'].stock('wood')==102,'slot restores its state after a fresh RT-11 boot')
 check(got['overwritten'].word('SV_ERROR')==0,'occupied slot can be overwritten successfully')
 for slot in [1,2,4,5]:check(file_bytes(q.disk,f'DRSAV{slot}.DAT')==file_bytes(disk,f'DRSAV{slot}.DAT'),f'overwriting slot 3 preserves slot {slot}')
 check(file_bytes(q.disk,'DRSAV3.DAT')!=file_bytes(disk,'DRSAV3.DAT'),'overwrite commits a new version of the selected file')
 # Freeze first, then seed a meaningful mid-expedition scene. Save/restore every
 # persistent byte, including less visible timers, PRNG, scene and death rollback.
 scene=next(x['id'] for x in CAT['scenes'] if x['group']=='setpieces' and x['event']=='cave' and x['scene']=='start')
 d=Scenario('save-exact',save_writes=True).key('F2',40).word('AWAY',1).word('POS_X',31).word('POS_Y',29).word('HP',37).word('MAX_HP',50).word('WATER',13).stock('cured meat',7,True).flag('ship').call('SNAPSHOT_WORLD')
 d.call('START_EVENT',scene).word('ENEMY_HP',77).word('ENEMY_CLOCK',43).word('POISON',2).word('POISON_CLOCK',17).word('GAMBLE_TIME',432).word('GAMBLE_AMOUNT',91).word('STOKE_CD',37).word('WEAPON_CD',19).word('WEAPON_SPAN',25).word('ALTITUDE',321).word('SPACE_CLOCK',7).word('DEBRIS',123).byte('WORLD_MAP',7,1861).byte('MAP_SEEN',1,1861).byte('MAP_DONE',1,1861).word('SEED',0o12345).call('SV_NAME').snap('before')
 for plane in [1,2]:d.lines.append(f'dump {plane} 155000 5582 {ROOT}/tmp/save-exact-before-{plane}.plane')
 d.call('SV_SAVE').snap('saved').word('SV_MODE',1).word('HP',1).word('ENEMY_HP',1).word('AWAY',0).word('SEED',1).byte('WORLD_MAP',0,1861).byte('SCENE_BASE',0,4).call('SNAPSHOT_WORLD').call('SV_NAME').call('SV_LOAD').snap('loaded')
 for plane in [1,2]:d.lines.append(f'dump {plane} 155000 5582 {ROOT}/tmp/save-exact-loaded-{plane}.plane')
 d.call('RESTORE_WORLD').snap('rollback').call('DISK_READ',scene).snap('scene-read')
 x=d.execute();a=d.s['TENTHS'];b=d.s['STATE_END']
 skip=set(range(d.s['LOG_SHADE'],d.s['LOG_SHADE']+10))|set(range(d.s['BAR_USED'],d.s['BAR_USED']+24))|set(range(d.s['NOTICE'],d.s['NOTICE']+2))|set(range(d.s['REPEAT_CD'],d.s['REPEAT_CD']+2))
 check(all(x['before'].data[i]==x['loaded'].data[i] for i in range(a,b) if i not in skip),'every persistent state byte restores exactly before game time resumes')
 check(x['loaded'].word('TAB')==x['before'].word('TAB') and x['loaded'].word('SELECTED')==x['before'].word('SELECTED'),'current location and selection restore exactly')
 check(x['loaded'].word('SEED')==x['before'].word('SEED'),'PRNG state restores exactly')
 base=d.s['SCENE_BASE'];check(x['loaded'].data[base:base+1024]==x['before'].data[base:base+1024],'active disk scene restores without replaying entry effects')
 for plane in [1,2]:check((ROOT/f'tmp/save-exact-before-{plane}.plane').read_bytes()==(ROOT/f'tmp/save-exact-loaded-{plane}.plane').read_bytes(),f'expedition rollback plane {plane} restores exactly')
 check(x['rollback'].data[d.s['WORLD_MAP']+1861]!=7,'death rollback still uses the pre-expedition world after loading')
 check(x['scene-read'].data[base:base+1024]==x['before'].data[base:base+1024],'ordinary scene channel still reads correctly after saving/loading')
 check(d.s['SV_DATA_BLOCKS']*256<=17*960,'hidden rows have enough capacity for the entire staged file')
 # Exercise both native staging boundaries without touching the protected center
 # or footer; save-exact above proves every staged state/rollback word survives.
 walk=Scenario('save-stage-map').key('F1',40)
 for name,start in [('center',0o100000+9*960-1),('footer',0o100000+23*960-1)]:
  walk.word('SV_VIDEO',start).call('SV_ADVANCE').snap(name)
 mapped=walk.execute()
 check(mapped['center'].word('SV_VIDEO')==0o100000+15*960 and mapped['footer'].word('SV_VIDEO')==0o100000,'native staging skips the whole centered window and wraps before the footer')
 for mode in ['signature','checksum','truncated']:
  v=Volume(d.disk);entry=v.find('DRSAV1.DAT');start=entry.block*512
  if mode=='signature':v.img[start]^=1
  elif mode=='checksum':v.img[start+512+100]^=1
  else:
   (ROOT/'tmp/truncated-save.bin').write_bytes(v.img[start:start+512]);v.put('DRSAV1.DAT',ROOT/'tmp/truncated-save.bin')
  path=ROOT/f'tmp/save-{mode}.dsk';v.save(path)
  t=Scenario('save-'+mode,path).stock('wood',888).key('F1',40).snap('before').call('SV_NAME').call('SV_LOAD').snap('after')
  z=t.execute()
  check(z['after'].word('SV_MODE')==1 and z['after'].word('SV_ERROR')!=0,f'{mode}: bad save is rejected in the slot window')
  check(all(z['before'].data[i]==z['after'].data[i] for i in range(a,b) if i not in skip),f'{mode}: rejection leaves all persistent game state intact')
 # Exhaust free extents. ENTER must fail without deleting the previous slot.
 v=Volume(disk);i=0
 while True:
  empty=[e.length for e in v.read_dir()[1] if e.status&0o1000 and e.length]
  if not empty:break
  p=ROOT/'tmp/fill-save.bin';p.write_bytes(bytes(max(empty)*512));v.put(f'FILL{i}.DAT',p);i+=1
 full=ROOT/'tmp/save-full.dsk';v.save(full)
 f=Scenario('save-no-space',full,save_writes=True).key('F2',40).key('ENTER',150).snap('error').shot('error')
 result=f.execute()['error']
 check(result.word('SV_MODE')==2 and result.word('SV_ERROR')!=0,'full disk reports a write error and keeps the window open')
 error_image=Image.open(ROOT/'tmp/save-no-space-error.bmp').convert('RGB')
 check(all(error_image.getpixel((x,165))==(0,0,0) for x in [144,495]),'write failure removes progress before returning to the picker')
 for slot in range(1,6):check(file_bytes(f.disk,f'DRSAV{slot}.DAT')==file_bytes(disk,f'DRSAV{slot}.DAT'),f'failed save preserves previous slot {slot}')
 # Exercise the same build helper that carries slots into rebuilt release disks.
 from build import carry_slots
 target=Volume(ROOT/'orig/RT11BASE.DSK');carry_slots(q.disk,target,ROOT/'tmp')
 carried=ROOT/'tmp/save-rebuilt.dsk';target.save(carried)
 for slot in range(1,6):check(file_bytes(carried,f'DRSAV{slot}.DAT')==file_bytes(q.disk,f'DRSAV{slot}.DAT'),f'rebuild preserves slot {slot} byte-for-byte')
 from clean import clean
 scratch=ROOT/'tmp/save-clean-check';scratch.mkdir(exist_ok=True)
 (scratch/'darkroom.dsk').write_bytes(q.disk.read_bytes());(scratch/'generated.bin').write_bytes(b'generated')
 clean(scratch)
 check((scratch/'darkroom.dsk').read_bytes()==q.disk.read_bytes() and not (scratch/'generated.bin').exists(),'make clean retains a disk containing player saves')
 mapping=subprocess.check_output([str(ROOT/'bin/ukncbtl/uknc-play'),'--keymap'],text=True)
 check('F1 010' in mapping and 'F2 011' in mapping,'actual SDL runner maps PC F1/F2 to UKNC K1/K2')
 for name in ['empty','full']:
  Image.open(ROOT/f'tmp/save-slots-{name}.bmp').save(ROOT/f'tmp/save-slots-{name}.png')
 print('five native save files, restart/overwrite, full state and rollback, bad files/full disk, pause/cancel and SDL keys: OK',flush=True)

if __name__=='__main__':
 count=0
 def check(ok,message):
  global count
  count+=1
  if not ok:raise AssertionError(message)
 verify_saves(check)
 print(f'PASS: {count} save checks')
