"""One strip per clip with frames at 18%, 50% and 80%, then 8-clip pages.

Usage: python3 review_card.py CLIP_DIR card-metadata.json OUT_DIR
"""
import io
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

from _config import FFMPEG


def review(args):
    c, clip_dir, out = args
    name = c['clip']
    source = clip_dir / (name + '.MP4')
    page = Image.new('RGB', (960, 205), '#121212')
    draw = ImageDraw.Draw(page)
    samples = []
    for i, fraction in enumerate([.18, .5, .8]):
        sec = c['duration_seconds'] * fraction
        r = subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-ss', str(sec),
                            '-i', str(source), '-frames:v', '1', '-vf', 'scale=320:-1',
                            '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'], capture_output=True, timeout=45)
        if r.returncode or not r.stdout:
            continue
        page.paste(Image.open(io.BytesIO(r.stdout)).convert('RGB'), (i * 320, 0))
        draw.text((i * 320 + 4, 183), f'{name}  {sec:.2f}s / {c["duration_seconds"]:.2f}s', fill='white')
        samples.append(sec)
    page.save(out / (name + '.jpg'))
    return {'clip': name, 'sample_times': samples, 'sheet': str(out / (name + '.jpg'))}


if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    clip_dir, meta, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    clips = json.loads(meta.read_text())['clips']
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = []
        for r in pool.map(review, [(c, clip_dir, out) for c in clips]):
            results.append(r)
            print(r['clip'], flush=True)
    (out / 'index.json').write_text(json.dumps(results, indent=2))
    for start in range(0, len(clips), 8):
        page = Image.new('RGB', (960, 1640), '#121212')
        for i, c in enumerate(clips[start:start + 8]):
            page.paste(Image.open(out / (c['clip'] + '.jpg')), (0, 205 * i))
        page.save(out / f'page-{start // 8 + 1:02}.jpg')
