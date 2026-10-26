"""Find Film Look Creator grades inside exported .drp archives and wrap their Body bytes as DRX.

Usage: python3.14 extract_grades.py DRP_DIR OUT_DIR
Needs Python 3.14+ for the built-in Zstandard decoder (compression.zstd). Never opens Resolve.
Writes OUT_DIR/grade-inventory.json and one <project>-<sha12>.drx per unique Film Look body.
These Resolve_Color_Exchange wrappers are for offline analysis; use native_wrappers.py
to build import candidates.
"""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from compression import zstd
from pathlib import Path

FILMLOOK = b'com.blackmagicdesign.resolvefx.filmlook'


def readxml(data):
    # Resolve uses C++ namespace labels (Gallery::GyStill), not XML namespaces.
    return ET.fromstring(re.sub(rb'(<\/?[A-Za-z0-9_]+)::', rb'\1__', data))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    archives, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    results, unique = [], {}
    for archive in sorted(archives.glob('*.drp')):
        rows = []
        with zipfile.ZipFile(archive) as z:
            for member in z.namelist():
                if not member.endswith('.xml'):
                    continue
                try:
                    root = readxml(z.read(member))
                except Exception as exc:
                    rows.append({'member': member, 'parse_error': str(exc)})
                    continue
                parents = {child: par for par in root.iter() for child in par}
                for index, body in enumerate(root.iter('Body')):
                    rawhex = ''.join((body.text or '').split())
                    if not rawhex:
                        continue
                    row = {'archive': archive.name, 'member': member, 'body_index': index, 'ancestors': []}
                    node = parents.get(body)
                    while node is not None:
                        row['ancestors'].append({'tag': node.tag, 'id': node.get('DbId'), 'name': node.findtext('Name'),
                                                 'label': node.findtext('Label'),
                                                 'has_correction': node.findtext('HasCorrection')})
                        node = parents.get(node)
                    try:
                        data = bytes.fromhex(rawhex)
                        if data[:1] == b'\x81' and data[1:5] == bytes.fromhex('28b52ffd'):
                            decoded = zstd.decompress(data[1:])
                        elif data[:1] == b'\x80':
                            decoded = data[1:]
                        else:
                            row['unknown_header'] = data[:12].hex(); rows.append(row); continue
                        row['plugins'] = sorted(set(x.decode('ascii') for x in re.findall(rb'com\.[a-zA-Z0-9_.-]+', decoded)))
                        row['filmlook'] = FILMLOOK in decoded
                        row['sha256'] = hashlib.sha256(data).hexdigest()
                        row['decoded_bytes'] = len(decoded)
                        row['strings'] = [x.decode('ascii') for x in re.findall(rb'[\x20-\x7e]{5,}', decoded)]
                        if row['filmlook']:
                            key = row['sha256']
                            if key not in unique:
                                stem = re.sub(r'[^A-Za-z0-9_-]+', '-', archive.stem) + '-' + key[:12]
                                drx = ET.Element('Resolve_Color_Exchange')
                                ET.SubElement(drx, 'Label').text = archive.stem + ' preserved reference grade ' + key[:12]
                                ET.SubElement(drx, 'Width').text = root.findtext('Width') or '3840'
                                ET.SubElement(drx, 'Height').text = root.findtext('Height') or '2160'
                                ET.SubElement(drx, 'Body').text = rawhex
                                target = out / (stem + '.drx')
                                ET.ElementTree(drx).write(target, encoding='UTF-8', xml_declaration=True)
                                assert bytes.fromhex(ET.parse(target).getroot().findtext('Body')) == data
                                unique[key] = str(target)
                            row['extracted_drx'] = unique[key]
                    except Exception as exc:
                        row['decode_error'] = str(exc)
                    rows.append(row)
        results.append({'archive': archive.name, 'body_count': len(rows),
                        'filmlook_count': sum(bool(x.get('filmlook')) for x in rows), 'bodies': rows})
        print(archive.name, 'bodies', len(rows), 'filmlook', results[-1]['filmlook_count'])
    (out / 'grade-inventory.json').write_text(json.dumps(results, indent=2))
    print('Unique preserved Film Look grade files:', len(unique))
