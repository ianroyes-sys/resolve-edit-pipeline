"""Read Sony XAVC sidecar XML for every clip on a card, then optionally transcribe speech.

Usage:
  python3 card_metadata.py CLIP_DIR OUT_DIR                 # metadata only
  python3 card_metadata.py CLIP_DIR OUT_DIR C0012 C0015     # + whisper.cpp transcripts
  python3 card_metadata.py CLIP_DIR OUT_DIR --voice C0012   # second pass with voice EQ

Writes OUT_DIR/card-metadata.json (frames, fps, duration, camera, gamma, primaries).
Transcripts are machine output for finding candidate lines, not auditioned quotes.
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from _config import FFMPEG, WHISPER_CLI, WHISPER_MODEL

RATES = {'23.98': 24000 / 1001, '29.97': 30000 / 1001, '59.94': 60000 / 1001}


def metadata(card, out):
    rows = []
    for path in sorted(card.glob('*M01.XML')):
        tree = ET.parse(path).getroot()

        def get(tag):
            found = tree.find('.//{*}' + tag)
            return found.attrib if found is not None else {}
        vf = get('VideoFrame')
        frames = int(get('Duration').get('value', 0))
        rate = vf.get('formatFps', '0p').rstrip('pi')
        fps = RATES.get(rate, float(rate))
        items = {x.get('name'): x.get('value') for x in tree.findall('.//{*}Item')}
        rows.append({'clip': path.stem.removesuffix('M01'), 'frames': frames, 'fps': fps,
                     'duration_seconds': frames / fps if fps else None, 'video': vf,
                     'layout': get('VideoLayout'), 'recorded': get('CreationDate').get('value'),
                     'camera': get('Device').get('modelName'),
                     'gamma': items.get('CaptureGammaEquation'),
                     'primaries': items.get('CaptureColorPrimaries')})
    result = {'count': len(rows), 'duration_seconds': sum(r['duration_seconds'] or 0 for r in rows),
              'format_fps_counts': dict(Counter(r['video'].get('formatFps') for r in rows)),
              'gamma_counts': dict(Counter(r['gamma'] for r in rows)), 'clips': rows}
    (out / 'card-metadata.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'clips'}), flush=True)


def transcribe(card, out, names, voice=False):
    if not WHISPER_MODEL:
        raise SystemExit('Set WHISPER_MODEL to a whisper.cpp ggml model path')
    for name in names:
        wave = out / (name + '.wav')
        if not wave.exists():
            subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                            '-i', str(card / (name + '.MP4')), '-vn', '-ac', '1', '-ar', '16000',
                            '-c:a', 'pcm_s16le', str(wave)], check=True)
        stem, extra = out / name, []
        if voice:
            stem = out / (name + '-voice')
            subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-i', str(wave),
                            '-af', 'highpass=f=110,lowpass=f=6500,loudnorm=I=-18:TP=-2:LRA=11',
                            '-ar', '16000', str(stem) + '.wav'], check=True)
            wave, extra = Path(str(stem) + '.wav'), ['-ml', '70', '-sow']
        with Path(str(stem) + '.log').open('w') as log:
            subprocess.run([WHISPER_CLI, '-m', WHISPER_MODEL, '-f', str(wave), '-of', str(stem),
                            '-oj', '-osrt', '-otxt', '-t', '4', '-ng'] + extra,
                           stdout=log, stderr=log, check=True)
        print(name, Path(str(stem) + '.txt').read_text(), flush=True)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    card, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    rest = sys.argv[3:]
    voice = '--voice' in rest
    names = [x for x in rest if x != '--voice']
    metadata(card, out)
    if names:
        transcribe(card, out, names, voice)
