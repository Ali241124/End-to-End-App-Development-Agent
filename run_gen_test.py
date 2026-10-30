import sys, json, pathlib, traceback
sys.path.append('c:/Users/ah627/OneDrive/Documents/End-to-End-App-Development-Agent')
from app.generators.project_generator import generate_project

project_name = 'demoapp'
workspace = pathlib.Path('c:/Users/ah627/OneDrive/Documents/End-to-End-App-Development-Agent') / 'generated_projects' / project_name
import shutil
if workspace.exists():
    shutil.rmtree(workspace)
workspace.mkdir(parents=True, exist_ok=False)
intent_path = workspace / 'intent.json'
intent = {
    "project_name": project_name,
    "tech_preferences": {"frontend": "React", "backend": "FastAPI"},
    "features": ["todo list"]
}
intent_path.write_text(json.dumps(intent), encoding='utf-8')

try:
    out = generate_project('dummy idea', project_name)
    print('Generated at', out)
    for p in sorted(out.rglob('*')):
        if p.is_file():
            print(' -', p.relative_to(out))
except Exception as e:
    traceback.print_exc()

