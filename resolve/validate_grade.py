"""Apply one DRX grade to a group post-clip graph in a DISPOSABLE project and export a still.

Usage: python3 validate_grade.py GRADE.drx TEST_CLIP OUT_DIR [START_FRAME]
Creates or reuses a project named "Isolated grade validation". Save and export valuable
work first: a malformed DRX can take Resolve down.
"""
import sys
import time
from pathlib import Path

from _config import resolve_app

if len(sys.argv) < 4:
    raise SystemExit(__doc__)
grade, clip_path, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
assert grade.is_file()
out.mkdir(parents=True, exist_ok=True)
r = resolve_app(); pm = r.GetProjectManager(); name = 'Isolated grade validation'
p = pm.LoadProject(name) if name in pm.GetProjectListInCurrentFolder() else pm.CreateProject(name)
assert p
p.SetSetting('timelineFrameRate', '23.976')
p.SetSetting('colorScienceMode', 'davinciYRGB')
p.SetSetting('colorSpaceTimeline', 'Rec.709 Gamma 2.4')
mp = p.GetMediaPool(); t = p.GetCurrentTimeline()
if not t:
    media = mp.ImportMedia([str(clip_path)])[0]
    t = mp.CreateEmptyTimeline('Grade test')
    mp.AppendToTimeline([{'mediaPoolItem': media, 'startFrame': start, 'endFrame': start + 72,
                          'mediaType': 1, 'trackIndex': 1, 'recordFrame': t.GetStartFrame()}])
clip = t.GetItemListInTrack('video', 1)[0]
pm.SaveProject()
groups = p.GetColorGroupsList()
group = groups[0] if groups else p.AddColorGroup('Look validation')
assert clip.AssignToColorGroup(group)
graph = group.GetPostClipNodeGraph()
print('APPLY', grade, flush=True)
print('RESULT', graph.ApplyGradeFromDRX(str(grade), 0), flush=True)
time.sleep(1)
graph = group.GetPostClipNodeGraph(); count = graph.GetNumNodes()
print('NODES', count, 'TOOLS', [graph.GetToolsInNode(i) for i in range(1, (count or 0) + 1)], flush=True)
pm.SaveProject()
r.OpenPage('color'); t.SetCurrentTimecode('01:00:01:00'); time.sleep(1)
print('STILL', p.ExportCurrentFrameAsStill(str(out / (grade.stem + '.png'))), flush=True)
