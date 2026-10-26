"""Build native Gallery::GyStill DRX candidates from grade-inventory.json; never calls Resolve.

Usage: python3 native_wrappers.py OUT_DIR   (the folder extract_grades.py wrote to)
The Resolve_Color_Exchange wrappers from extract_grades.py are offline analysis artifacts only.
Grade Body bytes are copied unchanged. Validate candidates with resolve/validate_grade.py
in a disposable project.
"""
from pathlib import Path
import json
import re
import uuid
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
inventory = json.loads((ROOT/'grade-inventory.json').read_text())
for project in inventory:
    for row in project['bodies']:
        if not row.get('filmlook'):
            continue
        source = Path(row['extracted_drx'])
        body = ET.parse(source).getroot().findtext('Body')
        # Native exporter structure, as also used by drx-codec/drx-generator.js.
        text = f'''<?xml version="1.0" encoding="UTF-8"?>
<!--DbAppVer="20.3.3.0010" DbPrjVer="15"-->
<Gallery::GyStill DbId="{uuid.uuid4()}">
 <FieldsBlob/>
 <SrcHint>{escape(project['archive'])}</SrcHint>
 <SrcType>1</SrcType>
 <GalleryPath/>
 <Label>{escape(source.stem)} native wrapper candidate</Label>
 <RecTC>01:00:00:00</RecTC>
 <SrcTC>00:00:00:00</SrcTC>
 <DpxDescriptor>50</DpxDescriptor>
 <Width>3840</Width>
 <Height>2160</Height>
 <BitDepth>10</BitDepth>
 <PAR>1</PAR>
 <Endianship>1</Endianship>
 <CreateTime>2026-09-18T00:00:00.000</CreateTime>
 <pClipFullVer>
  <ListMgt::LmVersion DbId="{uuid.uuid4()}">
   <FieldsBlob/>
   <Name/>
   <HasCorrection>true</HasCorrection>
   <VerType>0</VerType>
   <ImplVersion>1</ImplVersion>
   <IncludedInRecording>true</IncludedInRecording>
   <FlatPassEnabled>false</FlatPassEnabled>
   <RGBAOutputEnabled>false</RGBAOutputEnabled>
   <Body>{body}</Body>
   <UseVersionClipProcParams>true</UseVersionClipProcParams>
  </ListMgt::LmVersion>
 </pClipFullVer>
 <PrimaryCCMode>0</PrimaryCCMode>
</Gallery::GyStill>
'''
        target = ROOT/(source.stem+'-native.drx')
        target.write_text(text)
        assert re.search(r'<Body>([^<]+)</Body>', text).group(1) == body
        print(target.name)
