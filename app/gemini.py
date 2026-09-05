import json
import logging
from pathlib import Path
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent.parent

# prompt file path and save it in var PROMPT
prompt_path = ROOT / "prompt.txt"
PROMPT = prompt_path.read_text(encoding="utf-8")

kb_path = ROOT / "assets" / "kb_articles.json"
with open(kb_path, encoding="utf-8") as f:
    kb_data = json.load(f)

ARTICLES = kb_data["articles"]
# get each line then add them to our dynamic var KB_TEXT
lines = []
for article in ARTICLES:
    lines.append(f"{article['id']}. {article['text']}")
KB_TEXT = "\n".join(lines)

# allowed decision values
ALLOWED = {"respond", "ask", "escalate"}

# start call gemini, timeout in ms so a hung request cannot block us forever
client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": 30000})


def decide(short_description: str, description: str | None, priority: int) -> dict:
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
                response_mime_type="application/json", # force json mode
            ),
        )

        text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)

        decision = data.get("decision")

        # error handling for wrong classification
        if decision not in ALLOWED:
            logger.error("Unexpected decision from Gemini: %r", decision)
            return {"decision": "escalate", "message": "Could not decide automatically, needs a human."}

        # final output to use in service now
        return {"decision": decision, "message": str(data.get("message", ""))[:1000]}

    # error handling for any fall-back in gemini
    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        return {"decision": "escalate", "message": "Automatic triage failed, needs a human."}