import argparse, json, pathlib, subprocess, sys, traceback, importlib, os

# Uvicorn import with fallback stub - ensures the name exists for static analysis.
try:
    import uvicorn  # type: ignore
except ImportError:
    class _UvicornStub:
        @staticmethod
        def run(*args, **kwargs):
            raise NotImplementedError("uvicorn is not installed; backend preview unavailable.")
    uvicorn = _UvicornStub()


# Project paths
ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'generated_projects'

def run_planner(app_idea: str, project_name: str):
    """Execute the planner to create intent.json and development plan.
    The planner is a module that provides a main function or similar.
    """
    try:
        from app.agents.planner import plan_project
    except Exception:
        traceback.print_exc()
        raise RuntimeError('Planner module not found or failed to import')
    # planner expects to be run interactively; we call its core logic directly if available.
    # The existing planner script writes intent.json under generated_projects/<project_name>/intent.json
    # Here we invoke its CLI via subprocess for simplicity.
    cmd = [sys.executable, '-m', 'app.agents.planner']
    # The planner script prompts for input; we feed via stdin.
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Provide idea and project name (the script asks for description then name).
    input_data = f"{app_idea}\n{project_name}\n"
    out, err = proc.communicate(input_data)
    if proc.returncode != 0:
        raise RuntimeError(f'Planner failed: {err}')
    print(out)

def run_generator(app_idea: str, project_name: str):
    """Run the project generator after the planner has produced intent.json."""
    try:
        from app.generators.project_generator import generate_project
    except Exception:
        traceback.print_exc()
        raise RuntimeError('Project generator import failed')
    return generate_project(app_idea, project_name)

def test_project(project_name: str):
    """Basic sanity tests: ensure backend .py files compile and required files exist."""
    project_root = WORKSPACE / project_name
    if not project_root.is_dir():
        raise FileNotFoundError(f'Project {project_name} not found in {WORKSPACE}')
    # Compile all .py files in backend
    backend_dir = project_root / 'backend'
    py_files = list(backend_dir.rglob('*.py'))
    for py in py_files:
        try:
            subprocess.run([sys.executable, '-m', 'py_compile', str(py)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Compilation failed for {py}: {e.stderr.decode()}')
    # Simple existence checks for frontend package.json
    frontend_pkg = project_root / 'frontend' / 'package.json'
    if not frontend_pkg.is_file():
        raise FileNotFoundError('frontend/package.json missing')
    print('Basic tests passed.')

def preview_backend(project_name: str, host: str = '127.0.0.1', port: int = 8000):
    """Start the FastAPI backend using uvicorn. This runs in the current process.
    Note: In the sandbox the server is only reachable from the same command; to preview externally run this command outside the sandbox.
    """
    project_root = WORKSPACE / project_name
    backend_main = project_root / 'backend' / 'main.py'
    if not backend_main.is_file():
        raise FileNotFoundError('backend/main.py not found')
    # Add the project root to PYTHONPATH so that imports work.
    sys.path.insert(0, str(project_root / 'backend'))
    # Import the generated FastAPI app.
    spec = importlib.util.spec_from_file_location('generated_main', backend_main)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = getattr(mod, 'app', None)
    if app is None:
        raise RuntimeError('FastAPI app object not found in generated main.py')
    print(f'Starting backend at http://{host}:{port} (Ctrl+C to stop)')
    try:
        import uvicorn
    except ImportError:
        raise NotImplementedError('uvicorn is not installed; cannot preview backend')
    uvicorn.run(app, host=host, port=port)

def preview_frontend(project_name: str, host: str = '127.0.0.1', port: int = 3000):
    """Serve the frontend directory via a simple HTTP server.
    This is a placeholder; for a real dev server use npm/vite.
    """
    project_root = WORKSPACE / project_name
    frontend_dir = project_root / 'frontend'
    if not frontend_dir.is_dir():
        raise FileNotFoundError('frontend directory not found')
    os.chdir(frontend_dir)
    handler = __import__('http.server').SimpleHTTPRequestHandler
    server = __import__('socketserver').TCPServer((host, port), handler)
    print(f'Frontend preview at http://{host}:{port} (Ctrl+C to stop)')
    try:
        server.serve_forever()
    finally:
        server.server_close()

def main():
    parser = argparse.ArgumentParser(prog='e2e-agent', description='End‑to‑End App Development Agent CLI')
    subparsers = parser.add_subparsers(dest='command')

    build_parser = subparsers.add_parser('build', help='Plan, generate and scaffold a project')
    build_parser.add_argument('idea', help='Natural language description of the app')
    build_parser.add_argument('name', help='Project name (no spaces)')

    test_parser = subparsers.add_parser('test', help='Run basic sanity tests on a generated project')
    test_parser.add_argument('name', help='Project name')

    preview_parser = subparsers.add_parser('preview', help='Run a preview server')
    preview_parser.add_argument('name', help='Project name')
    preview_parser.add_argument('--type', choices=['backend', 'frontend'], default='backend', help='Which part to preview')

    args = parser.parse_args()
    if args.command == 'build':
        run_planner(args.idea, args.name)
        generate_path = run_generator(args.idea, args.name)
        print(f'Project generated at {generate_path}')
    elif args.command == 'test':
        test_project(args.name)
    elif args.command == 'preview':
        if args.type == 'backend':
            preview_backend(args.name)
        else:
            preview_frontend(args.name)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

