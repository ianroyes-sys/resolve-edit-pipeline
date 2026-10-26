"""Copy a group's Post Clip Grade from a reference .drp into a group of a new .drp, offline.

Usage: python3 transfer_group.py BASE.drp REFERENCE.drp OUT.drp "Target group" [SOURCE_GROUP]

BASE is an exported project that already has an empty color group named "Target group"
(create it in Resolve and assign clips first). SOURCE_GROUP is the group name inside
REFERENCE (default G1). Every archive member stays byte-for-byte identical except the
target slot's Body and HasCorrection. The source project is never rewritten or imported.
Writes group-transfer-report.json next to OUT.drp.
"""
from pathlib import Path
import zipfile
import re
import json
import hashlib
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) < 5:
    raise SystemExit(__doc__)
BASE, REFERENCE, DEST = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
TARGET_GROUP = sys.argv[4]
SOURCE_GROUP = sys.argv[5] if len(sys.argv) > 5 else 'G1'
ROOT = DEST.parent

def parse(data):
    return ET.fromstring(re.sub(rb'(<\/?[A-Za-z0-9_]+)::', rb'\1__', data))

def slot(xml, name):
    groups = [e for e in parse(xml).iter('Sm2Group') if e.findtext('Name') == name]
    assert len(groups) == 1, (name, len(groups))
    group = groups[0]
    versions = [e for e in group.iter('ListMgt__LmVersion') if e.findtext('Name') == 'Post Clip Grade']
    assert len(versions) == 1, (name, len(versions))
    version = versions[0]
    return group.get('DbId'), version.get('DbId'), version.findtext('Body'), version.findtext('HasCorrection')

assert BASE != DEST and REFERENCE != DEST
assert not DEST.exists(), 'Refusing to overwrite existing output'
with zipfile.ZipFile(BASE) as zin, zipfile.ZipFile(REFERENCE) as zref:
    before = zin.read('project.xml')
    source = zref.read('project.xml')
    gid, vid, old_body, old_correction = slot(before, TARGET_GROUP)
    source_gid, source_vid, new_body, source_correction = slot(source, SOURCE_GROUP)
    assert source_correction == 'true'
    assert new_body and re.fullmatch(r'[0-9a-fA-F]+', new_body)
    # Match only the already-parsed UUIDs, and retain original XML formatting.
    group_pat = rb'<Sm2Group\b(?=[^>]*\bDbId="'+re.escape(gid.encode())+rb'")[^>]*>.*?</Sm2Group>'
    group_matches = list(re.finditer(group_pat, before, re.S))
    assert len(group_matches) == 1
    gm = group_matches[0]
    group_bytes = gm.group()
    ver_pat = rb'<ListMgt::LmVersion\b(?=[^>]*\bDbId="'+re.escape(vid.encode())+rb'")[^>]*>.*?</ListMgt::LmVersion>'
    vmatches = list(re.finditer(ver_pat, group_bytes, re.S))
    assert len(vmatches) == 1
    vm = vmatches[0]
    version_bytes = vm.group()
    assert len(re.findall(rb'<Body(?:\s*/>|>.*?</Body>)', version_bytes, re.S)) == 1
    patched_version, n = re.subn(rb'<Body(?:\s*/>|>.*?</Body>)', b'<Body>'+new_body.encode()+b'</Body>', version_bytes, flags=re.S)
    assert n == 1
    patched_version, n = re.subn(rb'<HasCorrection>.*?</HasCorrection>', b'<HasCorrection>true</HasCorrection>', patched_version, flags=re.S)
    assert n == 1
    patched_group = group_bytes[:vm.start()]+patched_version+group_bytes[vm.end():]
    after = before[:gm.start()]+patched_group+before[gm.end():]
    assert slot(after, TARGET_GROUP) == (gid, vid, new_body, 'true')
    # Canonical comparison after replacing ONLY the two intended values back.
    revert = patched_version.replace(b'<Body>'+new_body.encode()+b'</Body>', re.search(rb'<Body(?:\s*/>|>.*?</Body>)', version_bytes, re.S).group(), 1)
    revert = revert.replace(b'<HasCorrection>true</HasCorrection>', b'<HasCorrection>'+old_correction.encode()+b'</HasCorrection>', 1)
    assert revert == version_bytes
    with zipfile.ZipFile(DEST, 'w') as zout:
        zout.comment = zin.comment
        for info in zin.infolist():
            zout.writestr(info, after if info.filename == 'project.xml' else zin.read(info.filename))

with zipfile.ZipFile(BASE) as a, zipfile.ZipFile(DEST) as b:
    assert a.namelist() == b.namelist()
    changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert changed == ['project.xml'], changed
    assert slot(b.read('project.xml'), TARGET_GROUP)[2] == new_body
    report = {'source_project': str(REFERENCE), 'source_group': SOURCE_GROUP, 'source_group_id': source_gid,
              'source_version_id': source_vid, 'base_project': str(BASE), 'output_project': str(DEST),
              'target_group': TARGET_GROUP, 'target_group_id': gid, 'target_version_id': vid,
              'changed_members': changed, 'unchanged_members': [n for n in a.namelist() if n not in changed],
              'changes': ['Target group Post Clip Grade Body', 'Target group Post Clip Grade HasCorrection=true'],
              'body_sha256': hashlib.sha256(bytes.fromhex(new_body)).hexdigest(),
              'archive_sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(),
              'validation': 'All member names/order identical; every non-project.xml member byte-identical; replacing only two target values reverses to original version XML; IDs unchanged.',
              'resolve_import_validated': False}
(ROOT/'group-transfer-report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
