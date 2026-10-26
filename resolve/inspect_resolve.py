"""Print Resolve version, projects in the current folder, and the current project's settings."""
import json

from _config import resolve_app

r = resolve_app()
pm = r.GetProjectManager()
p = pm.GetCurrentProject()
print(json.dumps({'product': r.GetProductName(), 'version': r.GetVersionString(),
                  'projects': pm.GetProjectListInCurrentFolder(),
                  'folders': pm.GetFolderListInCurrentFolder(),
                  'current': p.GetName() if p else None}, indent=2))
if p:
    print('SETTINGS', json.dumps(p.GetSetting(), indent=2))
