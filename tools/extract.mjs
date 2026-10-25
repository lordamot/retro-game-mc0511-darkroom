#!/usr/bin/env node
// Evaluate data declarations only, in an isolated context; never initialize the browser game.
import fs from 'node:fs';
import vm from 'node:vm';
const root = new URL('../orig/adarkroom/', import.meta.url).pathname;
let translations = {};
const tr = s => s;
tr.setTranslation = t => translations = t;
const ctx = vm.createContext({_: tr, AudioLibrary: {}, Events: {}, Engine: {}, window: {},
  $SM: {get: () => 0}, console, setTimeout: () => {}, clearTimeout: () => {}});
for (const f of ['lang/ru/strings.js','script/room.js','script/outside.js','script/world.js','script/path.js','script/fabricator.js','script/events.js','script/events/encounters.js','script/events/setpieces.js','script/events/executioner.js','script/events/room.js','script/events/outside.js','script/events/global.js']) {
  vm.runInContext(fs.readFileSync(root+f,'utf8'),ctx,{filename:f});
}
ctx.Fabricator = vm.runInContext("Fabricator",ctx);
const recipes = {};
for(const [group, entries] of Object.entries({craft:ctx.Room.Craftables,trade:ctx.Room.TradeGoods,fabricate:ctx.Fabricator.Craftables})){
  recipes[group] = Object.entries(entries).map(([key,r])=>{
    ctx.$SM.get=()=>0; const cost=r.cost();
    ctx.$SM.get=()=>1; const next=r.cost();
    return {key,type:r.type,maximum:r.maximum||0,quantity:r.quantity||1,cost,increment:Object.fromEntries(Object.keys(cost).map(k=>[k,next[k]-cost[k]])),message:r.buildMsg||'',blueprint:!!r.blueprintRequired};
  });
}
const data={recipes,workers:ctx.Outside._INCOME,drops:ctx.Outside.TrapDrops,weapons:ctx.World.Weapons,weight:ctx.Path.Weight,
  encounters:ctx.Events.Encounters,setpieces:ctx.Events.Setpieces,executioner:ctx.Events.Executioner,room:ctx.Events.Room,outside:ctx.Events.Outside,global:ctx.Events.Global,translations};
// Retain function source for explicit, audited target-side effect mapping.
fs.writeFileSync('src/res/upstream.json',JSON.stringify(data,(k,v)=>typeof v==='function'?{js:String(v)}:v,2)+'\n');
console.log(Object.keys(ctx.Events));
console.log('extracted recipes and events');
