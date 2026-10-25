#!/usr/bin/env python3
"""Compile editable UTF-8 resources and audited upstream data to PDP-11 tables."""
import json,re,struct,textwrap,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'src/res'; OUT=ROOT/'build'
SCENE_BASE=int(re.search(r'SCENE_BASE = ([0-7]+)',(ROOT/'src/defs.mac').read_text())[1],8)
x=json.loads((SRC/'upstream.json').read_text())
# Callback hashes are a review gate, not an automatic JS translator.
audit=json.loads((SRC/'hook-audit.json').read_text());actual={}
def audit_hooks(v,path):
 if isinstance(v,dict):
  if list(v)==['js']:actual[path]=hashlib.sha256(v['js'].encode()).hexdigest()
  else:
   for k,z in v.items():audit_hooks(z,path+'/'+k)
 elif isinstance(v,list):
  for i,z in enumerate(v):audit_hooks(z,path+'/'+str(i))
for g in ['encounters','setpieces','executioner','room','outside','global']:audit_hooks(x[g],g)
if actual!={p:v['sha256'] for p,v in audit.items()}:
 raise SystemExit('Upstream callbacks changed: audit native semantics and update src/res/hook-audit.json explicitly')
extra=json.loads((SRC/'ru-extra.json').read_text())
translations=x['translations']|extra
for line in (SRC/'ru-extra.txt').read_text().splitlines():
 if line and not line.startswith('#'):
  key, val=line.split('|',1); translations[key]=val
KOI={c:64+i for i,c in enumerate('ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧЪ')}
def koi(s):
 s=s.upper().replace('Ё','Е').replace('—','-').replace('–','-').replace('’',"'").replace('…','...').replace('\xa0',' ')
 return bytes(KOI[c] if c in KOI else ord(c)+32 if 'A'<=c<='Z' else ord(c) if c=='\n' or 32<=ord(c)<=63 else 63 for c in s)
missing=set()
def tr(s):
 if not s:return ''
 if s in translations and translations[s]:return translations[s].replace('&nbsp;',' ')
 missing.add(s)
 return 'НЕ ПЕРЕВЕДЕНО'
def ident(s):return re.sub('[^A-Z0-9]','_',s.upper())
resources=['wood','fur','meat','scales','teeth','cloth','charm','leather','cured meat','iron','coal','steel','sulphur','bullets','energy cell','medicine','bait']
buildings=[r['key'] for r in x['recipes']['craft'] if r['type']=='building']
for group in x['recipes'].values():
 for r in group:
  if r['key'] not in resources and r['key'] not in buildings:resources.append(r['key'])
for k in x['weapons']:
 if k!='fists' and k not in resources:resources.append(k)
for k in ['hypo blueprint','kinetic armour blueprint','plasma rifle blueprint','disruptor blueprint','glowstone blueprint','stim blueprint']:
 resources.append(k)
# Catch every loot/reward key, including the later additions.
def scan(v):
 if isinstance(v,dict):
  for k,z in v.items():
   if k in ['loot','reward','cost'] and isinstance(z,dict):
    for a in z:
     if a not in resources and a not in buildings:resources.append(a)
   scan(z)
 elif isinstance(v,list):
  for z in v:scan(z)
scan({k:v for k,v in x.items() if k in ['encounters','setpieces','executioner','room','outside','global']})
res={r:i*2 for i,r in enumerate(resources)}
bld={r:i*2 for i,r in enumerate(buildings)}
flags=['ship','ironmine','coalmine','sulphurmine','executioner','engineering','medical','martial','cityCleared','thieves']
perks=['gastronome','scout','evasive','precise','barbarian','stealthy','slow metabolism','desert rat','unarmed master','boxer','martial artist']
data=[]; constants=[]; strings={}
def w(label,vals):
 data.append(label+':')
 for i in range(0,len(vals),8):
  data.append(' .WORD '+','.join(str(v) if isinstance(v,str) else f'{v}.' for v in vals[i:i+8]))
def string(s):
 if s not in strings:strings[s]='STR'+str(len(strings))
 return strings[s]
