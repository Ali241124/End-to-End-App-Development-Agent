
import json
import re
from pathlib import Path, PurePosixPath

from ollama import chat


# The local model that already works in your setup.
MODEL_NAME = "qwen2.5:7b"

# Generated applications must stay inside this directory.
WORKSPACE = Path(__file__).resolve().parents[2] / "generated_projects"

# Limits help prevent unexpectedly large model responses.
MAX_FILES = 8
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

    # Require simple, relative paths using forward slashes.
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

    # Ensure the resolved destination remains inside this project.
    try:
        target.relative_to(project_root)
    except ValueError:
        raise ValueError(f"File escapes the project directory: {relative_path}")

    return target


_CURRENT_PROJECT_ROOT = WORKSPACE


def generate_project(app_idea: str) -> Path:
    """Ask the AI for a project and write its files into the workspace."""

    if not app_idea.strip():
        raise ValueError("Please describe the application you want to build.")

    print("\nAsking Qwen to generate the project files...")

    response = chat(
        model=MODEL_NAME,
        format="json",
        options={
            "temperature": 0.2,
            "num_predict": 2500,
            },
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": app_idea},
        ],
    )

    # Convert the AI's JSON text into a Python dictionary.
    try:
        result = json.loads(response.message.content)
    except json.JSONDecodeError as error:
        raise ValueError("The AI returned invalid JSON.") from error

    if not isinstance(result, dict):
        raise ValueError("The AI response must be a JSON object.")

    project_name = make_safe_project_name(
        result.get("project_name", "")
    )

    files = result.get("files")

    if not isinstance(files, list) or not files:
        raise ValueError("The AI did not return a valid file list.")

    if len(files) > MAX_FILES:
        raise ValueError(
            f"The AI returned too many files. Limit: {MAX_FILES}."
        )

    total_chars = 0
    validated_files = []
    seen_paths = set()

    # Validate every file before writing any of them.
    project_root = (WORKSPACE / project_name).resolve()

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

        # Temporarily set the root so the path validator checks
        # this particular project's directory.
        global _CURRENT_PROJECT_ROOT
        _CURRENT_PROJECT_ROOT = project_root

        target = validate_file_path(relative_path)

        relative_key = target.relative_to(project_root).as_posix().lower()

        if relative_key in seen_paths:
            raise ValueError(f"Duplicate file path: {relative_path}")

        seen_paths.add(relative_key)
        validated_files.append((target, content))

    # Do not silently overwrite an earlier generated project.
    if project_root.exists():
        raise FileExistsError(
            f"{project_root} already exists. "
            "Rename or move the existing folder before trying again."
        )

    # Create files only after all entries have passed validation.
    project_root.mkdir(parents=True, exist_ok=False)

    try:
        for target, content in validated_files:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    except Exception:
        # Remove a partial output if writing fails.
        import shutil
        shutil.rmtree(project_root, ignore_errors=True)
        raise

    return project_root


if __name__ == "__main__":
    print("=" * 60)
    print("END-TO-END APP DEVELOPMENT AGENT")
    print("Project File Generator")
    print("=" * 60)

    idea = input("\nDescribe the application you want to build: ")

    try:
        output_path = generate_project(idea)

        print("\nProject files created successfully!")
        print(f"Location: {output_path}")
        print("\nGenerated files:")

        for file_path in sorted(output_path.rglob("*")):
            if file_path.is_file():
                print(f"  - {file_path.relative_to(output_path)}")

        print("\nNote: These files have been generated, not tested.")

    except Exception as error:
        print(f"\nCould not generate the project: {error}")
