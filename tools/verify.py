#!/usr/bin/env python3
"""Verify the real PDP-11 game in UKNCBTL, plus source/disk invariants.

Keyboard smoke tests use no host game implementation. Focused scenarios seed
RAM, invoke native routines via the headless runner's callcpu command, and
assert independent expected rules. Reports and screenshots stay under tmp/.
"""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from test_support import Scenario,CAT,ROOT
from rt11fs import Volume
checks=0

def check(ok,msg):
 global checks
 checks+=1
 if not ok:raise AssertionError(msg)

def plane_image(name,plane):
 from PIL import Image
 # UKNC pixels are least-significant bit first; Pillow uses MSB first.
 reverse=bytes(int(f'{n:08b}'[::-1],2) for n in range(256))
 raw=(ROOT/f'tmp/{name}.{plane}-plane').read_bytes().translate(reverse)
 return Image.frombytes('1',(640,288),raw).convert('L')

def without_overlay(name):
 from PIL import Image
 im=Image.open(ROOT/f'tmp/{name}.bmp').convert('RGB')
 im.paste((0,0,0),(0,0),plane_image(name,'overlay'))
 return im

def scene(group,event,name='start'):
 return next(s['id'] for s in CAT['scenes'] if s['group']==group and s['event']==event and s['scene']==name)

def static():
 disk=(ROOT/'build/darkroom.dsk').read_bytes()
 check(len(disk)==819200,'raw 80x2x10x512 disk geometry')
 volume=Volume(ROOT/'build/darkroom.dsk')
 check(disk[:512]==(ROOT/'orig/RT11BASE.DSK').read_bytes()[:512],'original RT-11 boot sector retained')
 sav=volume.find('DARKRM.SAV');data=volume.find('DARKRM.DAT')
 check(sav is not None and data is not None,'normal RT-11 SAV and DAT files')
 check(bytes(volume.img[sav.block*512:(sav.block+sav.length)*512])==(ROOT/'build/DARKRM.SAV').read_bytes(),'directory SAV matches linked file')
 bank=bytes(volume.img[data.block*512:(data.block+data.length)*512])
 check(bank==(ROOT/'build/DARKRM.DAT').read_bytes(),'directory DAT matches generated scenes')
 check(json.loads((ROOT/'build/missing-translations.json').read_text())==[],'all content is translated')
 check(sum(s['group']!='native' for s in CAT['scenes'])==273,'all 273 upstream scenes')
 check(sum(s['group']=='native' for s in CAT['scenes'])==6,'three native defeat reasons, splash and two endings')
 check(b'\x00' in disk,'disk data exists')
 s=Scenario('layout')
 base=s.s['SCENE_BASE']
 check(s.s['RESIDENT_END']<base,'resident below scene window')
 check(s.s['SCENE_LIMIT']<s.s['STACK_TOP']<=0o130000,'scene and stacks stay below RT-11')
 check(s.s['MAP_DONE']+3721-s.s['WORLD_MAP']==11163,'expedition snapshot covers exactly the map arrays')
 # Every pointer and every probabilistic transition fits the native format.
 for sc in CAT['scenes']:
  b=bank[sc['block']*512:(sc['block']+sc['sectors'])*512]
  h=struct.unpack_from('<16H',b)
  check(all(base<=h[i]<base+sc['bytes'] for i in [0,1,6,7,8]),f'scene {sc["id"]} pointers')
  bp=h[8]-base;n=struct.unpack_from('<H',b,bp)[0]
  for i in range(n):
   choice=struct.unpack_from('<6H',b,bp+2+i*12)
   off=choice[3]-base;count=struct.unpack_from('<H',b,off)[0]
   routes=[struct.unpack_from('<HH',b,off+2+j*4) for j in range(count)]
   check(routes[-1][0]==100 and all(t==65535 or t<len(CAT['scenes']) for _,t in routes),f'scene {sc["id"]} branch targets')
 print('resource graph and memory layout: OK',flush=True)
 return hashlib.sha256(disk).hexdigest()

