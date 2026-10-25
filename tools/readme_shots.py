#!/usr/bin/env python3
"""Capture spoiler-free native emulator screens for the Russian player README."""
from PIL import Image
from test_support import Scenario, ROOT, CAT


def frame(s, name):
    for routine in ['DRAW','TAB_UPDATE','BARS_DRAW','FLUSH','TAB_PIXELS','SV_FRAME',
                    'FOCUS_ERASE','BARS_DRAW','FOCUS_DRAW']:
        s.call(routine)
    return s.snap(name).shot(name)


def main():
    output=ROOT/'readme';output.mkdir(exist_ok=True)
    # Let the native opening develop through physical keys and real game ticks.
    base=Scenario('readme-base').key('ENTER').run(4100).key('2').key('ENTER').key('1')
    frame(base,'base');base.execute()
    # A prepared early expedition, with no late-game unlocks. Fog is opened by
    # the native reveal routine; the documented view is captured unretouched.
    travel=Scenario('readme-travel').stock('compass',1).stock('rucksack',1).stock('waterskin',1).stock('l armour',1)
    travel.stock('cured meat',15,True).stock('torch',2,True).stock('bone spear',1,True).call('EMBARK')
    travel.word('REV_RADIUS',8).call('UNCOVER_MAP').run(800)
    frame(travel,'travel')
    # Show a second near-field enemy, with actual enemy/player cooldown timers.
    creature=next(s['id'] for s in CAT['scenes'] if s['group']=='encounters' and s['event']=='3')
    travel.call('START_EVENT',creature).key('ENTER',50).word('SEED',2).call('ATTACK',1)
    frame(travel,'battle');result=travel.execute()
    for name,scenario in [('base',base),('travel',travel),('battle',travel)]:
        image=Image.open(ROOT/f'tmp/{scenario.name}-{name}.bmp').convert('RGB')
        image.save(output/(name+'.png'))
        print(output/(name+'.png'))
    assert result['travel'].word('BAG_WEIGHT') <= result['travel'].word('CAPACITY')
    assert result['battle'].word('TR_MODE') == 0
    overlay=(ROOT/'tmp/readme-travel-battle.overlay-plane').read_bytes()
    assert not any(overlay[216*80:217*80]), 'unfinished modal redraw in screenshot'
    for name,snap in result.items():
        if any(word in snap.screen() for word in ['КОРАБЛЬ','ЛИНКОР','ФАБРИКАТОР']):
            raise AssertionError('late-game spoiler in '+name)


if __name__=='__main__':main()
