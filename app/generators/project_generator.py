import json
import re
import sys
from pathlib import Path, PurePosixPath
import re
import json
from pathlib import Path, PurePosixPath

# Simple templating helper – substitutes {{ expr }} using a context dict.
def _render_template_string(template: str, context: dict) -> str:
    """Replace ``{{ expr }}`` placeholders with values from ``context``.

    ``expr`` may be a dotted attribute chain like ``intent.tech_preferences.frontend``.
    The function walks the context dictionary accordingly.
    """
    pattern = re.compile(r"{{\s*([^}]+)\s*}}")
    def replace(match):
        expr = match.group(1).strip()
        # Resolve dotted expression against the provided context.
        parts = expr.split('.')
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                # Fallback: try attribute access (unlikely in our simple dicts).
                value = getattr(value, part, None)
            if value is None:
                break
        return str(value) if value is not None else ''
    return pattern.sub(replace, template)


try:
    from ollama import chat
except ImportError:
    # Ollama not available in this environment; define a stub.
    def chat(*args, **kwargs):
        raise NotImplementedError("Ollama chat is not available in this sandbox.")

# The local model that already works in your setup.
MODEL_NAME = "qwen2.5:7b"

# Generated applications must stay inside this directory.
WORKSPACE = Path(__file__).resolve().parents[2] / "generated_projects"

# Limits help prevent unexpectedly large model responses.
MAX_FILES = 12  # increased to accommodate additional scaffold files
MAX_FILE_CHARS = 20_000
MAX_TOTAL_CHARS = 100_000

# These paths or file types are not permitted.
BLOCKED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}

BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".msi",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".pyc",
    ".pem",
    ".key",
}

SYSTEM_PROMPT = """
You are a software project scaffolding assistant.

Create a small, coherent starter project from the user's application idea.

Requirements:
- Return 3 to 6 files only.
- Keep each file short and useful.
- For a React and FastAPI app, prefer:
  1. README.md
  2. frontend/package.json
  3. frontend/src/App.jsx
  4. frontend/src/main.jsx
  5. backend/main.py
  6. backend/requirements.txt
- Use only the files needed for the requested project type.
- Include complete file contents. Do not use ellipses or placeholders.
- Do not create .env files, secrets, private keys, or binaries.
- Do not include node_modules, virtual environments, or build folders.
- Do not claim that the project has been tested or deployed.
- Do not generate a huge or production-scale application.

Return only valid JSON with this structure:
{
  "project_name": "example-app",
  "files": [
    {
      "path": "README.md",
      "content": "# Example app"
    }
  ]
}

The project_name must be short and filesystem-safe.
Every path must be relative to the project root.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "files": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["project_name", "files"],
    "additionalProperties": False,
}

def make_safe_project_name(name: str) -> str:
    """Convert a project name into a safe folder name."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_-]+", "-", name)
    name = name.strip("-_")
    if not name:
        raise ValueError("The AI did not provide a valid project name.")
    return name[:60]

def validate_file_path(relative_path: str) -> Path:
    """Reject unsafe paths and return a path inside the workspace project."""
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("A generated file has an empty path.")
    if "\\" in relative_path or ":" in relative_path:
        raise ValueError(f"Unsafe file path: {relative_path}")
    parsed_path = PurePosixPath(relative_path)
    if parsed_path.is_absolute() or ".." in parsed_path.parts:
        raise ValueError(f"Path traversal is not allowed: {relative_path}")
    if any(part in BLOCKED_DIRECTORIES for part in parsed_path.parts):
        raise ValueError(f"Blocked directory in path: {relative_path}")
    if parsed_path.name.lower() == ".env":
        raise ValueError("Generated .env files are not allowed.")
    if parsed_path.suffix.lower() in BLOCKED_EXTENSIONS:
        raise ValueError(f"Blocked file type: {relative_path}")
    project_root = _CURRENT_PROJECT_ROOT.resolve()
    target = project_root.joinpath(*parsed_path.parts).resolve()
    try:
        target.relative_to(project_root)
    except ValueError:
        raise ValueError(f"File escapes the project directory: {relative_path}")
    return target

_CURRENT_PROJECT_ROOT = WORKSPACE

