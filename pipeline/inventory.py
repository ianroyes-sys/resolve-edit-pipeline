"""Read-only media discovery. Writes a categorized manifest per root.

Usage: python3 inventory.py OUT_DIR name=/path/to/root [name=/path ...]
Videos whose names don't look like camera originals (C0001, DSC0001, MVI_0001)
are listed in reference-candidates.json as possible finished edits to study.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

VIDEO = {'.mov', '.mp4', '.mxf', '.mts', '.m2ts', '.avi', '.braw'}
AUDIO = {'.wav', '.mp3', '.aif', '.aiff', '.m4a', '.flac'}
SKIP = {'$RECYCLE.BIN', 'System Volume Information'}


def scan(root):
    rows = []
    for p in root.rglob('*'):
        if any(part.startswith('.') or part in SKIP for part in p.relative_to(root).parts):
            continue
        ext = p.suffix.lower()
        if ext not in VIDEO | AUDIO | {'.drp', '.drx', '.xml'} or not p.is_file():
            continue
        kind = ('audio' if ext in AUDIO else 'project' if ext in {'.drp', '.drx'}
                else 'metadata' if ext == '.xml' else 'video')
        camera = bool(re.match(r'^(C\d+|DSC\d+|MVI_\d+)\.', p.name, re.I))
        rows.append({'path': str(p), 'bytes': p.stat().st_size, 'kind': kind, 'camera_name': camera})
    return rows


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    refs = []
    for arg in sys.argv[2:]:
        name, root = arg.split('=', 1)
        rows = scan(Path(root))
        (out / f'{name}-inventory.json').write_text(json.dumps(rows, indent=2))
        print(name, dict(Counter(r['kind'] for r in rows)), 'GiB', round(sum(r['bytes'] for r in rows) / 2**30, 2))
        refs += [r for r in rows if r['kind'] == 'video' and not r['camera_name']]
    (out / 'reference-candidates.json').write_text(json.dumps(refs, indent=2))
    print('Reference candidates', len(refs))
