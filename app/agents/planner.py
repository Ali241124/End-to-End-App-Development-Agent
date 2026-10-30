
from ollama import chat
import json
from pathlib import Path
from .nlu_extractor import extract_intent


MODEL_NAME = "qwen2.5:7b"


SYSTEM_PROMPT = """
You are an experienced software architect and AI app development agent.

Your job is to turn a user's software idea into a practical development plan.

For every request, provide these sections:

1. Project Overview
2. Core Features
3. Recommended Technology Stack
4. Project Folder Structure
5. Database Design, if needed
6. API Endpoints, if needed
7. Authentication and Security
8. Testing Strategy
9. Deployment Plan
10. Development Steps

Support web apps, full-stack applications, mobile apps, and backend APIs.

Be practical, beginner-friendly, and specific.
Do not claim that code has been created, tested, or deployed.
You are creating a plan only.
"""


def create_development_plan(app_idea: str, project_name: str) -> str:
    """Generate a development plan, persist it, and save the extracted intent.

    * Extract intent via NLU extractor.
    * Enrich system prompt with intent JSON.
    * Write plan to ``generated_projects/<project_name>/DEVELOPMENT_PLAN.md``.
    * Write intent JSON to ``intent.json`` for downstream agents.
    """
    if not app_idea.strip():
        raise ValueError("Please provide an application idea.")

    # 1️⃣ Extract structured intent
    intent = extract_intent(app_idea)
    # 2️⃣ Enrich prompt with intent JSON for deterministic output
    enriched_prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"User intent (JSON) for reference:\n{json.dumps(intent, indent=2)}\n"
    )

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": enriched_prompt},
            {"role": "user", "content": app_idea},
        ],
    )
    plan_text = response.message.content

    # 3️⃣ Persist files
    out_dir = Path("generated_projects") / project_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "DEVELOPMENT_PLAN.md").write_text(plan_text, encoding="utf-8")
    (out_dir / "intent.json").write_text(json.dumps(intent, indent=2), encoding="utf-8")
    return plan_text

if __name__ == "__main__":
    idea = input("Describe the application you want to build: ")

    try:
        plan = create_development_plan(idea)
        print("\n" + "=" * 60)
        print("AI-GENERATED DEVELOPMENT PLAN")
        print("=" * 60)
        print(plan)

    except ValueError as error:
        print(f"Input error: {error}")

    except Exception as error:
        print(f"Could not generate the plan: {error}")
