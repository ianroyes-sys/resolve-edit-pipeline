"""Render the current timeline of a project to an H.264 review movie and export an editable .drp.

Usage: python3 render_review.py "Project name" OUT_DIR OUTPUT_BASENAME [WIDTH HEIGHT FPS]
Waits for the render and fails unless Resolve reports the job Complete.
Inspect the rendered file afterwards (pipeline/qc_render.py); API success is not a review.
"""
import json
import sys
import time
from pathlib import Path

from _config import resolve_app

if len(sys.argv) < 4:
    raise SystemExit(__doc__)
name, out, base = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
w, h, fps = (int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (1920, 1080, 23.976)
out.mkdir(parents=True, exist_ok=True)
pm = resolve_app().GetProjectManager()
p = pm.LoadProject(name); assert p, f'No project named {name}'
assert p.SetCurrentRenderMode(1)
assert p.SetCurrentRenderFormatAndCodec('mp4', 'H264')
settings = {'SelectAllFrames': True, 'TargetDir': str(out), 'CustomName': base, 'ExportVideo': True,
            'ExportAudio': True, 'FormatWidth': w, 'FormatHeight': h, 'FrameRate': fps, 'VideoQuality': 20000,
            'AudioCodec': 'aac', 'AudioSampleRate': 48000, 'NetworkOptimization': True,
            'ColorSpaceTag': 'Rec.709', 'GammaTag': 'Gamma 2.4'}
assert p.SetRenderSettings(settings)
job = p.AddRenderJob(); assert job
pm.SaveProject()
assert pm.ExportProject(p.GetName(), str(out / (base + '-EDITABLE.drp')), True)
assert p.StartRendering([job])
while p.IsRenderingInProgress():
    print(json.dumps(p.GetRenderJobStatus(job)), flush=True)
    time.sleep(10)
status = p.GetRenderJobStatus(job)
(out / (base + '-render-status.json')).write_text(json.dumps({'job': job, 'settings': settings, 'status': status}, indent=2))
print(json.dumps(status), flush=True)
if status.get('JobStatus') != 'Complete':
    raise SystemExit('Render did not complete')
