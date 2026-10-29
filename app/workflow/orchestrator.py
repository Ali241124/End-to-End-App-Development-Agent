
from datetime import datetime
from pathlib import Path

from app.agents.planner import create_development_plan
from app.generators.project_generator import generate_project
from app.testing.self_repair import run_self_repair


def save_development_plan(project_path: Path, plan: str) -> Path:
    """Save the planner's output inside the generated project."""

    plan_path = project_path / "DEVELOPMENT_PLAN.md"

    # Never overwrite a file the generator already created.
    if plan_path.exists():
        plan_path = project_path / "DEVELOPMENT_PLAN_AGENT.md"

    plan_path.write_text(
        "# AI Development Plan\n\n"
        f"Generated on: {datetime.now().astimezone().isoformat(timespec='seconds')}\n\n"
        "Note: This plan is AI-generated and has not been independently verified.\n\n"
        f"{plan.strip()}\n",
        encoding="utf-8",
    )

    return plan_path


def run_workflow(app_idea: str) -> dict:
    """
    Run planning, file generation, and static checks in order.

    This workflow does not execute the generated application.
    """

    if not app_idea.strip():
        raise ValueError("Please describe the application you want to build.")

    print("\n" + "=" * 65)
    print("END-TO-END APP DEVELOPMENT AGENT")
    print("=" * 65)

    # Stage 1: create a development plan.
    print("\n[1/4] Creating the development plan...")
    plan = create_development_plan(app_idea)

    if not plan or not plan.strip():
        raise RuntimeError("The planner returned an empty plan.")

    print("\n--- DEVELOPMENT PLAN ---\n")
    print(plan)

    # Require approval before creating files on disk.
    approval = input(
        "\nContinue and generate project files? Type YES to proceed: "
    ).strip()

    if approval != "YES":
        print("\nWorkflow cancelled before file generation.")
        return {
            "status": "cancelled",
            "plan": plan,
            "project_path": None,
            "checks": None,
        }

    # Stage 2: generate the source files.
    print("\n[2/4] Generating project files...")

    generation_request = (
        "APPLICATION IDEA:\n"
        f"{app_idea[:1500]}\n\n"
        "DEVELOPMENT PLAN SUMMARY:\n"
        f"{plan[:3000]}\n\n"
        "Create a minimal, coherent starter project with 3 to 6 files. "
        "Keep source files short and beginner-friendly. Include a README. "
        "Follow the requested technology stack. Do not add optional "
        "features or claim to have run tests."
    )


    project_path = generate_project(generation_request)

    # Stage 3: save the planner's output alongside the project.
    print("\n[3/4] Saving the development plan...")
    plan_path = save_development_plan(project_path, plan)
    print(f"Plan saved to: {plan_path}")

    # Stage 4: static checking and limited repair.
    print("\n[4/4] Checking and attempting repairs...")
    checks = run_self_repair(project_path)

    status = "static_checks_passed" if checks["passed"] else "review_required"

    print("\n" + "=" * 65)
    print("WORKFLOW SUMMARY")
    print("=" * 65)
    print(f"Status: {status}")
    print(f"Project folder: {project_path}")
    print(f"Development plan: {plan_path}")
    print(f"Python files checked: {checks['python_files_checked']}")
    print(f"JSON files checked: {checks['json_files_checked']}")
    print(f"Issues remaining: {len(checks['issues'])}")

    if checks["passed"]:
        print(
            "\nConfigured static checks passed. "
            "The application has NOT been executed or fully tested."
        )
    else:
        print(
            "\nManual review is required. Inspect the reported issues "
            "before attempting to run the generated application."
        )

    return {
        "status": status,
        "plan": plan,
        "project_path": project_path,
        "plan_path": plan_path,
        "checks": checks,
    }


if __name__ == "__main__":
    try:
        idea = input(
            "Describe the application you want to build:\n> "
        ).strip()

        result = run_workflow(idea)

        if result["status"] == "cancelled":
            print("No project files were generated.")

    except KeyboardInterrupt:
        print("\nWorkflow interrupted by the user.")

    except Exception as error:
        print(f"\nWorkflow stopped: {type(error).__name__}: {error}")
        print(
            "Review the error before retrying. "
            "The workflow may have created some files before the failure."
        )
