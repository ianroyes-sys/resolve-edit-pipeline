"""Build full-length, source-traceable sound stems for a timeline with ffmpeg. Originals are never modified.

Usage: python3 build_stems.py sound-plan.json timeline-build.json CLIP_DIR OUT_DIR

Produces 48 kHz / 24-bit stereo WAVs that all start at the first picture frame:
  Music.wav     one track, two-pass loudnorm, fades, ducked under the listed dialogue shots
  Dialogue.wav  synchronous camera audio for chosen shots, filtered and loudness-matched
  Natural.wav   synchronous ambience (applause, room) under chosen shots
  SFX.wav       library effects placed a few ms before chosen cuts, peak-normalized
  Review-Mix.wav unity sum of the stems through a -1.5 dBFS limiter
and manifest.json with every source path, offset, gain and loudness measurement.
Stems are built, not auditioned: listen before delivery and confirm music rights.
See examples/sound-plan.example.json.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pipeline'))
from _config import FFMPEG  # noqa: E402

SR = 48000


def run(args):
    r = subprocess.run([FFMPEG, '-hide_banner', '-nostdin', '-y'] + list(map(str, args)), capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])
    return r.stderr


def loudness(log):
    return json.loads(log[log.rfind('{'):log.rfind('}') + 1])


def measure(path):
    return loudness(run(['-i', path, '-af', 'loudnorm=I=-20:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-']))


def normalized_segment(source, offset, duration, out, target, prefilter='anull'):
    base = ['-ss', offset, '-t', duration, '-i', source, '-vn']
    af = f'{prefilter},aformat=sample_rates=48000:channel_layouts=stereo'
    m = loudness(run(base + ['-af', f'{af},loudnorm=I={target}:TP=-2:LRA=11:print_format=json', '-f', 'null', '-']))
    norm = (f"loudnorm=I={target}:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(base + ['-af', f'{af},{norm},aresample=48000', '-ac', '2', '-c:a', 'pcm_s24le', out])
    return out, m


def full_stem(segments, out, samples):
    if not segments:
        run(['-f', 'lavfi', '-i', f'anullsrc=r={SR}:cl=stereo', '-t', samples / SR, '-c:a', 'pcm_s24le', out])
        return out
    args, filters = [], []
    for i, (p, start, duration, fade) in enumerate(segments):
        args += ['-i', p]
        filters.append(f'[{i}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,afade=t=in:d={fade},'
                       f'afade=t=out:st={max(0, duration - fade)}:d={fade},adelay={round(start * SR)}S:all=1[a{i}]')
    labels = ''.join(f'[a{i}]' for i in range(len(segments)))
    filters.append(f'{labels}amix=inputs={len(segments)}:normalize=0,apad,atrim=end_sample={samples}[out]')
    run(args + ['-filter_complex', ';'.join(filters), '-map', '[out]', '-ar', SR, '-ac', 2, '-c:a', 'pcm_s24le', out])
    return out


if __name__ == '__main__':
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    plan = json.loads(Path(sys.argv[1]).read_text())
    build = json.loads(Path(sys.argv[2]).read_text())
    clip_dir, out = Path(sys.argv[3]), Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
    fps = build['fps']
    total = (build['end_frame'] - build['start_frame'] + plan.get('tail_frames', 120)) / fps
    samples = round(total * SR)
    shots = {s['clip']: s for s in build['shots']}

    def place(clip):
        s = shots[clip]
        return (s['timeline_start'] - build['start_frame']) / fps, s['timeline_duration_frames'] / fps, s['in']

    manifest = {'fps': fps, 'duration_seconds': total, 'sample_rate': SR, 'samples': samples,
                'audio_auditioned': False, 'music_rights_verified': False, 'events': []}

    # Dialogue and natural sound: the clip's own synchronous audio under its picture.
    for stem in ('dialogue', 'natural'):
        segs = []
        for e in plan.get(stem, []):
            start, dur, src_in = place(e['clip'])
            src = clip_dir / (e['clip'] + '.MP4')
            p, m = normalized_segment(src, src_in, dur, out / f"{e['clip']}-{stem}.wav", e.get('target_lufs', -16),
                                      e.get('prefilter', 'highpass=f=70'))
            segs.append((p, start, dur, e.get('fade', .012)))
            manifest['events'].append({'stem': stem, 'source': str(src), 'source_in': src_in, 'timeline_start': start,
                                       'duration': dur, 'source_loudness': m, **e})
        full_stem(segs, out / (stem.capitalize() + '.wav'), samples)

    # Music: normalize, fade, duck under dialogue shots with linear ramps.
    music = plan.get('music')
    if music:
        norm, m = normalized_segment(music['source'], music.get('source_in', 0), total, out / 'music-normalized.wav',
                                     music.get('target_lufs', -20))
        duck, ramp = 10 ** (music.get('duck_db', -17) / 20), music.get('ramp', .5)
        expr = '1'
        for clip in reversed(music.get('duck_under', [])):
            a, d, _ = place(clip); b = a + d
            expr = (f"if(lt(t,{a - ramp}),{expr},if(lt(t,{a}),1-(1-{duck})*(t-{a - ramp})/{ramp},"
                    f"if(lt(t,{b}),{duck},if(lt(t,{b + ramp}),{duck}+(1-{duck})*(t-{b})/{ramp},{expr}))))")
        fi, fo = music.get('fade_in', .8), music.get('fade_out', 4)
        run(['-i', norm, '-af', f"volume='{expr}':eval=frame,afade=t=in:d={fi},afade=t=out:st={total - fo}:d={fo},"
             f"apad,atrim=end_sample={samples}", '-ar', SR, '-ac', 2, '-c:a', 'pcm_s24le', out / 'Music.wav'])
        manifest['events'].append({'stem': 'music', 'source_loudness': m, **music})
    else:
        full_stem([], out / 'Music.wav', samples)

    # SFX: start slightly before the cut, peak-normalize each effect.
    segs = []
    for e in plan.get('sfx', []):
        start, _, _ = place(e['at_clip'])
        start = max(0.0, start - e.get('lead', .12)); dur = e.get('duration', .8)
        log = run(['-i', e['source'], '-t', dur, '-af', 'volumedetect', '-f', 'null', '-'])
        peak = float(re.search(r'max_volume: ([\-\d.]+) dB', log).group(1))
        gain = e.get('peak_dbfs', -25) - peak
        p = out / f"{e['at_clip']}-sfx.wav"
        run(['-i', e['source'], '-t', dur, '-af', f'volume={gain}dB', '-ar', SR, '-ac', 2, '-c:a', 'pcm_s24le', p])
        segs.append((p, start, dur, .08))
        manifest['events'].append({'stem': 'sfx', 'timeline_start': start, 'gain_db': gain, **e})
    full_stem(segs, out / 'SFX.wav', samples)

    names = ['Music', 'Dialogue', 'Natural', 'SFX']
    args = []
    for n in names:
        args += ['-i', out / (n + '.wav')]
    run(args + ['-filter_complex', f'[0:a][1:a][2:a][3:a]amix=inputs=4:normalize=0,alimiter=limit={10 ** (-1.5 / 20)}'
                f':level=false:latency=true,apad,atrim=end_sample={samples}[out]', '-map', '[out]', '-ar', SR, '-ac', 2,
                '-c:a', 'pcm_s24le', out / 'Review-Mix.wav'])
    manifest['measurements'] = {n: measure(out / (n + '.wav')) for n in names + ['Review-Mix']}
    silence = run(['-i', out / 'Review-Mix.wav', '-af', 'silencedetect=noise=-55dB:d=0.2', '-f', 'null', '-'])
    manifest['mix_silence_events'] = [l for l in silence.splitlines() if 'silence_' in l]
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'duration': total, 'mix': manifest['measurements']['Review-Mix']}, indent=2))
