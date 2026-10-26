"""Copy a camera card's folder structure to working storage, verifying SHA-256.

Usage: python3 ingest.py SOURCE_DIR DEST_DIR [MANIFEST_JSON]
Never deletes or modifies the source. An existing copy that differs is an error.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    source, dest = Path(sys.argv[1]), Path(sys.argv[2])
    manifest = Path(sys.argv[3]) if len(sys.argv) > 3 else dest.parent / 'ingest-manifest.json'
    results = []
    for p in sorted(source.rglob('*')):
        if not p.is_file() or any(s.startswith('.') for s in p.relative_to(source).parts):
            continue
        target = dest / p.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(p)
        if target.exists():
            if digest(target) != before:
                raise RuntimeError(f'Existing copy differs: {target}')
        else:
            shutil.copyfile(p, target)
        if digest(target) != before:
            raise RuntimeError(f'Checksum mismatch: {p}')
        results.append({'source': str(p), 'copy': str(target), 'bytes': p.stat().st_size,
                        'sha256': before, 'verified': True})
        manifest.write_text(json.dumps(results, indent=2))
        print('Verified', p.name, flush=True)
    print('COMPLETE', len(results), 'files', flush=True)
