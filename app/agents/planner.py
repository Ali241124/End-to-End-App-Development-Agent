
from ollama import chat


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


def create_development_plan(app_idea: str) -> str:
    """Generate a development plan from a user's application idea."""

    if not app_idea.strip():
        raise ValueError("Please provide an application idea.")

    response = chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": app_idea,
            },
        ],
    )

    return response.message.content


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