def pairs(cost):
 vals=[]
 for k,v in cost.items():
  if v:vals.extend([res[k],int(v)])
 return [len(vals)//2]+vals
for k,v in res.items():constants.append(f'R_{ident(k)} = {v}.')
for k,v in bld.items():constants.append(f'B_{ident(k)} = {v}.')
for i,k in enumerate(flags):constants.append(f'F_{ident(k)} = {i*2}.')
for i,k in enumerate(perks):constants.append(f'P_{ident(k)} = {i*2}.')
constants+= [f'NRES = {len(res)}.',f'NBLD = {len(bld)}.',f'NWORK = {len(x["workers"])}.']
w('RES_NAMES',[string(tr(k)) for k in resources]);w('BLD_NAMES',[string(tr(k)) for k in buildings]);w('PERK_NAMES',[string(tr(k)) for k in perks])
# Recipe: name, category (building/craft/trade/fabricate), index, max, quantity,
# cost list pointer, increment for wood, blueprint resource or -1.
recipes=[];cost_lists={}
for group,rs in x['recipes'].items():
 for r in rs:
  i=len(recipes);k=r['key'];cat=0 if k in bld else {'craft':1,'trade':2,'fabricate':3}[group]
  cost_lists.setdefault(tuple(pairs(r['cost'])),[]).append(f'COST{i}')
  recipes.append([string(tr(k)),cat,bld[k] if cat==0 else res[k],r['maximum'],r['quantity'],f'COST{i}',r['increment'].get('wood',0),res.get(k+' blueprint',-1) if r['blueprint'] else -1])
# Share immutable lists; RECIPE_COST copies them before applying increments.
for values,labels in cost_lists.items():
 data.extend(label+':' for label in labels[:-1]);w(labels[-1],values)
constants.append(f'NREC = {len(recipes)}.')
w('RECIPES',[a for r in recipes for a in r])
# Workers: name, unlock kind 0 always 1 building 2 flag, index, income deltas x2.
worker_unlock=[(0,0),(1,bld['lodge']),(1,bld['lodge']),(1,bld['tannery']),(1,bld['smokehouse']),(2,2),(2,4),(2,6),(1,bld['steelworks']),(1,bld['armoury'])]
for i,(k,r) in enumerate(x['workers'].items()):
 w('INC'+str(i),[len(r['stores'])]+[a for k,v in r['stores'].items() for a in [res[k],round(v*2)]])
w('WORKERS',[a for i,(k,r) in enumerate(x['workers'].items()) for a in [string(tr(k)),*worker_unlock[i],'INC'+str(i)]])
w('WEIGHTS',[round(x['weight'].get(k,1)*10) for k in resources])
weapons=[]
for i,(k,v) in enumerate(x['weapons'].items()):
 cost=v.get('cost',{});ammo=next(iter(cost),None)
 weapons.extend([string(tr(k)) if k!='fists' else string('КУЛАКИ'),res.get(k,-1),-1 if v['damage']=='stun' else v['damage'],int(v['cooldown']*10),res[ammo] if ammo else -1,1 if v['type']=='melee' else 0])
w('WEAPONS',weapons);constants.append('NWEAP = 12.')
# Every scene gets an ID; all text, loot, choices and effects remain disk resident.
scenes=[]; ids={}; events={}
for group in ['encounters','setpieces','executioner','room','outside','global']:
 entries=x[group].items() if isinstance(x[group],dict) else enumerate(x[group])
 for key,e in entries:
  key=str(key);events[(group,key)]=e
  for name,s in e['scenes'].items():
   ids[(group,key,name)]=len(scenes); scenes.append((group,key,name,e,s))
for (group,key),e in events.items():constants.append(f'EV_{ident(group)}_{ident(key)} = {ids[(group,key,"start")]}.')
ui=json.loads((SRC/'ui.json').read_text())
disk_ui={'RESCUE_BODY'}
for kind in ['DEFEAT','HUNGER','THIRST']:
 disk_ui.update({kind+'_TITLE',kind+'_BODY'})
 key=kind.lower();ids[('native',key,'start')]=len(scenes)
 constants.append(f'EV_NATIVE_{kind} = {len(scenes)}.')
 scenes.append(('native',key,'start',{'title':ui[kind+'_TITLE']},
                {'text':[ui[kind+'_BODY']+' '+ui['RESCUE_BODY']], 'buttons':{}}))

# Full-screen pages use the scene window too, keeping long credits off CPU RAM.
def centered_page(rows):
 lines=['']*24
 for row,text in rows:
  for offset,line in enumerate(text.split('\n')):
   if len(line)>78 or row+offset>=24:raise ValueError(('page overflow',row,line))
   lines[row+offset]=(' '*((80-len(line))//2)+line) if line else ''
 return '\n'.join(lines).rstrip()
page_texts={
 'SPLASH':centered_page([(4,ui['SPLASH']),(20,ui['SPLASH_KEYS'])]),
 'END':centered_page([(8,ui['END']),(18,ui['END2']),(20,ui['CREDITS'])]),
 'BEACON_END':centered_page([(5,ui['BEACON_END']),(18,ui['END2']),(20,ui['CREDITS'])]),
}
for kind,body in page_texts.items():
 if kind!='SPLASH':body+='\n\n\n  '+ui['ENDKEYS']
 constants.append(f'EV_NATIVE_{kind} = {len(scenes)}.')
 scenes.append(('native',kind.lower(),'start',{'title':''},{'page':body,'buttons':{}}))
disk_ui.update({'SPLASH','SPLASH_KEYS','END','BEACON_END','END2','CREDITS','ENDKEYS'})

# Effects are explicit semantic translations of JS hooks, never evaluated in the port.
def effects(g,k,n,v,hook='onLoad'):
 js=v.get(hook,{}).get('js',''); out=[]
 def add(op,a=0,b=0):out.extend([op,a,b])
 if 'World.clearDungeon' in js:add(1)
 if 'World.markVisited' in js:add(2)
 if 'World.useOutpost' in js:add(3)
 if 'World.setWater' in js:add(3)
 if 'World.drawRoad' in js:add(4)
 for f in flags:
  if re.search(r'World.state.'+f+r'\s*=\s*true',js) or (f=='cityCleared' and "game.cityCleared" in js):add(5,flags.index(f)*2,1)
 for p in re.findall(r"addPerk\('([^']+)'\)",js):add(6,perks.index(p)*2)
 if 'World.setHp' in js:add(7)
 if 'World.applyMap' in js or 'World.uncoverMap' in js:
  for _ in range(3 if 'i < 3' in js else 1):add(8)
 for m in re.finditer(r"\$SM.add\('stores(?:\.([^']+)|\[\"([^\"]+)\"\])',\s*(\d+)\)",js):add(9,res[m[1] or m[2]],int(m[3]))
 if g=='room' and k=='2' and hook=='onLoad' and n!='start':add(10,res[n])
 if g=='room' and k=='4' and n=='build':add(11)
 if g=='room' and k in ['5','6'] and n!='start':add(12,res['wood' if k=='5' else 'fur'],100 if '100' in n else 500)
 if g=='outside' and js:
  if k=='0':add(13)
  if k=='1':add(14)
  if 'killVillagers' in js:
   add(15,{'2':0,'3':5 if n=='healed' else 80,'4':10,'5':40}.get(k,10), (2 if n=='healed' else 10) if k=='3' else 1)
 if g=='global' and js:add(16,1 if n=='hang' else 0)
 for a,b in v.get('reward',{}).items():add(9,res[a],b)
 return out

def condition(v):
 js=v.get('available',{}).get('js','')
 if not js:return [0,0]
 if 'stores.compass' in js:return [1,res['compass']]
 if 'World.seenAll' in js:return [5,0]
 for p in perks:
  if "'"+p+"'" in js:return [2,perks.index(p)*2]
 if '&&' in js:return [4,0]
 for f in flags:
  if 'World.state.'+f in js:return [3,flags.index(f)*2]
 raise ValueError(js)

class Block:
 def __init__(self):self.b=bytearray(32)
 def words(self,vals):
  if len(self.b)%2:self.b.append(0)
  p=SCENE_BASE+len(self.b);self.b+=struct.pack('<'+'H'*len(vals),*(int(a)&65535 for a in vals));return p
 def text(self,s):
  p=SCENE_BASE+len(self.b);self.b+=koi(s)+b'\0';return p
 def cost(self,c):return self.words(pairs(c))
 def eff(self,e):return self.words([len(e)//3]+e)

def nexts(b,g,k,v,current):
 if 'nextEvent' in v:
  return b.words([1,100,ids[('executioner',v['nextEvent'],'start')]])
 nxt=v.get('nextScene',None)
 if nxt is None:return b.words([1,100,current])
 if isinstance(nxt,str):nxt={1:nxt}
 vals=[len(nxt)]
 for chance,n in sorted(nxt.items(),key=lambda kv:float(kv[0])):
  target=65535 if n=='end' else ids[(g,k,n)]
  vals.extend([round(float(chance)*100),target])
 return b.words(vals)

bank=bytearray();directory=[];meta=[]
for sid,(g,k,n,e,s) in enumerate(scenes):
 b=Block();title=b.text(e['title'] if g=='native' else tr(e['title']))
 paragraphs=s.get('text',[]) or [s.get('notification','')]
 body=s['page'] if 'page' in s else ('\n'+18*' ').join(textwrap.wrap(' '.join(paragraphs),44)) if g=='native' else (
       '\n'.join('\n'.join(textwrap.wrap(tr(t),76)) for t in paragraphs if t))
 if 'page' not in s and len(body.splitlines())>4:raise ValueError(('text exceeds 4 rows above choices and notification log',g,k,n))
 txt=b.text(body)
 compact=txt if g=='native' and 'page' not in s else 0
 if s.get('health',0):
  lines=textwrap.wrap(' '.join(body.split()),44)
  if len(lines)>4:raise ValueError(('encounter exceeds compact dialog',g,k,n))
  compact=b.text(('\n'+18*' ').join(lines))
 loot=[]
 for r,v in s.get('loot',{}).items():loot += [res[r],v['min'],v['max'],round(v['chance']*100)]
 lp=b.words([len(loot)//4]+loot)
 eff=b.eff(effects(g,k,n,s))
 buttons=[]
 bs=s.get('buttons',{'leave':{'text':'leave','nextScene':'end'}})
 for bk,bv in bs.items():
  name=b.text(tr(bv['text']));cost=b.cost(bv.get('cost',{}));ef=b.eff(effects(g,k,n,bv,'onChoose'))
  nxt=nexts(b,g,k,bv,sid)
  buttons += [name,cost,ef,nxt,*condition(bv)]
 bp=b.words([len(buttons)//6]+buttons)
 hp=int(s.get('health',0));dmg=int(s.get('damage',0));delay=round(s.get('attackDelay',1)*10);hit=round(s.get('hit',.8)*100)
 special=0
 if 'atHealth' in s:special=1
 if 'specials' in s:
  js=str(s['specials']);special=6 if 'meditation' in js else 2 if 'shield' in js else 3 if 'energised' in js else 4
 if 'explosion' in s:special=5
 # 16 words: title text hp damage delay hit loot effects buttons special group special-delay explosion compact-text reserved...
 struct.pack_into('<16H',b.b,0,title,txt,hp,dmg,delay,hit,lp,eff,bp,special,0 if g in ['room','outside','global'] else 1,round(s.get("specials",[{}])[0].get("delay",0)*10),int(s.get("explosion",0)),compact,0,0)
 size=(len(b.b)+511)//512
 if size>2:raise ValueError(('scene exceeds window',g,k,n,len(b.b)))
 directory += [1+len(bank)//512,size]
 bank+=b.b+bytes(size*512-len(b.b))
 meta.append({'id':sid,'group':g,'event':k,'scene':n,'bytes':len(b.b),'block':directory[-2],'sectors':size})
# Pair the executable with this exact scene bank before taking over video/input.
header=b'ADRUKNC\0'+struct.pack('<4H',1,SCENE_BASE,len(scenes),len(bank)//512)+hashlib.sha256(bank).digest()
w('DATA_HEADER',struct.unpack('<24H',header))
constants.append('HEADER_WORDS = 24.')
bank=header+bytes(512-len(header))+bank
constants.append(f'SCENE_BLOCKS = {len(bank)//512}.')
w('SCENE_DIR',directory)
# Random village event availability is native and index based.
w('ROOM_EVENTS',[ids[('room',str(i),'start')] for i in range(10)])
w('OUT_EVENTS',[ids[('outside',str(i),'start')] for i in range(6)])
w('ENCOUNTERS',[ids[('encounters',str(i),'start')] for i in range(11)])
# ASCII map symbols are replaced with readable KOI-7 single-letter mnemonics.
landmarks=[('ironmine',1,5,5,'Ж'),('coalmine',1,10,10,'У'),('sulphurmine',1,20,20,'С'),('house',10,1,45,'Д'),('cave',5,3,10,'П'),('town',10,10,20,'Г'),('city',20,20,45,'Р'),('ship',1,28,28,'К'),('borehole',10,15,45,'Б'),('battlefield',5,18,45,'О'),('swamp',1,15,45,'М'),('executioner-intro',1,28,28,'Х')]
w('LANDMARKS',[a for i,(k,num,mn,mx,ch) in enumerate(landmarks) for a in [num,mn,mx,ids[('executioner' if k.startswith('executioner') else 'setpieces',k,'start')],koi(ch)[0]]])
constants.append(f'NLAND = {len(landmarks)}.')
# UI strings are all Russian; identifiers and developer documentation are English.
ui={label:s for label,s in ui.items() if label not in disk_ui}
for label,s in ui.items():string(s)
for s,label in strings.items():
 for name,txt in ui.items():
  if txt==s:data.append('S_'+name+':')
 data.append(label+':')
 encoded=koi(s)+b'\0'
 for i in range(0,len(encoded),24):data.append(' .BYTE '+','.join(str(v)+'.' for v in encoded[i:i+24]))
data.append(' .EVEN')
(OUT/'constants.mac').write_text('\n'.join(constants)+'\n')
(OUT/'data.mac').write_text('\n'.join(data)+'\n')
(OUT/'scenes.bin').write_bytes(bank)
(OUT/'catalog.json').write_text(json.dumps({'resources':res,'buildings':bld,'flags':flags,'perks':perks,'scenes':meta},ensure_ascii=False,indent=2)+'\n')
(OUT/'missing-translations.json').write_text(json.dumps(sorted(missing),ensure_ascii=False,indent=2))
if missing:raise SystemExit(f'Missing Russian translations: {sorted(missing)}')
print(f'{len(resources)} resources, {len(recipes)} recipes, {len(scenes)} scenes, {len(bank)} bank bytes; {len(missing)} missing translations')