def keyboard():
 s=Scenario('opening').snap('start').shot('start').key('ENTER').run(4100).snap('builder').key('2').key('ENTER').snap('gather').key('3').snap('build').shot('build')
 r=s.execute()
 check(r['start'].word('FIRE')==0,'starts with dead fire')
 check('РАЗЖЕЧЬ ОГОНЬ' in r['start'].screen(),'Russian startup screen')
 check('КОРАБЛЬ' not in r['start'].screen(),'late tabs are hidden at start')
 check(r['builder'].word('BUILDER')==4 and r['builder'].word('FOREST')==1,'natural builder/forest progression')
 check(r['gather'].word('TAB')==1 and r['gather'].stock('wood')>=10,'physical key gathers wood')
 check(r['build'].word('MENU_COUNT')>=1,'first building becomes visible')
 from PIL import Image
 im=Image.open(ROOT/'tmp/opening-start.bmp').convert('RGB')
 colors=set(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
 check(colors <= {(0,0,0),(255,255,255)},f'white text on black: {colors}')
 # Compare the actual raster to the independent firmware reference, including
 # Cyrillic remapping, glyph stride and the blank twelfth scanline of each cell.
 rom=(ROOT/'bin/ukncbtl/uknc_rom.bin').read_bytes()
 chars=r['start'].data[s.s['SCREEN_BUF']:s.s['SCREEN_BUF']+1920]
 expected=Image.new('RGB',(640,288))
 pixels=expected.load()
 for cell,code in enumerate(chars):
  firmware_code=code+160 if 64<=code<96 else code-32 if code>=96 else code
  offset=0o20170+(firmware_code-32)*11
  for y,bits in enumerate(rom[offset:offset+11]):
   for x in range(8):
    if bits & (1<<x):pixels[cell%80*8+x,cell//80*12+y]=(255,255,255)
 check(plane_image('opening-start','text').tobytes()==expected.convert('L').tobytes(),'rendered text matches UKNC firmware 8x11 glyphs')
 decorated=expected.copy();decorated.paste((255,255,255),(0,0),plane_image('opening-start','overlay'))
 check(im.tobytes()==decorated.tobytes(),'white pixel decorations compose correctly with firmware text')
 version=(ROOT/'build/DARKRM.SAV').read_bytes()[s.s['GAME_VERSION']:s.s['GAME_VERSION']+s.s['GAME_VERSION_LENGTH']].decode('ascii')
 check(r['start'].screen().splitlines()[23].endswith(version),'source version appears exactly, right-aligned on the bottom row')
 im.save(ROOT/'tmp/start.png')
 print('boot, Cyrillic, palette, keyboard, opening progression: OK',flush=True)

def decorations():
 from PIL import Image
 import re
 s=Scenario('decorations').snap('start').shot('start').run(5).snap('phase').shot('phase')
 s.word('BUILDER',4).word('FOREST',1).word('TEMPERATURE',3).stock('wood',1000).key('3').snap('first').shot('first')
 s.key('DOWN').snap('second').shot('second').key('ENTER').snap('crafted').shot('crafted')
 for resource in CAT['resources']:s.stock(resource,1000)
 s.building('workshop',1).word('POPULATION',5).stock('compass',1).flag('ship').run(40).key('4').word('SELECTED',9).word('DIRTY',1).run(40).snap('page').shot('page')
 s.key('0').snap('help').shot('help').key('SPACE').snap('stock').shot('stock')
 s.call('START_EVENT',scene('setpieces','cave')).run(40).snap('event').shot('event')
 r=s.execute()
 check('>' not in r['start'].screen(),'text cursor is removed')
 check(plane_image('decorations-start','overlay').crop((8,72,16,84)).tobytes()!=plane_image('decorations-phase','overlay').crop((8,72,16,84)).tobytes(),'single-cell focus dots move while idle')
 check(Image.open(ROOT/'tmp/decorations-start.bmp').crop((0,11,640,48)).tobytes()==Image.open(ROOT/'tmp/decorations-phase.bmp').crop((0,11,640,48)).tobytes(),'location frames remain static while idle')
 check(plane_image('decorations-start','text').tobytes()==plane_image('decorations-phase','text').tobytes(),'animation leaves glyph pixels unchanged')
 for name in ['start','phase','first','second','crafted','page','help','event']:
  q=r[name];mask=plane_image('decorations-'+name,'overlay');row=q.word('FOCUS_ROW')
  check(q.word('FOCUS_COUNT') in (0,6) and q.word('FOCUS_LENGTH')>0,f'{name}: selected Enter action has a compact spinner')
  # Gray glyphs also occupy plane 2. The cursor owns only column 1 below headers.
  points=[(x,y) for y in range(60,288) for x in range(8,16) if mask.getpixel((x,y))]
  check(0<len(points)<=6 and all(row*12<=y<row*12+11 for x,y in points),f'{name}: no stale spinner pixels outside the selected character cell')
  text=plane_image('decorations-'+name,'text')
  check(not any(text.getpixel(p) for p in points),f'{name}: spinner never touches glyphs')
 check(r['first'].word('FOCUS_ROW')+1==r['second'].word('FOCUS_ROW'),'arrow selection moves the spinner to the next action')
 check(r['page'].word('MENU_START')==8 and r['page'].word('FOCUS_ROW')==7,'spinner follows selection onto the next page')
 check(r['crafted'].word('BUILDINGS',CAT['buildings']['cart'])==1,'Enter activates the highlighted second building')
 check(r['stock'].word('FOCUS_COUNT')==0 and plane_image('decorations-stock','overlay').crop((0,60,640,288)).getbbox() is None,'read-only stock list has no Enter-action spinner')
 for name in ['start','first','page','help','stock','event']:
  q=r[name];lines=q.screen().splitlines();mask=plane_image('decorations-'+name,'overlay');im=Image.open(ROOT/f'tmp/decorations-{name}.bmp').convert('RGB')
  expected=set()
  if name!='event':
   for row in [1,2]:
    for match in re.finditer(r'[1-9] [^\d]+?(?=  |$)',lines[row].rstrip()):
     left=match.start()*8-1;right=match.end()*8;top=row*12;bottom=top+11
     frame={(x,y) for x in range(left,right+1) for y in [top,bottom]}|{(x,y) for y in range(top,bottom+1) for x in [left,right]}
     expected.update(frame)
     color=(255,255,255) if int(match[0][0])-1==q.word('TAB') else (128,128,128)
     check(all(im.getpixel(pt)==color for pt in frame),f'{name}: tab {match[0][0]} has a solid one-pixel frame with correct active/inactive shade')
  actual={(x,y) for y in range(12,36) for x in range(640) if mask.getpixel((x,y))}
  check(actual==expected,f'{name}: frames match usable numbered tabs exactly; no stale frames or Help frame')
 print('single-cell spinner, static white/gray location frames, cleanup and physical keyboard actions: OK',flush=True)

def square_cursor_layout():
 from PIL import Image
 s=Scenario('square-cursor').word('FIRE',4).word('TEMPERATURE',4).key('1').snap('layout').shot('layout')
 for phase in range(20):s.word('FOCUS_PHASE',phase*4).call('FOCUS_DRAW').shot(str(phase))
 r=s.execute();lines=r['layout'].screen().splitlines()
 check(lines[0][72:]=='0 ПОМОЩЬ' and 'ВЫБОР:' in lines[0][:44] and 'К1 ЗАГРУЗИТЬ' in lines[0][44:72] and 'К2 СОХРАНИТЬ' in lines[0][44:72],'Help sits at the top right after the selection count')
 check(lines[3].strip()=='ОГОНЬ ПОЛЫХАЕТ' and lines[4].strip().startswith('В КОМНАТЕ ЖАРКО'),'fire and temperature move up one row')
 check(not lines[5].strip() and 'ПОДБРОСИТЬ ДРОВА' in lines[6],'an empty row separates room status from selectable options')
 boundary={(x,y) for y in range(2,8) for x in range(1,7) if x in (1,6) or y in (2,7)}
 phases=[];frames=[];reference=plane_image('square-cursor-layout','text').tobytes()
 for phase in range(20):
  mask=plane_image('square-cursor-'+str(phase),'overlay').crop((8,72,16,84))
  points={(x,y) for y in range(12) for x in range(8) if mask.getpixel((x,y))}
  check(len(points)==6 and points<=boundary,f'square phase {phase}: exactly six pixels on the square perimeter')
  reached={next(iter(points))}
  while True:
   grown=reached|{p for p in points if any(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for q in reached)}
   if grown==reached:break
   reached=grown
  check(reached==points,f'square phase {phase}: snake remains connected around corners')
  check(plane_image('square-cursor-'+str(phase),'text').tobytes()==reference,f'square phase {phase}: text plane stays intact')
  phases.append(points);frames.append(Image.open(ROOT/f'tmp/square-cursor-{phase}.bmp').convert('RGB'))
 check(len({frozenset(p) for p in phases})==20,'snake visits every square-perimeter position')
 check(all(len(phases[i]^phases[(i+1)%20])==2 for i in range(20)),'each animation step moves one pixel, including wraparound')
 frames[0].save(ROOT/'tmp/square-cursor.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
 frames[0].save(ROOT/'tmp/square-cursor.png')
 sheet=Image.new('RGB',(400,480))
 for i,frame in enumerate(frames):sheet.paste(frame.crop((8,72,16,84)).resize((80,120),Image.Resampling.NEAREST),((i%5)*80,(i//5)*120))
 sheet.save(ROOT/'tmp/square-cursor-phases.png')
 # Later locations must not collide with the raised room status. Check the
 # font's actual first scanline, which the compact frames use for their top edge.
 s=Scenario('compact-header').word('FIRE',4).word('TEMPERATURE',4).word('BUILDER',4).word('FOREST',1).word('POPULATION',5).building('workshop',1).building('trading post',1).stock('compass',1).flag('ship').flag('executioner').key('1').snap('all').shot('all').key('0').snap('help').shot('help')
 q=s.execute();lines=q['all'].screen().splitlines();rom=(ROOT/'bin/ukncbtl/uknc_rom.bin').read_bytes();a=s.s['SCREEN_BUF']
 check('6 ЖИТЕЛИ' in lines[2] and '9 СИНТЕЗ' in lines[2] and lines[3].strip()=='ОГОНЬ ПОЛЫХАЕТ','all unlocked tabs fit above room status')
 for row in [1,2]:
  chars=q['all'].data[a+row*80:a+(row+1)*80]
  check(all(rom[0o20170+((code if code<64 else code+160)-32)*11]==0 for code in chars),'compact frame top edge occupies an unused font scanline')
 check(q['help'].word('TAB')==9 and q['help'].screen().splitlines()[0][72:]=='0 ПОМОЩЬ','relocated Help remains keyboard accessible')
 Image.open(ROOT/'tmp/compact-header-all.bmp').save(ROOT/'tmp/compact-header.png')
 print('top-right Help, compact tabs, separated status and six-pixel square snake: OK',flush=True)

def disabled_recipes():
 from PIL import Image
 s=Scenario('disabled-recipes').word('BUILDER',4).word('FOREST',1).word('TEMPERATURE',3).stock('wood',1000).key('3').snap('ready').shot('ready')
 # Keep the capped-purchase comparison clear of the independent income tick.
 s.key('DOWN').key('ENTER').snap('built').shot('built').word('INCOME_TIME',0).key('ENTER').snap('retry')
 s.stock('wood',0).run(40).snap('poor').shot('poor').stock('wood',1000).run(40).snap('restored').shot('restored')
 s.word('TEMPERATURE',1).word('TEMP_TIME',0).word('DIRTY',1).run(30).snap('cold').shot('cold')
 s.word('TEMPERATURE',3).building('trap',10).stock('wood',1000).run(40).snap('max').shot('max')
 s.key('2').snap('forest').shot('forest').key('3').snap('back').shot('back')
 r=s.execute()
 for name,shades in [('ready',[255,255,255]),('built',[255,128,255]),('poor',[128,128,128]),('restored',[255,128,255]),('cold',[128,128,128]),('max',[128,128,255]),('back',[128,128,255])]:
  im=Image.open(ROOT/f'tmp/disabled-recipes-{name}.bmp').convert('RGB');text=plane_image('disabled-recipes-'+name,'text')
  for row,shade in zip(range(6,9),shades):
   box=(16,row*12,440,row*12+11);glyphs=text.crop(box);pixels=im.crop(box)
   check(glyphs.getbbox() is not None and all(pixels.getpixel((x,y))==((shade,)*3 if glyphs.getpixel((x,y)) else (0,0,0)) for y in range(11) for x in range(424)),f'{name}: recipe row {row} has correct gray/white intact glyphs and count')
 check(r['retry'].stock('wood')==r['built'].stock('wood') and r['retry'].word('BUILDINGS',CAT['buildings']['cart'])==1,'gray capped cart remains visible and cannot be built twice')
 check(plane_image('disabled-recipes-ready','text').crop((16,72,370,83)).tobytes()==plane_image('disabled-recipes-poor','text').crop((16,72,370,83)).tobytes(),'shading preserves the complete firmware glyph mask')
 check(plane_image('disabled-recipes-forest','overlay').crop((16,72,370,108)).getbbox() is None,'switching away clears all disabled-label overlays')
 print('unaffordable/capped/cold recipe shading, recovery and page cleanup: OK',flush=True)

def location_and_fire():
 s=Scenario('location-fire').snap('dark').key('ENTER').snap('lit').shot('lit').run(250).key('ENTER').snap('roaring').shot('roaring')
 s.word('FOREST',1).word('BUILDER',4).key('2')
 stages=[(0,'ТИХИЙ ЛЕС'),(1,'ОДИНОКАЯ ХИЖИНА'),(2,'НЕБОЛЬШАЯ ДЕРЕВНЯ'),(4,'НЕБОЛЬШАЯ ДЕРЕВНЯ'),(5,'СКРОМНАЯ ДЕРЕВНЯ'),(8,'СКРОМНАЯ ДЕРЕВНЯ'),(9,'БОЛЬШАЯ ДЕРЕВНЯ'),(14,'БОЛЬШАЯ ДЕРЕВНЯ'),(15,'ОГРОМНАЯ ДЕРЕВНЯ')]
 for huts,title in stages:s.building('hut',huts).word('DIRTY',1).run(30).snap('huts'+str(huts))
 s.shot('village').key('1').snap('room').shot('room').word('BUILDER',0).word('TEMP_TIME',0).word('FIRE',4).word('FIRE_AGE',299).call('VILLAGE_SECOND').run(30).snap('cooled')
 s.word('FIRE',1).word('TEMPERATURE',2).word('TEMP_TIME',29).call('VILLAGE_SECOND').run(30).snap('cold')
 s.word('FIRE',0).word('DIRTY',1).run(30).snap('out')
 r=s.execute()
 check(r['dark'].screen().splitlines()[0].strip().startswith('ТЕМНАЯ КОМНАТА'),'dead fire starts with the dark room title')
 for name,desc in [('lit','ОГОНЬ ГОРИТ'),('roaring','ОГОНЬ ПОЛЫХАЕТ'),('cooled','ОГОНЬ ГОРИТ'),('cold','ОГОНЬ ТЛЕЕТ'),('out','ОГОНЬ ПОГАС')]:
  check(desc in r[name].screen().splitlines()[3],f'{name}: live fire description follows its native state')
 # SCREEN_BUF can be sampled midway through composition at a second boundary.
 # Inspect the committed notification, independently of the redraw phase.
 def newest_is(snapshot,label):
  message=snapshot.data[s.s['LOG_TEXT']:s.s['LOG_TEXT']+80].split(b'\0')[0]
  expected=snapshot.data[s.s[label]:].split(b'\0')[0]
  return message==expected
 check(newest_is(r['roaring'],'S_FIRE4'),'actual stoking publishes the current fire description immediately')
 check(newest_is(r['cooled'],'S_FIRE3'),'cooling publishes its changed fire description')
 check('В КОМНАТЕ ХОЛОДНО' in r['cold'].screen().splitlines()[4] and any('В КОМНАТЕ ХОЛОДНО' in line for line in r['cold'].screen().splitlines()[18:23]),'temperature changes update both status and event log')
 for huts,title in stages:
  check(r['huts'+str(huts)].screen().splitlines()[0].strip().startswith(title),f'{huts} huts: original outside title threshold')
  check(('2 ДЕРЕВНЯ' if huts else '2 ЛЕС') in r['huts'+str(huts)].screen().splitlines()[1],f'{huts} huts: outside shortcut matches the settlement')
 check(r['room'].screen().splitlines()[0].strip().startswith('ОЧАГ'),'returning indoors restores the lit-room title ОЧАГ')
 print('room/fire/temperature descriptions, notifications and original village title thresholds: OK',flush=True)

def worker_controls():
 s=Scenario('worker-controls').word('POPULATION',2).building('lodge',1).key('6').snap('start').key('RIGHT',31).snap('one').shot('one')
 s.key('ENTER').snap('enter').key('RIGHT').key('RIGHT').snap('full').key('LEFT').snap('less').key('LEFT').key('LEFT').snap('zero').key('UP').snap('gatherers')
 r=s.execute()
 check('< 0 >' in r['start'].screen().splitlines()[7] and '<' not in r['start'].screen().splitlines()[6],'editable workers show arrow brackets; automatic gatherers remain a plain count')
 check(r['one'].word('JOBS',2)==1 and '< 1 >' in r['one'].screen().splitlines()[7],'physical Right assigns one worker and updates the bracketed count')
 check(r['enter'].word('JOBS',2)==1,'Enter no longer changes worker assignments')
 check(r['full'].word('JOBS',2)==2 and r['full'].word('SELECTED')==0,'Right stops at available population without paging')
 check(r['less'].word('JOBS',2)==1 and r['zero'].word('JOBS',2)==0,'Left removes workers and stops at zero')
 check(r['gatherers'].word('JOBS')==2 and r['gatherers'].word('JOBS',2)==0,'unassigned gatherer count stays automatic')
 check(r['start'].word('MENU_COUNT')==2 and r['start'].word('MENU',4)==2 and r['gatherers'].word('FOCUS_ROW')==7,'gatherers are absent from selectable actions and cursor stays on a speciality')
 check(r['one'].word('JOBS')==1 and r['full'].word('JOBS')==0 and r['less'].word('JOBS')==1,'speciality assignments transfer people to and from gatherers')
 print('worker arrow controls, bracketed counts, population bounds and inert Enter: OK',flush=True)

def packing_arrows():
 from PIL import Image
 s=Scenario('packing-arrows').stock('compass',1).stock('rucksack',1).stock('cured meat',3).stock('torch',2).key('7',31)
 s.key('LEFT',10).key('RIGHT',10).snap('departure').key('DOWN',31).snap('zero').shot('zero')
 s.key('RIGHT',31).snap('one').shot('one').key('ENTER',10).key('SPACE',10).snap('old-keys')
 s.key('LEFT',31).snap('removed').key('LEFT',10).snap('floor')
 for _ in range(4):s.key('RIGHT',10)
 s.snap('empty-store').key('LEFT',10).snap('returned')
 s.stock('cured meat',20).stock('cured meat',20,True).word('DIRTY',1).run(31).key('RIGHT',31).snap('full').shot('full')
 s.key('LEFT',10).key('RIGHT',10).snap('refilled')
 s.stock('cured meat',20).stock('cured meat',0,True).word('DIRTY',1).run(31)
 s.lines+=['keydown 133','run 30','keyup 133','run 10'];s.snap('held-right')
 s.lines+=['keydown 116','run 90','keyup 116','run 10'];s.snap('held-left').shot('held-left')
 s.key('UP',10).key('ENTER',31).snap('departed')
 r=s.execute()
 check(r['departure'].word('AWAY')==0 and r['departure'].word('SELECTED')==0,'Left/Right on departure neither launches nor jumps the list')
 check(r['zero'].word('SELECTED')==1 and '< 0 >' in r['zero'].screen().splitlines()[7],'packing row shows an editable carried count, including zero')
 check(r['one'].stock('cured meat',True)==1 and r['one'].stock('cured meat')==2 and r['one'].word('SELECTED')==1,'Right transfers one item into the bag without changing selection')
 check('< 1 >' in r['one'].screen().splitlines()[7] and 'ВЕС: 10/200' in r['one'].screen().splitlines()[4],'packing displays bracketed quantity and plain readable weight totals')
 check('ВЛЕВО: ВЫЛОЖИТЬ' in r['one'].screen().splitlines()[23] and 'ВПРАВО: ВЗЯТЬ' in r['one'].screen().splitlines()[23],'packing footer describes the arrow controls')
 check(r['old-keys'].stock('cured meat',True)==1 and r['old-keys'].stock('cured meat')==2 and r['old-keys'].word('AWAY')==0,'Enter and Space on packing items no longer transfer or depart')
 for name in ['removed','floor']:
  check(r[name].stock('cured meat',True)==0 and r[name].stock('cured meat')==3,f'{name}: Left returns items and cannot go below zero')
 check(r['empty-store'].stock('cured meat',True)==3 and r['empty-store'].stock('cured meat')==0 and r['empty-store'].word('SELECTED')==1,'Right stops at empty home stock and keeps the carried item selectable')
 check(r['returned'].stock('cured meat',True)==2 and r['returned'].stock('cured meat')==1,'Left replenishes an exhausted home stock')
 for name in ['full','refilled']:
  check(r[name].stock('cured meat',True)==20 and r[name].stock('cured meat')==20 and r[name].word('BAG_WEIGHT')==200,f'{name}: arrows respect carrying capacity without losing stock')
 check(1<r['held-right'].stock('cured meat',True)<=20 and r['held-right'].stock('cured meat',True)+r['held-right'].stock('cured meat')==20 and r['held-right'].word('SELECTED')==1,'holding Right repeats quantity adjustment without scrolling')
 check(r['held-left'].stock('cured meat',True)==0 and r['held-left'].stock('cured meat')==20 and r['held-left'].word('SELECTED')==1,'holding Left stops at zero and preserves total inventory')
 check(r['departed'].word('AWAY')==1 and r['departed'].word('TAB')==10,'Enter still activates the selected departure action')
 # Fill enough rows to exercise real pagination and other lists, not just a
 # three-row fixture where the previous ten-row jump could wrap back to zero.
 p=Scenario('list-arrows').word('BUILDER',4).word('TEMPERATURE',3).building('workshop',1)
 for name in CAT['resources']:p.stock(name,10)
 p.key('7',31)
 for _ in range(9):p.key('DOWN',5)
 p.run(31).snap('page').shot('page').key('RIGHT',31).snap('added').key('LEFT',31).snap('restored')
 p.stock('wood',1000).key('3',31).key('DOWN',10).snap('build').key('RIGHT',10).key('LEFT',10).snap('build-still')
 p.key('0',31).shot('help').key('SPACE',31)
 for _ in range(9):p.key('DOWN',5)
 p.run(31).snap('stock').key('RIGHT',10).snap('stock-right').key('LEFT',10).snap('stock-left')
 p.key('7',31).key('DOWN',10).key('7',31).snap('shortcut').key('LEFT',10).snap('move')
 q=p.execute()
 check(q['page'].word('SELECTED')==9 and q['page'].word('MENU_START')==8,'Up/Down reaches subsequent packing pages')
 offset=q['page'].word('MENU',9*8+4);resource=next(k for k,v in CAT['resources'].items() if v==offset)
 check(q['added'].stock(resource,True)==1 and q['added'].stock(resource)==9 and q['added'].word('SELECTED')==9,'Right adjusts the selected item on later packing pages')
 check(q['restored'].stock(resource,True)==0 and q['restored'].stock(resource)==10 and q['restored'].word('SELECTED')==9,'Left restores the selected item on later packing pages')
 check(q['build'].word('SELECTED')==q['build-still'].word('SELECTED')==1,'build list no longer uses horizontal fast navigation')
 check(all(q[name].word('SELECTED')==9 for name in ['stock','stock-right','stock-left']),'read-only stock list no longer uses horizontal fast navigation')
 check(q['shortcut'].word('AWAY')==1 and q['shortcut'].word('TAB')==10,'7 still starts an expedition from an item row')
 check(q['move'].word('POS_X')==q['shortcut'].word('POS_X')-1,'Left retains its movement meaning on the expedition map')
 for name in ['zero','one','full','held-left']:
  Image.open(ROOT/f'tmp/packing-arrows-{name}.bmp').save(ROOT/f'tmp/packing-arrows-{name}.png')
 for name in ['page','help']:
  Image.open(ROOT/f'tmp/list-arrows-{name}.bmp').save(ROOT/f'tmp/list-arrows-{name}.png')
 print('packing Left/Right, bracketed quantities, stock/capacity limits, held arrows, Up/Down pages and departure: OK',flush=True)

def help_pause():
 s=Scenario('help-pause').stock('wood',321).word('FIRE',4).word('STOKE_CD',123).key('0',10).snap('open').shot('open').run(250).snap('paused').key('1',10).run(30).snap('resumed').shot('resumed')
 r=s.execute()
 check(r['open'].word('TAB')==9 and not r['open'].screen().splitlines()[4][56:].strip(),'Help clears the resource sidebar')
 for name in ['TENTHS','SECONDS','STOKE_CD','FIRE_AGE','TEMP_TIME','INCOME_TIME','EVENT_TIME']:
  check(r['open'].word(name)==r['paused'].word(name),f'Help pauses {name}')
 a=s.s['LOG_AGE'];check(r['open'].data[a:a+10]==r['paused'].data[a:a+10],'Help pauses notification lifetimes')
 check(r['resumed'].word('TAB')==0 and r['resumed'].word('STOKE_CD')<r['paused'].word('STOKE_CD'),'leaving Help resumes gameplay')
 check(r['paused'].word('STOKE_CD')-r['resumed'].word('STOKE_CD')<25,'leaving Help does not replay paused time')
 print('Help clears the sidebar, pauses timers and resumes without catch-up: OK',flush=True)

def hidden_locations():
 s=Scenario('hidden-locations').snap('start')
 for key in range(2,10):s.key(str(key),5).snap(str(key))
 s.word('FOREST',1).key('2').snap('forest').word('BUILDER',4).key('3').snap('build').building('workshop',1).key('4').snap('craft').building('trading post',1).key('5').snap('trade').word('POPULATION',1).key('6').snap('workers')
 r=s.execute();log=s.s['LOG_TEXT']
 for key in range(2,10):
  q=r[str(key)]
  check(q.word('TAB')==0 and q.word('SELECTED')==0,f'hidden shortcut {key} leaves location and selection unchanged')
  check(q.data[log:log+400]==r['start'].data[log:log+400],f'hidden shortcut {key} publishes no notification')
  check('ПОКА НИЧЕГО НЕТ' not in q.screen() and 'ЕЩЕ НЕ ОТКРЫТО' not in q.screen(),f'hidden shortcut {key} opens no empty/locked view')
 for name,tab in [('forest',1),('build',2),('craft',3),('trade',4),('workers',5)]:check(r[name].word('TAB')==tab,f'{name}: shortcut works once its tab is present')
 print('hidden location shortcuts are silent and inert; unlocked locations remain reachable: OK',flush=True)

def cooldown_bars():
 from PIL import Image
 s=Scenario('cooldown-bars')
 for remaining in [100,98,50,48,2,1,0]:
  s.word('STOKE_CD',remaining).call('BARS_DRAW').snap(str(remaining)).shot(str(remaining))
 s.key('ENTER').snap('pressed').shot('pressed').run(40).snap('later').shot('later')
 s.word('FOREST',1).building('trap',1).key('2')
 s.word('GATHER_CD',300).word('TRAPS_CD',450).call('BARS_DRAW').snap('forest').shot('forest')
 s.stock('compass',1).key('7').word('DEATH_CD',600).call('BARS_DRAW').shot('departure')
 s.flag('ship').key('8').word('LAUNCH_CD',1200).call('BARS_DRAW').shot('launch_full')
 s.word('LAUNCH_CD',600).call('BARS_DRAW').shot('launch')
 s.word('BUILDER',4).stock('wood',1000).key('3').snap('quantity').shot('quantity')
 # Fists plus both speed effects: duration must remain the one used at firing.
 s.call('START_EVENT',scene('encounters','0')).key('ENTER',1).word('ENEMY_HP',100).word('HP',100).word('PERKS',1,CAT['perks'].index('unarmed master')*2)
 s.word('STIM_TIME',30).word('WEAPON_CD',0).call('ATTACK',0).run(31).word('WEAPON_CD',5).call('BARS_DRAW').snap('attack').shot('attack')
 s.word('STIM_TIME',0).word('DIRTY',1).run(30).word('WEAPON_CD',2).call('BARS_DRAW').snap('buff_ended').shot('buff_ended')
 r=s.execute()
 def width(name,row):
  im=Image.open(ROOT/f'tmp/cooldown-bars-{name}.bmp').convert('L')
  band=im.crop((384,row*12+4,440,row*12+7))
  rows=[]
  for y in range(3):
   line=band.crop((0,y,56,y+1));rows.append(list(line.get_flattened_data() if hasattr(line,'get_flattened_data') else line.getdata()))
  n=sum(v>0 for v in rows[0])
  check(all(a==[255]*n+[0]*(56-n) for a in rows),f'{name}: solid contiguous white fill in fixed 56x3 area')
  return n
 for remaining,expected in [(100,56),(98,55),(50,28),(48,27),(2,2),(1,1),(0,0)]:
  check(width(str(remaining),6)==expected,f'{remaining}: cooldown width shrinks in individual pixels')
  check(not r[str(remaining)].screen().splitlines()[6][48:55].strip(),'cooldown digits removed from text plane')
 check(0<r['later'].word('STOKE_CD')<r['pressed'].word('STOKE_CD')<100,'physical Enter starts a real ticking cooldown')
 check(width('later',6)<width('pressed',6),'bar animates down without further input')
 check(width('forest',6)==28 and width('forest',7)==28,'gather and trap bars use their own 60/90-second durations')
 check(width('departure',6)==28 and width('launch',8)==28,'departure and launch timers use 120-second durations')
 check(width('launch_full',8)==56,'120-second full bar handles a numerator above 65535')
 from PIL import ImageChops
 check(ImageChops.subtract(plane_image('cooldown-bars-quantity','overlay'),plane_image('cooldown-bars-quantity','text')).crop((384,60,440,216)).getbbox() is None,'old cooldown overlays clear on a quantity menu; only gray count glyphs remain')
 check(r['quantity'].screen().splitlines()[6][48:55].strip()=='1','building quantities remain numbers')
 check(r['attack'].word('WEAPON_SPAN')==5 and width('attack',8)==56,'attack bar starts full using the perk/stimulant-adjusted duration')
 check(r['buff_ended'].word('BAR_MAX',16)==5 and width('buff_ended',8)==23,'active attack bar keeps its original scale after a speed buff expires')
 print('56-pixel cooldown bars, one-pixel steps, live countdowns, distinct durations and cleanup: OK',flush=True)

def enemy_cooldowns():
 from PIL import Image
 # Scene 0 is a real one-damage creature. Lengthen its native delay for clear
 # captures; force hit/miss probabilities only for deterministic feedback.
 s=Scenario('enemy-cooldown').word('HP',100).word('MAX_HP',100).call('START_EVENT',scene('encounters','0')).key('ENTER',1)
 s.word('ENEMY_HP',100).word('SCENE_BASE',100,8).word('ENEMY_CLOCK',100).word('ENEMY_SPAN',100).run(31).snap('open')
 for remaining in [100,98,50,48,2,1,0]:
  s.word('ENEMY_CLOCK',remaining).call('BARS_DRAW').shot(str(remaining))
 s.word('ENEMY_CLOCK',100).call('BARS_DRAW').snap('early').shot('early').run(30).snap('later').shot('later')
 s.word('SCENE_BASE',0,10).word('ENEMY_CLOCK',1).snap('before-miss').call('COMBAT_TICK').snap('miss').run(31).shot('miss')
 s.word('SCENE_BASE',100,10).word('ENEMY_CLOCK',1).snap('before-hit').call('COMBAT_TICK').snap('hit').run(31).shot('hit')
 s.word('ENEMY_STUN',20).word('ENEMY_CLOCK',50).word('DIRTY',1).run(10).snap('stun').shot('stun').run(10).snap('stun-later').run(40).snap('unstunned').shot('unstunned')
 s.word('ENEMY_STATUS',5).word('STATUS_TIME',100).word('ENEMY_CLOCK',50).word('DIRTY',1).run(10).snap('meditation').shot('meditation').run(20).snap('meditation-later')
 # Start frenzy through the native special-attack path, then let it expire
 # during a short wait. The bar must retain that wait's captured five ticks.
 s.word('ENEMY_STATUS',0).word('SCENE_BASE',4,18).word('SCENE_BASE',1,22).word('SPECIAL_CLOCK',0).call('COMBAT_TICK').call('BARS_DRAW').snap('frenzy').shot('frenzy')
 s.word('SCENE_BASE',0,22).word('STATUS_TIME',1).call('COMBAT_TICK').call('BARS_DRAW').snap('expired').shot('expired')
 s.word('ENEMY_CLOCK',1).call('COMBAT_TICK').call('BARS_DRAW').snap('normal').shot('normal')
 s.key('F2',40).snap('paused').shot('paused').run(30).snap('still-paused').key('AP2',10).snap('resumed').shot('resumed')
 s.word('ENEMY_HP',0).word('EXPLODE_TIME',30).word('DIRTY',1).run(5).snap('exploding').shot('exploding')
 s.word('EXPLODE_TIME',0).call('END_EVENT').word('DIRTY',1).run(31).snap('ended').shot('ended')
 r=s.execute()
 def width(name):
  im=Image.open(ROOT/f'tmp/enemy-cooldown-{name}.bmp').convert('RGB')
  rows=[[im.getpixel((x,y)) for x in range(384,440)] for y in range(88,91)]
  n=sum(p==(255,255,255) for p in rows[0])
  check(all(row==[(255,255,255)]*n+[(0,0,0)]*(56-n) for row in rows),f'enemy {name}: contiguous white cooldown pixels')
  return n
 check('АТАКА ПРОТИВНИКА' in r['open'].screen().splitlines()[7] and r['open'].word('FOCUS_ROW')>=8,'enemy attack is labelled above the selectable player weapons')
 check(r['open'].word('BAR_PTR',14)==s.s['ENEMY_CLOCK'],'enemy bar follows the live attack clock')
 for remaining,expected in [(100,56),(98,55),(50,28),(48,27),(2,2),(1,1),(0,0)]:
  check(width(str(remaining))==expected,f'enemy {remaining}: individual-pixel cooldown width')
 check(0<r['later'].word('ENEMY_CLOCK')<r['early'].word('ENEMY_CLOCK') and width('later')<width('early'),'enemy countdown visibly advances without player input')
 def newest_is(snapshot,label):
  return snapshot.data[s.s['LOG_TEXT']:s.s['LOG_TEXT']+80].split(b'\0')[0]==snapshot.data[s.s[label]:].split(b'\0')[0]
 def visible_label(name,label,column,row):
  # SCREEN_BUF is scratch during composition; check the displayed ROM glyphs.
  data=r[name].data;text=data[s.s[label]:].split(b'\0')[0]
  plane=(ROOT/f'tmp/enemy-cooldown-{name}.text-plane').read_bytes()
  return all(plane[(row*12+y)*80+column+i]==data[s.s['FONT']+(code-32)*11+y] for i,code in enumerate(text) for y in range(11))
 check(r['miss'].word('HP')==r['before-miss'].word('HP') and newest_is(r['miss'],'S_ENEMY_MISS'),'enemy miss announces the attack without causing damage')
 check(r['hit'].word('HP')==r['before-hit'].word('HP')-1 and newest_is(r['hit'],'S_HURT'),'enemy hit applies damage and announces the attack')
 check(all(r[k].word('ENEMY_CLOCK')==100 and r[k].word('ENEMY_SPAN')==100 for k in ['miss','hit']),'both enemy hits and misses restart the full native wait')
 check(r['stun'].word('ENEMY_CLOCK')==r['stun-later'].word('ENEMY_CLOCK')==50 and visible_label('stun','S_STUN',1,7),'stun visibly explains the frozen enemy countdown')
 check(r['unstunned'].word('ENEMY_CLOCK')<50 and visible_label('unstunned','S_ENEMY_ATTACK',1,7),'stun expiry restores the attack label and resumes the countdown')
 check(r['meditation'].word('ENEMY_CLOCK')==r['meditation-later'].word('ENEMY_CLOCK')==50 and visible_label('meditation','S_MEDITATION',27,5),'meditation status explains its paused countdown')
 check(r['frenzy'].word('ENEMY_SPAN')==5 and width('frenzy')==45,'native frenzy starts a five-tick enemy bar without waiting for text redraw')
 check(r['expired'].word('ENEMY_STATUS')==0 and r['expired'].word('ENEMY_SPAN')==5 and width('expired')==34,'frenzy expiry does not rescale the already-running enemy wait')
 check(r['normal'].word('ENEMY_SPAN')==100 and width('normal')==56,'the next ordinary attack restores the normal cooldown scale')
 check(r['paused'].word('ENEMY_CLOCK')==r['still-paused'].word('ENEMY_CLOCK') and r['paused'].word('ENEMY_SPAN')==r['still-paused'].word('ENEMY_SPAN'),'save modal freezes enemy cooldown and its scale')
 check(width('paused')==0 and r['resumed'].word('BAR_PTR',14)==s.s['ENEMY_CLOCK'],'enemy bar hides for the modal and returns on cancel')
 check(width('exploding')==0 and r['exploding'].word('BAR_PTR',14)==0,'dead enemies have no attack bar during the explosion wait')
 check(width('ended')==0 and 'АТАКА ПРОТИВНИКА' not in r['ended'].screen(),'leaving combat erases enemy attack text and pixels')
 for name in ['early','later','hit','miss','stun','meditation','ended']:
  Image.open(ROOT/f'tmp/enemy-cooldown-{name}.bmp').save(ROOT/f'tmp/enemy-cooldown-{name}.png')
 print('enemy attack countdown, hit/miss feedback, stun/meditation, frenzy scale, pause and cleanup: OK',flush=True)

def recipes():
 x=json.loads((ROOT/'src/res/upstream.json').read_text())
 rs=sum(x['recipes'].values(),[])
 s=Scenario('recipes').word('TEMPERATURE',3)
 for i,recipe in enumerate(rs):
  for k in CAT['resources']:s.stock(k,10000)
  for k in CAT['buildings']:s.building(k,0)
  if recipe['key'] in CAT['resources']:s.stock(recipe['key'],0)
  s.call('CRAFT',i).snap(str(i))
 s.stock('wood',9).building('trap',0).call('CRAFT',0).snap('short')
 s.stock('wood',100).building('trap',1).call('CRAFT',0).snap('scaled')
 s.building('trap',10).call('CRAFT',0).snap('maximum')
 s.word('TEMPERATURE',0).building('trap',0).call('CRAFT',0).snap('cold')
 r=s.execute()
 for i,recipe in enumerate(rs):
  got=r[str(i)];k=recipe['key']
  qty=got.word('BUILDINGS',CAT['buildings'][k]) if k in CAT['buildings'] else got.stock(k)
  check(qty==recipe['quantity'],f'crafted {k} quantity')
  check(all(got.stock(c)==10000-n for c,n in recipe['cost'].items()),f'original cost for {k}')
 check(r['short'].stock('wood')==9 and r['short'].word('BUILDINGS')==0,'unaffordable craft is atomic')
 check(r['scaled'].stock('wood')==80 and r['scaled'].word('BUILDINGS')==2,'trap cost increases by ten')
 check(r['maximum'].stock('wood')==80 and r['maximum'].word('BUILDINGS')==10,'trap maximum enforced')
 check(r['cold'].word('BUILDINGS')==0,'cold builder cannot craft')
 print('all 46 recipes/trades, dynamic costs, limits, atomic spending: OK',flush=True)

def notifications():
 s=Scenario('notifications').word('AWAY',1)
 names=['S_AWAKE','S_FIRELIT','S_STRANGER','S_FOREST','S_HOME','S_DEAD']
 for name in names:s.word('NOTICE',s.s[name]).call('NOTIFY')
 s.run(40).snap('five').shot('five').run(200).snap('reading')
 s.word('NOTICE',s.s['S_GATHERED']).call('NOTIFY').run(540).snap('older_expired').shot('older_expired')
 s.run(250).snap('empty').shot('empty')
 s.word('NOTICE',s.s['S_WAIT']).call('NOTIFY').call('NOTIFY').run(40).snap('repeated')
 # The log remains readable after changing panels; the map stays above it.
 s.word('TAB',10).word('POS_Y',60).word('DIRTY',1).run(40).snap('map').shot('map')
 r=s.execute()
 def source(snapshot,label):
  return snapshot.data[s.s[label]:].split(b'\0',1)[0]
 def entries(snapshot):
  p=s.s['LOG_TEXT']
  return [snapshot.data[p+i*80:p+(i+1)*80].split(b'\0',1)[0] for i in range(5)]
 expected=[source(r['five'],name) for name in reversed(names[1:])]
 check(entries(r['five'])==expected,'newest first, sixth message evicts only the oldest')
 check(entries(r['reading'])==expected,'messages remain readable for several seconds')
 check(entries(r['older_expired'])==[source(r['five'],'S_GATHERED')]+[b'']*4,'each message expires independently after 30 seconds')
 check(entries(r['empty'])==[b'']*5,'log expires without player input')
 check(all(not line.strip() for line in r['empty'].screen().splitlines()[18:23]),'expired text is cleared from the composed display')
 check(entries(r['repeated'])[:2]==[source(r['five'],'S_WAIT')]*2,'repeated actions are separate log entries')
 check(r['map'].word('VIEW_Y')==50 and r['map'].word('VIEW_ROW')==11,'map viewport remains within rows 6 through 16 at southern edge')
 check(r['map'].screen().splitlines()[18:23]==r['repeated'].screen().splitlines()[18:23],'changing panels preserves the notification history')
 from PIL import Image
 five=Image.open(ROOT/'tmp/notifications-five.bmp').convert('RGB')
 empty=Image.open(ROOT/'tmp/notifications-empty.bmp').convert('RGB')
 for row in range(18,23):
  check(five.crop((0,row*12,640,(row+1)*12)).getbbox() is not None,f'log row {row} is actually visible')
 check(empty.crop((0,18*12,640,23*12)).getbbox() is None,'expired log pixels disappear from framebuffer')
 five.save(ROOT/'tmp/notifications.png')
 print('five-row notification history, ordering, independent expiry, repeated actions and map layout: OK',flush=True)

def notification_fade():
 from PIL import Image
 s=Scenario('notification-fade').word('AWAY',1)
 # Identical messages prove that a shade change does not require new glyphs.
 # This text includes Й, whose accent occupies the first glyph scanline.
 for _ in range(5):s.word('NOTICE',s.s['S_SHIVER']).call('NOTIFY')
 s.run(40).shot('fresh').run(250).shot('older').run(250).shot('dark')
 s.word('AWAY',0).key('0').shot('help').key('1').shot('back')
 # Help now pauses the log; add its 35-frame stay to the later wait.
 s.run(100).shot('last_seconds').run(55).shot('last_step').run(50).shot('gone')
 s.execute()
 images={name:Image.open(ROOT/f'tmp/notification-fade-{name}.bmp').convert('RGB')
         for name in ['fresh','older','dark','help','back','last_seconds','last_step','gone']}
 def color_set(im):return set(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata())
 reference=images['fresh'].crop((0,18*12,640,19*12)).convert('L').point(lambda v:255 if v else 0)
 expected={'fresh':[255,128,128,128,128], 'older':[255,96,96,96,96],
           'dark':[255,0,0,0,0], 'back':[255,0,0,0,0],
           'last_seconds':[128,0,0,0,0], 'last_step':[96,0,0,0,0], 'gone':[0]*5}
 for name,levels in expected.items():
  im=images[name]
  for i,level in enumerate(levels):
   row=im.crop((0,(18+i)*12,640,(19+i)*12))
   colors=color_set(row)
   check(colors==({(0,0,0),(level,level,level)} if level else {(0,0,0)}),f'{name} row {i}: actual grayscale {level}, including first scanline')
   if level:check(row.convert('L').point(lambda v:255 if v else 0).tobytes()==reference.tobytes(),f'{name} row {i}: font pixels intact while fading')
  for box in [(0,0,640,11),(0,48,640,18*12),(0,23*12,640,24*12)]:
   check(color_set(im.crop(box))<={(0,0,0),(255,255,255)},f'{name}: fading confined to the log')
 check(color_set(images['help'].crop((0,48,640,288)))<={(0,0,0),(255,255,255)},'help restores white on rows previously used by gray log entries')
 images['fresh'].save(ROOT/'tmp/notification-fade.png')
 print('native grayscale fade, unchanged glyphs, white UI, hidden log and timed black: OK',flush=True)

def notification_superseded():
 from PIL import Image
 s=Scenario('notification-superseded').word('BUILDER',4).word('FIRE',2).word('FOREST',1).stock('wood',100)
 # Actual repeated stove actions: later key presses produce identical WAITs.
 for i in range(5):s.key('ENTER').snap(str(i)).shot(str(i))
 s.run(250).snap('aged').shot('aged').key('ENTER').snap('new').shot('new')
 r=s.execute()
 for name in ['1','2','3','4','new']:
  im=Image.open(ROOT/f'tmp/notification-superseded-{name}.bmp').convert('RGB')
  check(max(im.crop((0,216,640,228)).convert('L').getextrema())==255,f'{name}: only current stove message stays bright')
  for row in range(19,23):
   check(im.crop((0,row*12,640,(row+1)*12)).convert('L').getextrema()[1]<=128,f'{name}: every previous stove message is already old')
 check(r['new'].word('LOG_AGE',2)<=150,'displaced current message begins a 15-second fade')
 check(r['new'].word('LOG_AGE',4)<=r['aged'].word('LOG_AGE',2),'another arrival does not restart an older message fade')
 check(r['4'].data[s.s['LOG_TEXT']:s.s['LOG_TEXT']+80].split(b'\0')[0]==r['4'].data[s.s['LOG_TEXT']+80:s.s['LOG_TEXT']+160].split(b'\0')[0],'repeated keypress regression covers identical current and previous text')
 Image.open(ROOT/'tmp/notification-superseded-4.bmp').save(ROOT/'tmp/notification-superseded.png')
 print('repeated stove keypresses immediately demote prior messages without restarting old fades: OK',flush=True)

def economy():
 s=Scenario('economy').word('POPULATION',4).building('lodge',1).word('JOBS',1,2).call('COLLECT_INCOME').snap('half').call('COLLECT_INCOME').snap('whole')
 s.building('smokehouse',1).word('JOBS',1,8).stock('wood',4).stock('meat',5).call('COLLECT_INCOME').snap('consume')
 # Test production with no gatherers so missing one input cannot be hidden by income.
 s.word('POPULATION',1).word('JOBS',0,2).stock('wood',4).stock('meat',5).stock('cured meat',0).call('COLLECT_INCOME').snap('blocked')
 s.stock('wood',5).call('COLLECT_INCOME').snap('produced')
 s.word('POPULATION',1).word('JOBS',0,8).call('ASSIGN_JOB',2,1).call('ASSIGN_JOB',2,1).snap('assigned')
 s.stock('wood',29999).call('ADD_RESOURCE',0,100,s.s['STORES']).snap('saturated')
 r=s.execute()
 check(r['half'].stock('fur')==0 and r['whole'].stock('fur')==1,'hunter half-unit income accumulates')
 check(r['whole'].stock('wood')==6,'unassigned workers gather one per interval')
 check(r['blocked'].stock('wood')==4 and r['blocked'].stock('meat')==5 and r['blocked'].stock('cured meat')==0,'production consumes nothing when input missing')
 check(r['produced'].stock('wood')==0 and r['produced'].stock('meat')==0 and r['produced'].stock('cured meat')==1,'smokehouse recipe')
 check(r['assigned'].word('JOBS',2)==1,'cannot assign more people than population')
 check(r['saturated'].stock('wood')==30000,'stock saturation does not wrap')
 print('worker fractions, production transactions, assignments, saturation: OK',flush=True)

def inventory_world():
 s=Scenario('world').snap('map').stock('waterskin',1).stock('l armour',1).stock('rucksack',1).call('CAPACITIES').snap('capacity')
 s.stock('cured meat',25).call('TAKE_ONE',CAT['resources']['cured meat'],0,0,0,0,s.s['STORES'])
 for _ in range(25):s.call('TAKE_ONE',CAT['resources']['cured meat'],0,0,0,0,s.s['STORES'])
 s.snap('full').call('EMBARK').snap('depart')
 s.byte('WORLD_MAP',7,1861).word('DIRTY',1).run(25).key('RIGHT',60).snap('cave').shot('cave')
 s.key('ENTER',20).snap('no_torch')
 s.stock('torch',1,True).key('ENTER',60).snap('entered').shot('inside')
 s.flag('ship').byte('WORLD_MAP',17,1861).call('DIE').snap('dead')
 s.key('ENTER',1).word('DEATH_CD',0).call('EMBARK').stock('alien alloy',3,True).flag('ship').call('GO_HOME').snap('home')
 r=s.execute()
 m=r['map'];grid=m.data[m.s['WORLD_MAP']:m.s['WORLD_MAP']+3721]
 specs=[(1,5,5),(1,10,10),(1,20,20),(10,1,45),(5,3,10),(10,10,20),(20,20,45),(1,28,28),(10,15,45),(5,18,45),(1,15,45),(1,28,28)]
 for i,(num,lo,hi) in enumerate(specs):
  pos=[j for j,v in enumerate(grid) if v==i+3]
  check(len(pos)==num and all(lo<=abs(j%61-30)+abs(j//61-30)<=hi for j in pos),f'landmark {i} count and radius')
 check(r['capacity'].word('CAPACITY')==200 and r['capacity'].word('MAX_HP')==15 and r['capacity'].word('MAX_WATER')==20,'passive upgrades')
 check(r['full'].stock('cured meat',True)==20 and r['full'].stock('cured meat')==5,'bag capacity enforced without losing items')
 check(r['cave'].word('SCENE_ID')==scene('setpieces','cave'),'keyboard movement opens a cave')
 check(r['no_torch'].word('SCENE_ID')==scene('setpieces','cave'),'torch gate enforced')
 check(r['entered'].stock('torch',True)==0 and r['entered'].word('SCENE_ID')!=scene('setpieces','cave'),'torch spent once for branch')
 check(r['dead'].word('AWAY')==0 and r['dead'].stock('cured meat',True)==0,'death returns home and loses bag')
 check(r['dead'].word('FLAGS')==0 and r['dead'].data[m.s['WORLD_MAP']:m.s['WORLD_MAP']+3721]==grid,'death rolls back world changes')
 check(r['home'].word('FLAGS')==1 and r['home'].stock('alien alloy')==3,'successful return commits discoveries and loot')
 print('world topology, equipment, capacity, exploration, death and return: OK',flush=True)

def disk_scenes():
 s=Scenario('scenes')
 # Read through real firmware/FDD for every record, including tracks and sides.
 for sc in CAT['scenes']:
  s.call('DISK_READ',sc['id']).snap(str(sc['id']))
 r=s.execute();bank=(ROOT/'build/DARKRM.DAT').read_bytes();base=s.s['SCENE_BASE']
 for sc in CAT['scenes']:
  got=r[str(sc['id'])].data[base:base+sc['bytes']]
  check(got==bank[sc['block']*512:sc['block']*512+sc['bytes']],f'native FDD scene {sc["id"]}')
 print(f'all {len(CAT["scenes"])} scenes read correctly through RT-11/FDD: OK',flush=True)

def combat():
 s=Scenario('combat').word('SCENE_ID',0).call('LOAD_SCENE').key('ENTER',1).word('AWAY',1).word('ACTIVE_SCENE',1).word('HP',100).word('MAX_HP',100)
 weapons=json.loads((ROOT/'src/res/upstream.json').read_text())['weapons']
 for i,(k,w) in enumerate(weapons.items()):
  if k!='fists':s.stock(k,2,True)
  for ammo in w.get('cost',{}):s.stock(ammo,2,True)
  s.word('ENEMY_HP',100).word('SEED',2).word('WEAPON_CD',0,i*2).call('ATTACK',i).snap(k)
 s.word('HP',1).stock('cured meat',1,True).call('HEAL',0).snap('healed')
 s.word('HEAL_CD',0).stock('kinetic armour',1).call('HEAL',3).word('ENEMY_STATUS',0).call('ENEMY_DAMAGE',10).snap('shield')
 s.word('ENEMY_HP',100).word('ENEMY_STATUS',2).word('SCENE_BASE',100,4).word('WEAPON_CD',0,2).word('SEED',2).call('ATTACK',1).snap('enemyshield')
 s.word('AWAY',1).word('HP',30).word('MAX_HP',30).word('BAG',0,CAT['resources']['cured meat']).word('WATER',0).word('POS_X',30).word('POS_Y',30).call('SNAPSHOT_WORLD').byte('WORLD_MAP',15,1861).byte('WORLD_MAP',15,1862).call('MOVE',3).snap('thirst').call('MOVE',3).snap('dehydration')
 r=s.execute()
 for k,w in weapons.items():
  if isinstance(w['damage'],int):check(r[k].word('ENEMY_HP')==100-w['damage'],f'{k} original damage')
  else:check(r[k].word('ENEMY_STUN')==40,f'{k} stuns for four seconds')
  for ammo in w.get('cost',{}):check(r[k].stock(ammo,True)==1,f'{k} consumes {ammo}')
 check(r['healed'].word('HP')==9 and r['healed'].stock('cured meat',True)==0,'meat heals eight and is spent')
 check(r['shield'].word('HP')==19 and r['shield'].word('SHIELD_TIME')==0 and r['shield'].stock('kinetic armour')==1,'kinetic shield converts one hit to healing without consuming armour')
 check(r['enemyshield'].word('ENEMY_HP')==100 and r['enemyshield'].word('ENEMY_STATUS')==0,'enemy shield heals to max and breaks')
 check(r['thirst'].word('AWAY')==1 and r['dehydration'].word('AWAY')==0,'two dry steps cause death')
 print('all 12 weapons, ammunition, healing, shields and dehydration: OK',flush=True)

def milestones():
 s=Scenario('milestones').call('EMBARK').word('POS_X',35)
 for e,flag in [('ironmine','ironmine'),('coalmine','coalmine'),('sulphurmine','sulphurmine')]:
  s.word('SCENE_ID',scene('setpieces',e,'cleared')).call('LOAD_SCENE').snap(flag)
 s.word('SCENE_ID',scene('setpieces','ship')).call('LOAD_SCENE').snap('ship')
 s.word('SCENE_ID',scene('executioner','executioner-intro','7')).call('LOAD_SCENE').snap('fabricator')
 s.word('SCENE_ID',scene('executioner','executioner-engineering','8')).call('LOAD_SCENE').snap('engineering')
 s.word('SCENE_ID',scene('executioner','executioner-medical','17')).call('LOAD_SCENE').snap('medical')
 s.word('SCENE_ID',scene('executioner','executioner-martial','13')).call('LOAD_SCENE').snap('martial')
 s.call('GO_HOME').word('HULL',1000).call('LIFTOFF')
 for _ in range(599):s.call('SPACE_TICK')
 s.snap('before_end').call('SPACE_TICK')
 s.snap('end').call('DRAW').call('FLUSH').shot('end')
 r=s.execute()
 for name in ['ironmine','coalmine','sulphurmine','ship','engineering','medical','martial']:
  check(r[name].word('FLAGS',CAT['flags'].index(name)*2)==1,f'{name} progression hook')
 check(r['fabricator'].word('FLAGS',8)==1,'executioner unlocks fabricator')
 check(r['before_end'].word('WON')==0 and r['before_end'].word('ALTITUDE')==59,'flight lasts sixty seconds')
 check(r['end'].word('WON')==1 and r['end'].word('TAB')==12,'spaceship reaches ending')
 print('mine/ship/fabricator/wing milestones and playable ending: OK',flush=True)

def edge_cases():
 s=Scenario('edges').snap('initial')
 s.call('APPLY_MAP').snap('chart')
 s.word('HULL',1).call('LIFTOFF').word('THRUSTERS',8).call('SPACE_MOVE',0o116).call('SPACE_MOVE',0o154).snap('steer')
 s.word('DEBRIS',17).word('DEBRIS',5,2).word('DEBRIS',2,4).word('SPAWN_CLOCK',100).call('SPACE_TICK').snap('crash')
 s.word('POPULATION',5).word('JOBS',3,2).word('JOBS',2,4).call('KILL_PEOPLE',1).snap('loss')
 s.word('SCENE_ID',scene('room','9','alloy')).call('LOAD_SCENE').snap('alloy')
 s.word('SCENE_ID',scene('global','0','spare')).call('LOAD_SCENE').snap('spared')
 s.word('SCENE_ID',scene('executioner','executioner-engineering','7')).call('LOAD_SCENE').key('ENTER',1).word('HP',80).word('MAX_HP',85).stock('bone spear',1,True).stock('stim',1,True).call('HEAL',4).word('SEED',2).call('ATTACK',1).snap('stim')
 s.word('ENEMY_HP',100).word('ENEMY_STATUS',5).word('WEAPON_CD',0,2).word('SEED',2).call('ATTACK',1).snap('meditation')
 s.word('ENEMY_STATUS',0).word('ENEMY_CLOCK',1).call('COMBAT_TICK').snap('reflect')
 s.word('ENEMY_STATUS',2).word('STATUS_TIME',0).word('ENEMY_CLOCK',200).call('COMBAT_TICK').snap('persistent_shield')
 r=s.execute();m=r['initial'];off=m.s['MAP_SEEN']
 check(sum(m.data[off:off+3721])==13,'radius-two fog reveal is a Manhattan diamond')
 check(sum(r['chart'].data[off:off+3721])>13,'map reveals an unexplored radius-five area')
 check(r['steer'].word('SHIP_X')==17 and r['steer'].word('SHIP_Y')==6,'engines improve horizontal and vertical movement')
 check(r['crash'].word('TAB')==7 and r['crash'].word('LAUNCH_CD')==1200,'flight collision and two-minute recovery')
 check(r['loss'].word('POPULATION')==4 and r['loss'].word('JOBS',2)+r['loss'].word('JOBS',4)==4,'casualties retain feasible job assignments')
 check(r['alloy'].stock('alien alloy')==1,'medicine exchange hook grants alloy')
 check(r['spared'].word('PERKS',CAT['perks'].index('stealthy')*2)==1 and r['spared'].word('FLAGS',18)==2,'spared thief grants stealth and ends theft')
 check(r['stim'].word('HP')==70 and r['stim'].word('WEAPON_CD',2)==10 and r['stim'].stock('stim',True)==1,'stim hurts, halves cooldown and is reusable')
 check(r['meditation'].word('ENEMY_HP')==100 and r['meditation'].word('MEDITATE')==2,'meditation absorbs damage')
 check(r['reflect'].word('HP')==68 and r['reflect'].word('MEDITATE')==0,'meditation reflects stored damage')
 check(r['persistent_shield'].word('ENEMY_STATUS')==2,'shield lasts until struck')
 print('map charts, flight controls/crashes, casualties, rewards, buffs: OK',flush=True)

def rt11_roundtrip():
 s=Scenario('rt11').snap('first').shot('first').key('ENTER').snap('played').key('STOP',300).snap('exit').shot('exit').command('DIR').snap('dir').shot('dir').command('R DARKRM',1100).key('ENTER',50).snap('second').shot('second')
 # Normal scene reads followed by quitting from a late-game context.
 s.call('START_EVENT',scene('setpieces','ship')).run(50).key('STOP',300).snap('scene_exit').command('RUN DARKRM',1100).key('ENTER',50).snap('third').shot('third').key('0').key('ENTER',300).snap('help_exit')
 r=s.execute();first=r['first'];base=Volume(ROOT/'orig/RT11BASE.DSK');d=base.find('DIR.SAV')
 expected=bytes(base.img[d.block*512+512:d.block*512+576])
 check(r['dir'].data[512:576]==expected,'DIR command loads and executes after game exit')
 check(r['played'].word('FIRE')>0,'first launch actually played')
 from PIL import Image
 reference=without_overlay('rt11-first').tobytes()
 for name in ['second','third']:
  check(without_overlay('rt11-'+name).tobytes()==reference,f'{name} redraws the complete framebuffer independent of animation phase')
  check(r[name].word('FIRE')==0 and 'РАЗЖЕЧЬ ОГОНЬ' in r[name].screen(),f'{name} R DARKRM starts a fresh playable game')
  check(r[name].word('PP_DEST')==first.word('PP_DEST'),f'{name} reuses freed PPU memory')
  check(r[name].word('PP_READY')==1,f'{name} custom keyboard/timer installed')
 ppu=(ROOT/'tmp/rt11-first.ppu').read_bytes()
 save=first.word('PP_DEST')+s.s['PP_BACKUP']-s.s['PP_START']
 for name in ['exit','scene_exit','help_exit']:
  check(r[name].word('PP_READY')==0,f'{name} relinquishes PPU')
  for off in [0o4,0o6,0o30,0o32,0o100,0o102]:
   check(r[name].data[off:off+2]==first.data[off:off+2],f'{name} retains monitor vector {off:o}')
  after=(ROOT/f'tmp/rt11-{name}.ppu').read_bytes()
  for vector,label in [(0o100,'PP_OLDTIMER'),(0o300,'PP_OLDKEY')]:
   old=first.word('PP_DEST')+s.s[label]-s.s['PP_START']
   check(after[vector:vector+2]==ppu[old:old+2],f'{name} restores PPU {label}')
  for off in [0o2372,0o2400,0o2402,0o2406,0o2456,0o2470,0o2472,0o7026]:
   old=save+off-0o2300
   check(after[off:off+2]==ppu[old:old+2],f'{name} restores display chain {off:o}')
 # Moving the DAT file proves no physical disk locations are baked into the SAV.
 v=Volume(ROOT/'build/darkroom.dsk');v.rm('DARKRM.DAT');(ROOT/'tmp/padding.bin').write_bytes(bytes(1024));v.put('PAD.DAT',ROOT/'tmp/padding.bin');v.put('DARKRM.DAT',ROOT/'build/DARKRM.DAT');v.save(ROOT/'tmp/moved.dsk')
 sc=CAT['scenes'][-1]
 m=Scenario('moved',ROOT/'tmp/moved.dsk').call('DISK_READ',sc['id']).snap('last').execute()['last']
 bank=(ROOT/'build/DARKRM.DAT').read_bytes();start=s.s['SCENE_BASE']
 check(m.data[start:start+sc['bytes']]==bank[sc['block']*512:sc['block']*512+sc['bytes']],'copied DAT at different disk location reads correctly')
 for mode in ['missing','incompatible']:
  v=Volume(ROOT/'build/darkroom.dsk')
  if mode=='missing':v.rm('DARKRM.DAT')
  else:
   e=v.find('DARKRM.DAT');v.img[e.block*512]=0
  path=ROOT/f'tmp/{mode}.dsk';v.save(path)
  q=Scenario(mode,path).snap('error').shot('error').command('DIR').snap('dir').execute()
  check(q['error'].word('PP_READY')==0,f'{mode} data rejected before PPU takeover')
  check(q['dir'].data[512:576]==expected,f'{mode} data returns to usable RT-11')
 # An OS read error during a scene must also release graphics/input cleanly.
 bad=Scenario('read-error').word('AWAY',1).word('TAB',10).word('WATER',10).stock('cured meat',20,True).byte('WORLD_MAP',7,1861)
 bad=bad.word('SCENE_DIR',bad.s['SCENE_BLOCKS'],scene('setpieces','cave')*4).key('RIGHT',300).snap('exit').shot('error').command('DIR').snap('dir').execute()
 check(bad['exit'].word('PP_READY')==0 and bad['exit'].word('RT_TRIES')==0,'runtime read error exhausts bounded retries and restores/releases PPU')
 check(bad['dir'].data[512:576]==expected,'runtime read error returns to usable RT-11')
 print('RT-11 exit, DIR, relaunches, PPU release, relocated/missing/incompatible data and read error: OK',flush=True)

def main():
 (ROOT/'tmp/verification.json').unlink(missing_ok=True)
 from verify_saves import verify_saves
 from verify_debug_saves import verify_debug_saves
 from verify_exploration import verify_compass, verify_encounters
 from verify_release import verify_release
 from verify_pages import verify_pages
 from verify_travel import verify_travel
 initial=static();verify_pages(check);verify_release(check);verify_debug_saves(check);verify_saves(check);verify_travel(check);keyboard();decorations();square_cursor_layout();disabled_recipes();location_and_fire();worker_controls();packing_arrows();help_pause();hidden_locations();cooldown_bars();enemy_cooldowns();notifications();notification_fade();notification_superseded();recipes();economy();inventory_world();disk_scenes();combat();milestones();edge_cases();verify_compass(check);verify_encounters(check);rt11_roundtrip()
 check(hashlib.sha256((ROOT/'build/darkroom.dsk').read_bytes()).hexdigest()==initial,'released disk unchanged; scenario disks allow only RT-11 SWAP.SYS writes')
 (ROOT/'tmp/verification.json').write_text(json.dumps({'checks':checks,'disk_sha256':initial,'result':'passed'},indent=2)+'\n')
 print(f'PASS: {checks} checks; game disk unchanged',flush=True)
if __name__=='__main__':main()
