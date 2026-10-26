"""QC a rendered review movie against the timeline it came from.

Usage: python3 qc_render.py MOVIE timeline-build.json OUT_DIR
Samples the start, middle and end of every shot into 5-shot pages, decodes the whole
file, and runs blackdetect + volumedetect. A full decode is not a watched review.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from _config import FFMPEG

if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    movie, build, out = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    fps, shots = build['fps'], build['shots']
    for group in range(0, len(shots), 5):
        page = Image.new('RGB', (960, 205 * min(5, len(shots) - group)), '#141414'); d = ImageDraw.Draw(page)
        for row, s in enumerate(shots[group:group + 5]):
            start = (s['timeline_start'] - build['start_frame']) / fps
            dur = s['timeline_duration_frames'] / fps
            for col, f in enumerate([.05, .5, .95]):
                sec = start + dur * f
                data = subprocess.check_output([FFMPEG, '-v', 'error', '-ss', str(sec), '-i', str(movie), '-frames:v', '1',
                                                '-vf', 'scale=320:180', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'])
                page.paste(Image.open(io.BytesIO(data)), (col * 320, row * 205))
                d.text((col * 320 + 3, row * 205 + 184), f'{s["clip"]} t={sec:.2f}s', fill='white')
        page.save(out / f'render-review-{group // 5 + 1}.jpg')
    result = subprocess.run([FFMPEG, '-hide_banner', '-i', str(movie), '-vf', 'blackdetect=d=0.1:pix_th=0.1',
                             '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True)
    (out / 'render-decode-qc.txt').write_text(result.stderr)
    assert result.returncode == 0, 'Render failed to decode'
    print(f'Render fully decoded; sampled beginning/middle/end of {len(shots)} shots.')