def _render_templates(project_name: str) -> list[dict]:
    """Render simple ``{{ ... }}`` templates for the given project.

    This implementation avoids the external ``jinja2`` dependency by loading the
    ``.j2`` files as raw text and performing a minimal placeholder substitution
    using ``_render_template_string`` (defined earlier in this file).
    """
    project_root = Path("generated_projects") / project_name
    intent_path = project_root / "intent.json"
    if not intent_path.is_file():
        raise FileNotFoundError(f"Intent file not found: {intent_path}")
    intent = json.loads(intent_path.read_text(encoding="utf-8"))

    # List of (template_file, output_path) relative to the templates directory.
    files_to_render = [
        ("frontend/package.json.j2", "frontend/package.json"),
        ("frontend/src/App.jsx.j2", "frontend/src/App.jsx"),
        # Backend template
        ("backend/main.py.j2", "backend/main.py"),
        ("backend/requirements.txt.j2", "backend/requirements.txt"),
        ("README.md.j2", "README.md"),
        # Add more template mappings here as you create new .j2 files.
    ]
    rendered: list[dict] = []
    templates_dir = Path(__file__).parent / "templates"
    for tmpl_name, out_path in files_to_render:
        tmpl_path = templates_dir / tmpl_name
        if not tmpl_path.is_file():
            raise FileNotFoundError(f"Template not found: {tmpl_path}")
        raw_template = tmpl_path.read_text(encoding="utf-8")
        # Provide a context that includes the intent dict and the project name.
        context = {"intent": intent, "project_name": project_name}
        content = _render_template_string(raw_template, context)
        rendered.append({"path": out_path, "content": content})
    return rendered

def generate_project(app_idea: str, project_name: str) -> Path:
    """Generate a project using Jinja2 templates and write its files.

    The function expects that `planner` has already created the intent JSON
    under `generated_projects/<project_name>/intent.json`.
    """
    if not app_idea.strip():
        raise ValueError("Please describe the application you want to build.")
    if not project_name.strip():
        raise ValueError("Please provide a project name.")

    # Render the template based files.
    files = _render_templates(project_name)

    # Validate file list size constraints.
    if len(files) > MAX_FILES:
        raise ValueError(f"Too many files generated: {len(files)} > {MAX_FILES}")

    # Validation loop identical to the original implementation.
    total_chars = 0
    validated_files = []
    seen_paths = set()
    project_root = (WORKSPACE / make_safe_project_name(project_name)).resolve()

    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Each file must contain a path and content.")
        relative_path = item.get("path")
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("Every file's content must be text.")
        if len(content) > MAX_FILE_CHARS:
            raise ValueError(f"File is too large: {relative_path}")
        total_chars += len(content)
        if total_chars > MAX_TOTAL_CHARS:
            raise ValueError("The generated project is too large.")
        # Temporarily set the root for path validation.
        global _CURRENT_PROJECT_ROOT
        _CURRENT_PROJECT_ROOT = project_root
        target = validate_file_path(relative_path)
        relative_key = target.relative_to(project_root).as_posix().lower()
        if relative_key in seen_paths:
            raise ValueError(f"Duplicate file path: {relative_path}")
        seen_paths.add(relative_key)
        validated_files.append((target, content))

    # Allow generation if the folder only contains the intent.json (i.e., planning stage).
    if project_root.exists():
        # Check existing items.
        existing_items = list(project_root.iterdir())
        non_intent_items = [p for p in existing_items if p.name.lower() != "intent.json" and not p.name.startswith('.')]
        if non_intent_items:
            raise FileExistsError(
                f"{project_root} already exists with generated content. "
                "Rename or move the existing folder before trying again."
            )
        # Otherwise, continue to generate files inside the existing folder.


    project_root.mkdir(parents=True, exist_ok=False)
    try:
        for target, content in validated_files:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(project_root, ignore_errors=True)
        raise
    print(f"Project generated at: {project_root}")
    return project_root

if __name__ == "__main__":
    print("=" * 60)
    print("END-TO-END APP DEVELOPMENT AGENT")
    print("Project File Generator")
    print("=" * 60)
    idea = input("\nDescribe the application you want to build: ")
    pname = input("Project name (no spaces): ")
    try:
        output_path = generate_project(idea, pname)
        print("\nProject files created successfully!")
        print(f"Location: {output_path}")
        print("\nGenerated files:")
        for file_path in sorted(output_path.rglob("*")):
            if file_path.is_file():
                print(f"  - {file_path.relative_to(output_path)}")
        print("\nNote: These files have been generated, not tested.")
    except Exception as error:
        print(f"\nCould not generate the project: {error}")
