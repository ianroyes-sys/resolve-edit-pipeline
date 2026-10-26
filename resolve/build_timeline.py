"""Build a NEW editable Resolve project from a reviewed edit plan. Never edits an existing project.

Usage: python3 build_timeline.py edit-plan.json card-metadata.json CLIP_DIR OUT_DIR

- Imports every clip into "01 - Camera originals", colors selects green and the rest yellow
  (unused is an editorial choice, not a rejection), and marks each planned range.
- Appends the planned shots in order on V1 with a blue marker per shot.
- Optional plan["sync_audio_clip"]: puts that clip's own audio under its picture on A1.
- Exports a .drp and writes timeline-build.json (frame positions used by the sound and QC steps).
Run pipeline/verify_edit_plan.py first.
"""
import json
import sys
from pathlib import Path

from _config import resolve_app

if len(sys.argv) < 5:
    raise SystemExit(__doc__)
plan = json.loads(Path(sys.argv[1]).read_text())
meta = {c['clip']: c for c in json.loads(Path(sys.argv[2]).read_text())['clips']}
clip_dir, out = Path(sys.argv[3]), Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
name = plan['project']
r = resolve_app(); pm = r.GetProjectManager()
if name in pm.GetProjectListInCurrentFolder():
    raise SystemExit('Project already exists; refusing to rebuild over it')
p = pm.CreateProject(name); assert p, 'Cannot create project'
results = {}
for key, val in plan.get('project_settings', {}).items():
    results[key] = {'requested': val, 'ok': p.SetSetting(key, val), 'actual': p.GetSetting(key)}
print(json.dumps(results, indent=2), flush=True)

mp = p.GetMediaPool(); root = mp.GetRootFolder()
mp.SetCurrentFolder(mp.AddSubFolder(root, '01 - Camera originals'))
paths = [str(clip_dir / (c + '.MP4')) for c in meta]
missing = [x for x in paths if not Path(x).exists()]
assert not missing, f'Missing media: {missing[:5]}'
items = mp.ImportMedia(paths)
assert len(items) == len(paths), f'Imported {len(items)} / {len(paths)}'
by_name = {Path(i.GetClipProperty('File Path')).stem: i for i in items}
selected = {s['clip'] for s in plan['shots']}
for clip, item in by_name.items():
    if clip in selected:
        item.SetClipColor('Green')
        for shot in [s for s in plan['shots'] if s['clip'] == clip]:
            fps = meta[clip]['fps']
            item.AddMarker(round(shot['in'] * fps), 'Green', shot['role'], shot.get('review', 'Planned range'),
                           round(shot['duration'] * fps))
    else:
        item.SetClipColor('Yellow')
        item.AddMarker(0, 'Yellow', 'Alternate / unused', 'Retained intact; not a technical rejection.', 1)

mp.SetCurrentFolder(mp.AddSubFolder(root, '02 - Timelines'))
t = mp.CreateEmptyTimeline(plan.get('timeline', name + ' - assembly')); assert t
t.SetStartTimecode('01:00:00:00')
t.SetTrackName('video', 1, 'Story picture')
labels = plan.get('audio_tracks', ['Dialogue', 'Natural sound', 'Music', 'SFX'])
while t.GetTrackCount('audio') < len(labels):
    t.AddTrack('audio', 'stereo')
for index, label in enumerate(labels, 1):
    t.SetTrackName('audio', index, label)

cursor = t.GetStartFrame(); shots = []
for shot in plan['shots']:
    clip = shot['clip']; fps = meta[clip]['fps']
    start = round(shot['in'] * fps); frames = round(shot['duration'] * fps)
    assert start + frames <= meta[clip]['frames'], f'Range exceeds source: {clip}'
    placed = mp.AppendToTimeline([{'mediaPoolItem': by_name[clip], 'startFrame': start, 'endFrame': start + frames - 1,
                                   'mediaType': 1, 'trackIndex': 1, 'recordFrame': cursor}])
    assert placed, f'Append failed: {clip}'
    item = placed[0]
    t.AddMarker(item.GetStart() - t.GetStartFrame(), 'Blue', shot['role'], f'{clip}: {shot["in"]:.2f}s', 1)
    shots.append({**shot, 'timeline_start': item.GetStart(), 'timeline_duration_frames': item.GetDuration(),
                  'source_in_frame': start, 'source_frames': frames})
    cursor = item.GetEnd()
    print(clip, item.GetStart(), item.GetDuration(), flush=True)
assert len(t.GetItemListInTrack('video', 1)) == len(plan['shots'])

sync = plan.get('sync_audio_clip')
if sync:
    s = next(x for x in shots if x['clip'] == sync)
    assert mp.AppendToTimeline([{'mediaPoolItem': by_name[sync], 'startFrame': s['source_in_frame'],
                                 'endFrame': s['source_in_frame'] + s['source_frames'] - 1, 'mediaType': 2,
                                 'trackIndex': 1, 'recordFrame': s['timeline_start']}])
pm.SaveProject()
drp = out / (name.replace('/', '-') + '.drp')
assert pm.ExportProject(name, str(drp), True)
(out / 'timeline-build.json').write_text(json.dumps({'project': name, 'fps': plan['fps'], 'settings': results,
    'start_frame': t.GetStartFrame(), 'end_frame': t.GetEndFrame(), 'shots': shots}, indent=2))
r.OpenPage('edit')
print('SAVED', name, 'duration', (t.GetEndFrame() - t.GetStartFrame()) / plan['fps'], flush=True)
