"""Measure finished reference edits: 16-frame sheet, resolution, fps and scene-change pacing.

Usage: python3 style_analysis.py reference-candidates.json OUT_DIR SUBSTRING [SUBSTRING ...]
Only references whose path contains one of the substrings are analysed.
Scene changes at threshold 0.30 are estimates, not exact edit points.
"""
import concurrent.futures
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from _config import FFMPEG


def process(item):
    idx, p, out = item
    probe = subprocess.run([FFMPEG, '-hide_banner', '-i', p, '-t', '0', '-f', 'null', '-'], capture_output=True, text=True)
    h, m, s = map(float, re.search(r'Duration: (\d+):(\d+):([\d.]+)', probe.stderr).groups())
    duration = h * 3600 + m * 60 + s
    line = next(l for l in probe.stderr.splitlines() if 'Video:' in l)
    w, ht = map(int, re.search(r'(\d{3,5})x(\d{3,5})', line).groups())
    fps = re.search(r'([\d.]+) fps', line)
    times = [duration * (n + .5) / 16 for n in range(16)]
    sheet = Image.new('RGB', (1280, 800), (20, 20, 20)); draw = ImageDraw.Draw(sheet)
    for n, t in enumerate(times):
        frame = out / f'{idx:02d}-{n:02d}.jpg'
        subprocess.run([FFMPEG, '-v', 'error', '-ss', str(t), '-i', p, '-frames:v', '1',
                        '-vf', 'scale=320:170:force_original_aspect_ratio=decrease', '-y', str(frame)], capture_output=True)
        if frame.exists():
            im = Image.open(frame); x = (n % 4) * 320; y = (n // 4) * 200
            sheet.paste(im, (x + (320 - im.width) // 2, y)); draw.text((x + 5, y + 174), f'{t:.1f}s', fill='white')
    sheet.save(out / f'{idx:02d}-sheet.jpg')
    scan = subprocess.run([FFMPEG, '-hide_banner', '-i', p, '-an', '-vf', "scale=256:-2,select='gt(scene,0.30)',showinfo",
                           '-f', 'null', '-'], capture_output=True, text=True)
    cuts = [float(t) for t in re.findall(r'pts_time:([0-9.]+)', scan.stderr)]
    gaps = [b - a for a, b in zip([0] + cuts, cuts + [duration])]
    result = {'id': idx, 'path': p, 'duration': duration, 'width': w, 'height': ht,
              'fps': fps.group(1) if fps else None, 'video_stream': line, 'scene_threshold': .3,
              'detected_transitions': len(cuts), 'transition_times': cuts,
              'median_detected_interval': statistics.median(gaps), 'sheet': str(out / f'{idx:02d}-sheet.jpg')}
    (out / f'{idx:02d}-analysis.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    refs, out, patterns = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    selected = [r['path'] for r in refs if any(p in r['path'] for p in patterns)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(process, [(i, p, out) for i, p in enumerate(selected)]))
    (out / 'measurements.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
