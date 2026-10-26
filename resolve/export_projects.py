"""Export copies of existing Resolve projects to .drp without editing them.

Usage: python3 export_projects.py OUT_DIR "Project A" "Project B" ...
"""
import sys
from pathlib import Path

from _config import resolve_app

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
pm = resolve_app().GetProjectManager()
for name in sys.argv[2:]:
    path = out / (name + '.drp')
    if path.exists():
        print('Already exported', name)
        continue
    print(name, pm.ExportProject(name, str(path), True), flush=True)
