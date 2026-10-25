"""Shrink provably in-range PDP-11 branches using the assembler's layout.

Start fully relaxed, then only shrink instructions. With this program's even
alignment, distances cannot grow. Numeric local labels remain scoped by the
preceding global label. Macro expansion addresses come from the real listing.
"""
import re
INVERSE={'BEQ':'BNE','BNE':'BEQ','BGT':'BLE','BLE':'BGT','BGE':'BLT','BLT':'BGE','BHI':'BLOS','BLOS':'BHI','BHIS':'BLO','BLO':'BHIS','BCC':'BCS','BCS':'BCC','BPL':'BMI','BMI':'BPL','BVC':'BVS','BVS':'BVC'}
class Branches:
 def __init__(self,modules):
  self.lines=[];self.labels={};self.branches={};self.short=set();scope=''
  for path,text in modules:
   native=path.startswith('src/') and path not in ['src/defs.mac','src/tail.mac']
   if native:text=re.sub(r'(?m)^(\s*(?:[\w$]+:\s*)?)SOB\s+([^,]+),([^;\n]+)',r'\1DEC \2\n BNE \3',text)
   for line in text.splitlines():
    i=len(self.lines);self.lines.append(line)
    m=re.match(r'\s*([\w$]+):',line)
    if m:
     label=m[1]
     if label.endswith('$'):label=(scope,int(label[:-1]))
     else:scope=label
     self.labels[label]=i
    if not native:continue
    m=re.match(r'(\s*(?:[\w$]+:\s*)?)(B[A-Z]+)\s+([\w$]+)\s*(?:;.*)?$',line)
    if m and (m[2]=='BR' or m[2] in INVERSE):
     target=(scope,int(m[3][:-1])) if m[3].endswith('$') else m[3]
     self.branches[i]=(m[1],m[2],m[3],target)
 def render(self):
  out=[];self.rows={}
  for i,line in enumerate(self.lines):
   self.rows[i]=len(out)+1
   if i in self.branches and i not in self.short:
    prefix,op,target,_=self.branches[i]
    out.extend([prefix+'JMP '+target] if op=='BR' else [prefix+INVERSE[op]+' .+6',' JMP '+target])
   else:out.append(line)
  return '\n'.join(out)+'\n'
 def shrink(self,listing):
  addresses={}
  for line in listing.splitlines():
   m=re.match(r'\s*(\d+)\s+([0-7]{6})\s',line)
   if m:addresses.setdefault(int(m[1]),int(m[2],8))
  # Bare labels inherit the address of the next assembled source line.
  following=None
  for row in range(max(self.rows.values())+2,0,-1):
   if row in addresses:following=addresses[row]
   elif following is not None:addresses[row]=following
  before=len(self.short)
  for i,(_,_,_,label) in self.branches.items():
   target=self.labels.get(label)
   if target is None:continue
   # A macro invocation has no outer-line address; its expansion uses local
   # listing line numbers. Keep jumps to such targets long rather than guessing.
   statement=self.lines[target].split(':',1)[-1].strip()
   nextline=target+1
   while not statement and nextline<len(self.lines):
    statement=self.lines[nextline].split(';',1)[0].strip();nextline+=1
   if statement.startswith('.'):continue
   start=addresses.get(self.rows[i]);end=addresses.get(self.rows[target])
   if start is not None and end is not None and -256<=end-start-2<=254:self.short.add(i)
  return len(self.short)-before
