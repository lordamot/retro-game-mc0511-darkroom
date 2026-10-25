"""Native terrain/distance encounter pools and live compass bearings."""
import json
from collections import Counter
from test_support import Scenario, ROOT, CAT


def verify_encounters(check):
    scenes = {int(s['event']): s['id'] for s in CAT['scenes'] if s['group'] == 'encounters'}
    reverse = {value: key for key, value in scenes.items()}
    # Independently transcribed from the pinned encounter availability rules:
    # forest, field, barrens, with inclusive tier boundaries at 10 and 20.
    pools = [{0: {0}, 1: {2, 3}, 2: {1}},
             {0: {5}, 1: {7}, 2: {4, 6}},
             {0: {8}, 1: {10}, 2: {9}}]
    report = {}; observed = set()
    for distance in [10, 11, 20, 21]:
        tier = 0 if distance <= 10 else 1 if distance <= 20 else 2
        s = Scenario('encounter-pools-' + str(distance)).word('AWAY', 1).word('MAX_HP', 100)
        for tile in range(3):
            for seed in range(1, 65):
                s.word('TR_MODE', 0).word('ENEMY_HP', 0).word('POS_X', 29 + distance).word('POS_Y', 30)
                s.word('HP', 100).word('WATER', 100).stock('cured meat', 100, True).word('LAST_FIGHT', 3)
                s.word('TAB', 10).word('ACTIVE_SCENE', 0).word('SCENE_ID', 65535).word('SEED', seed)
                s.byte('WORLD_MAP', tile, 30 * 61 + 30 + distance).call('MOVE', 3).snap(f'{tile}-{seed}')
        result = s.execute()
        for tile in range(3):
            counts = Counter()
            for seed in range(1, 65):
                snap = result[f'{tile}-{seed}']; scene = snap.word('SCENE_ID')
                check(snap.word('CURRENT_TILE') == tile and snap.word('POS_X') == 30 + distance, 'native movement uses the intended terrain/distance')
                if scene == 65535:
                    check(snap.word('TR_MODE') == 0, 'a failed encounter roll leaves travel active')
                    continue
                enemy = reverse.get(scene)
                check(enemy in pools[tier][tile], f'distance {distance}, terrain {tile}: only eligible monsters spawn')
                check(snap.word('TR_MODE') == 1 and snap.word('ENEMY_HP') == snap.word('SCENE_BASE', 4) and snap.word('ENEMY_CLOCK') == snap.word('SCENE_BASE', 8), 'spawn loads the actual monster health and attack delay before acknowledgement')
                counts[enemy] += 1; observed.add(enemy)
            check(set(counts) == pools[tier][tile], f'distance {distance}, terrain {tile}: every eligible monster is reachable')
            report[f'{distance}/{tile}'] = dict(counts)
    # Continue one native PRNG stream too, instead of resetting it per roll.
    stream = Scenario('encounter-field-stream').word('AWAY',1).word('MAX_HP',100).word('SEED',1234).word('POS_X',33).word('POS_Y',30)
    stream.byte('WORLD_MAP',1,30*61+33).byte('WORLD_MAP',1,30*61+34)
    for i in range(64):
        stream.word('TR_MODE',0).word('ENEMY_HP',0).word('HP',100).word('WATER',100).stock('cured meat',100,True)
        stream.word('LAST_FIGHT',3).word('TAB',10).word('ACTIVE_SCENE',0).word('SCENE_ID',65535).call('MOVE',3 if i%2==0 else 2).snap(str(i))
    counts=Counter()
    for snap in stream.execute().values():
        sid=snap.word('SCENE_ID')
        if sid != 65535:
            check(reverse.get(sid) in {2,3}, 'continuous near-field random stream stays in its enemy pool')
            counts[reverse[sid]]+=1
    check(set(counts)=={2,3}, 'continuous random stream generates both birds and two-headed creatures')
    report['continuous-field']=dict(counts)
    check(observed == set(range(11)), 'all eleven roaming enemies are generated, not just birds')
    (ROOT / 'tmp/encounter-pools.json').write_text(json.dumps(report, indent=2) + '\n')
    print('all eleven monsters, three terrains, tier boundaries 10/11/20/21 and native enemy stats: OK', flush=True)


def verify_compass(check):
    from PIL import Image
    s = Scenario('travel-compass').stock('compass', 1).stock('cured meat', 5, True).call('EMBARK').snap('before')
    # Remove the generated target only in this disposable scenario. Every test
    # then places it at a known offset, including outside the visible viewport.
    s.lines += [f'callcpu {s.s["SCREEN_CLEAR"]:o}']
    # MAP_INIT always places one ship; use a native map snapshot from the same
    # deterministic initial seed to locate it without borrowing old addresses.
    initial = Scenario('compass-map-source').snap('map').execute()['map']
    world = initial.data[initial.s['WORLD_MAP']:initial.s['WORLD_MAP'] + 3721]
    for offset, tile in enumerate(world):
        if tile == 10: s.byte('WORLD_MAP', 0, offset)
    cases = [(-12,-12,'СЕВЕРО-ЗАПАД'),(0,-12,'СЕВЕР'),(12,-12,'СЕВЕРО-ВОСТОК'),
             (-12,0,'ЗАПАД'),(0,0,'ЗДЕСЬ'),(12,0,'ВОСТОК'),
             (-12,12,'ЮГО-ЗАПАД'),(0,12,'ЮГ'),(12,12,'ЮГО-ВОСТОК'),
             (20,3,'ВОСТОК'),(3,20,'ЮГ'),(-20,-3,'ЗАПАД'),(-3,-20,'СЕВЕР')]
    for i, (dx,dy,direction) in enumerate(cases):
        offset = (30+dy)*61+30+dx
        s.byte('WORLD_MAP',10,offset).call('DRAW').call('FLUSH').snap(str(i))
        if i in [0,4,10]:s.shot(str(i))
        s.byte('WORLD_MAP',0,offset)
    s.call('DRAW').call('FLUSH').snap('absent').shot('absent')
    # The same target must point differently as the player walks around it.
    s.byte('WORLD_MAP',10,30*61+40).word('POS_X',45).call('DRAW').call('FLUSH').snap('moved')
    s.key('0',50).call('DRAW').call('FLUSH').snap('bag')
    result = s.execute()
    check('КОМПАС' not in result['bag'].screen().splitlines()[6], 'leaving the map removes compass text')
    for i,(_,_,direction) in enumerate(cases):
        lines=result[str(i)].screen().splitlines()
        check(lines[6][48:].strip()=='КОМПАС' and lines[8][48:].strip()==direction, 'live compass points '+direction)
        off=s.s['MAP_SEEN']
        check(result[str(i)].data[off:off+3721]==result['before'].data[off:off+3721], 'compass does not reveal hidden map cells')
    check('КОМПАС' not in result['absent'].screen().splitlines()[6], 'missing target clears the old compass display')
    check(result['moved'].screen().splitlines()[8][48:].strip()=='ЗАПАД', 'bearing is relative to the current traveler, not home')
    for name in ['0','4','10','absent']:
        Image.open(ROOT/f'tmp/travel-compass-{name}.bmp').save(ROOT/f'tmp/travel-compass-{name}.png')
    print('live compass: eight directions, axis thresholds, at-target, absent-target and unchanged fog: OK', flush=True)


if __name__ == '__main__':
    count=0
    def check(ok,message):
        global count
        count+=1
        if not ok:raise AssertionError(message)
    verify_compass(check)
    verify_encounters(check)
    print(f'PASS: {count} exploration checks')
