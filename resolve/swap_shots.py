"""Swap shots in an existing timeline in place: same record position, same length.

Usage: python3 swap_shots.py swap.json
swap.json: {"timeline": "Recap v1", "source_frames": 36, "expected_duration": 90,
            "swaps": {"OLD_CLIP": {"new": "NEW_CLIP", "source_in": 17, "why": "..."}}}
Asserts each old clip has the expected duration and linked audio before deleting it.
Export a .drt backup of the timeline first.
"""
import json
import sys
from pathlib import Path

from _config import resolve_app

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
cfg = json.loads(Path(sys.argv[1]).read_text())
r = resolve_app(); p = r.GetProjectManager().GetCurrentProject(); mp = p.GetMediaPool()
tl = next(p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1)
          if p.GetTimelineByIndex(i).GetName() == cfg['timeline'])
p.SetCurrentTimeline(tl)
items = {it.GetName().split('.')[0]: it for it in mp.GetRootFolder().GetClipList()}
v1 = {x.GetName().split('.')[0]: x for x in tl.GetItemListInTrack('video', 1)}
a1 = {x.GetName().split('.')[0]: x for x in tl.GetItemListInTrack('audio', 1)}
for old, s in cfg['swaps'].items():
    v, a = v1[old], a1[old]; rec, dur = v.GetStart(), v.GetDuration()
    assert dur == cfg['expected_duration'] and a.GetStart() == rec, (old, dur)
    assert tl.DeleteClips([v, a], False), old
    got = mp.AppendToTimeline([{'mediaPoolItem': items[s['new']], 'startFrame': s['source_in'],
                                'endFrame': s['source_in'] + cfg['source_frames'], 'trackIndex': 1, 'recordFrame': rec}])
    print(old, '->', s['new'], 'rec', rec, 'ok' if got else 'FAILED', '|', s.get('why', ''))
r.GetProjectManager().SaveProject()
