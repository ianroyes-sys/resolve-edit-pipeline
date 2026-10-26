"""Build contact sheets: camera thumbnails, plus 8-frame sheets for finished reference edits.

Usage: python3 contact_sheets.py OUT_DIR [--thumbs THUMBNAIL_DIR] [--refs reference-candidates.json]
       [--exclude SUBSTRING ...]
Sheets are sparse samples (one frame every 8 s). They are triage, not a watched review.
"""
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from _config import FFMPEG


def card_sheets(thumbs, out):
    files = sorted(Path(thumbs).glob('*.JPG')) + sorted(Path(thumbs).glob('*.jpg'))
    for start in range(0, len(files), 24):
        page = Image.new('RGB', (1440, 1000), '#151515')
        draw = ImageDraw.Draw(page)
        for i, p in enumerate(files[start:start + 24]):
            im = ImageOps.contain(Image.open(p).convert('RGB'), (350, 140))
            x, y = (i % 4) * 360, (i // 4) * 166
            page.paste(im, (x, y))
            draw.text((x + 5, y + 143), p.stem, fill='white')
        page.save(out / f'card-{start // 24 + 1:02}.jpg')
    print('Card sheets created', len(files), flush=True)


def reference(args):
    i, row, out = args
    output = out / f'reference-{i:03}.jpg'
    cmd = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', row['path'], '-an',
           '-vf', 'fps=1/8,scale=320:-1,tile=4x2', '-frames:v', '1', '-y', str(output)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        return {'id': i, 'path': row['path'], 'sheet': str(output), 'ok': output.exists(),
                'error': result.stderr.decode()[-400:]}
    except subprocess.TimeoutExpired:
        return {'id': i, 'path': row['path'], 'ok': False, 'error': 'timeout'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--thumbs')
    ap.add_argument('--refs')
    ap.add_argument('--exclude', nargs='*', default=[])
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.thumbs:
        card_sheets(a.thumbs, out)
    if a.refs:
        refs = [r for r in json.loads(Path(a.refs).read_text())
                if not any(x.lower() in r['path'].lower() for x in a.exclude)]
        results = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for r in pool.map(reference, [(i, r, out) for i, r in enumerate(refs)]):
                results.append(r)
                print(r['id'], r['ok'], Path(r['path']).name, flush=True)
                (out / 'references.json').write_text(json.dumps(results, indent=2))
