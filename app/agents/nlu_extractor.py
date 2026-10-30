"""Simple NLU extractor for user prompts.

The extractor turns a free‑form description of an application into a structured
JSON‑compatible dictionary that downstream agents can rely on.  It is deliberately
lightweight – a rule‑based implementation that can be replaced later with a
small LLM if desired.
"""

import json
import re
from typing import Dict, List


def _extract_features(text: str) -> List[str]:
    """Extract bullet‑point style features from the prompt.

    Lines that start with a hyphen or asterisk are treated as features.
    """
    features: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            features.append(line.lstrip("-*").strip())
    return features


def extract_intent(prompt: str) -> Dict[str, object]:
    """Return a dict with the keys expected by the planner.

    The fields are:
    * ``purpose`` – a short one‑sentence description (first non‑empty line).
    * ``target_users`` – placeholder – can be refined later.
    * ``features`` – list of extracted bullet‑point features.
    * ``tech_preferences`` – a dict with default choices for frontend,
      backend and database.  These can be overridden in the prompt with
      keywords like "React", "FastAPI", "PostgreSQL" etc.
    """
    # Determine purpose – first non‑empty line
    purpose = ""
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped:
            purpose = stripped
            break

    # Basic feature extraction
    features = _extract_features(prompt)
    if not features:
        # Fallback: split on commas if no bullet points
        if "," in purpose:
            features = [f.strip() for f in purpose.split(",") if f.strip()]
        else:
            features = []

    # Detect tech hints – very simple keyword search
    tech = {
        "frontend": "React + Vite",
        "backend": "FastAPI",
        "db": "SQLite",
    }
    lowered = prompt.lower()
    if "react" in lowered:
        tech["frontend"] = "React + Vite"
    if "next" in lowered:
        tech["frontend"] = "Next.js"
    if "flask" in lowered:
        tech["backend"] = "Flask"
    if "django" in lowered:
        tech["backend"] = "Django"
    if "postgres" in lowered or "postgresql" in lowered:
        tech["db"] = "PostgreSQL"
    if "sqlite" in lowered:
        tech["db"] = "SQLite"

    intent = {
        "purpose": purpose,
        "target_users": "general audience",
        "features": features,
        "tech_preferences": tech,
    }
    return intent


if __name__ == "__main__":
    import sys
    print(json.dumps(extract_intent(sys.stdin.read()), indent=2))

