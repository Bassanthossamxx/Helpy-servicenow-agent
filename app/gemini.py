import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.models import Decision

load_dotenv()

logger = logging.getLogger(__name__)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent.parent

# prompt file path and save it in var PROMPT
PROMPT = (ROOT / "prompt.txt").read_text(encoding="utf-8")

# knowledge base, one article per line
ARTICLES = json.loads((ROOT / "assets" / "kb_articles.json").read_text(encoding="utf-8"))["articles"]
KB_TEXT = "\n".join(f"{a['id']}. {a['text']}" for a in ARTICLES)

# start call gemini, timeout in ms so a hung request cannot block us forever
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={"timeout": 30000})


def decide(short_description: str, description: str | None, priority: int) -> Decision:
    prompt = PROMPT.format(
        kb_articles=KB_TEXT,
        short_description=short_description,
        description=description or "",
        priority=priority,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", # can be changeable but this is best option better than lite and less cost than pro
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0, # this temp to choose highest prop so better for classification
                response_mime_type="application/json",
                response_schema=Decision, # gemini validates the shape for us, so no manual parsing
            ),
        )

        # parsed is a Decision, or None if gemini returned something unusable
        return response.parsed or Decision(
            decision="escalate",
            response="Could not decide automatically, needs a human.",
        )

    # error handling for any fall-back in gemini
    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        return Decision(decision="escalate", response="Automatic triage failed, needs a human.")
