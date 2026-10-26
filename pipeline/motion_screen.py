"""Screen planned shot ranges for camera movement with phase correlation.

Usage: python3 motion_screen.py CLIP_DIR edit-plan.json OUT_DIR [--extra CLIP:IN:DURATION ...]
For each range: frames at 12 fps, grayscale 320x180, frame-to-frame translation (dx, dy),
plus a dense contact sheet (every 3rd frame) to spot resets and reframes.
The numbers are screening evidence. Watch the range at normal speed before approving it.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from _config import FFMPEG


def screen(source, start, dur):
    raw = subprocess.check_output([FFMPEG, '-v', 'error', '-ss', str(start), '-t', str(dur), '-i', str(source),
                                   '-vf', 'fps=12,scale=320:180,format=gray', '-f', 'rawvideo', '-'])
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320)
    motions = []
    for a, b in zip(frames[:-1], frames[1:]):
        a = a.astype(float); b = b.astype(float); a -= a.mean(); b -= b.mean()
        cross = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
        cross /= np.maximum(abs(cross), 1e-9)
        corr = abs(np.fft.ifft2(cross))
        y, x = np.unravel_index(corr.argmax(), corr.shape)
        x = x if x < 160 else x - 320
        y = y if y < 90 else y - 180
        motions.append({'time': round(start + (len(motions) + 1) / 12, 3), 'dx': int(x), 'dy': int(y),
                        'shift': round(float(np.hypot(x, y)), 2),
                        'difference': round(float(np.mean(abs(a - b))), 2)})
    return frames, motions


if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    clip_dir, plan, out = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    ranges = [(s['clip'], s['in'], s['duration']) for s in plan['shots']]
    if '--extra' in sys.argv:
        for spec in sys.argv[sys.argv.index('--extra') + 1:]:
            c, i, d = spec.split(':'); ranges.append((c, float(i), float(d)))
    results = []
    for name, start, dur in ranges:
        frames, motions = screen(clip_dir / f'{name}.MP4', start, dur)
        results.append({'clip': name, 'in': start, 'duration': dur,
                        'max_shift': max((m['shift'] for m in motions), default=0), 'motions': motions})
        picks = list(range(0, len(frames), 3))
        sheet = Image.new('RGB', (1280, 205 * ((len(picks) + 3) // 4)), '#171717')
        draw = ImageDraw.Draw(sheet)
        for k, j in enumerate(picks):
            x, y = k % 4 * 320, k // 4 * 205
            sheet.paste(Image.fromarray(frames[j]).convert('RGB'), (x, y))
            draw.text((x + 4, y + 183), f'{name} {start + j / 12:.2f}s', fill='white')
        sheet.save(out / f'{name}-{start}-motion.jpg')
        print(name, start, results[-1]['max_shift'], flush=True)
    (out / 'motion-analysis.json').write_text(json.dumps(results, indent=2))
