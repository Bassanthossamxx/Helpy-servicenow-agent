import json
from pathlib import Path

from app.gemini import decide

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "assets" / "test_incidents.json").read_text(encoding="utf-8"))

for case in data["incidents"]:
    # call decide function to call llm
    result = decide(
        short_description=case["short_description"],
        description=case["description"],
        priority=3,
    )
    # save responses
    expected = case["expected_decision"]
    actual = result["decision"]
    # print testing result 
    mark = "PASS" if actual == expected else "FAIL"
    print(f"{mark} | expected={expected} | got={actual}")
    print(f"       {case['short_description']}")
    print(f"       message: {result['message']}\n")