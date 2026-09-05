# Helpy — ServiceNow Agent

Helpy is an AI agent that automates support tickets on [ServiceNow](https://www.servicenow.com).

Normally a support ticket waits in a queue until a human opens it, reads it, searches the
knowledge base and answers. Most of the time the answer is already written somewhere, the
ticket is only waiting for someone to be free. Helpy does that part by itself. The moment a
ticket is created it reads it, looks at the knowledge base, and decides what to do: answer it
and close it, ask the user for the one detail that is missing, or leave it for a human when
nothing in the knowledge base covers it.

I named it **Helpy** because that is what it does, it helps the person who opened the ticket without needing a human, and it does it in about 1 minute instead of hours.

Nothing in the loop is manual. Someone submits a ticket, and the answer is already on it when they look again.

## The three decisions

Helpy answers only from the knowledge base in `assets/kb_articles.json`, never from general knowledge. Every ticket ends as one of these:

| Decision | When | What lands on the ticket |
|----------|------|--------------------------|
| `respond` | an article covers the problem and the ticket has enough detail | the solution in `work_notes` and `close_notes`, state set to Resolved |
| `ask` | an article is on the topic but the ticket is too vague to be sure | one clarifying question in `comments`, customer visible, ticket stays open |
| `escalate` | no article covers it | short `work_notes` saying why a human is needed, ticket stays open |

If Gemini fails or answers something unusable, the decision falls back to `escalate`, so a ticket is never left without a note.

---

# Setup

## 1. What you need

- Python 3.11+
- a free ServiceNow developer instance (PDI) from [developer.servicenow.com](https://developer.servicenow.com)
- a free Gemini API key from [aistudio.google.com](https://aistudio.google.com), no credit card needed
- an ngrok account from [ngrok.com](https://ngrok.com)

## 2. Clone and install

```bash
git clone https://github.com/Bassanthossamxx/Helpy-servicenow-agent.git
cd Helpy-servicenow-agent

python -m venv .venv
.venv\Scripts\Activate.ps1        # windows powershell
# source .venv/bin/activate       # mac / linux

pip install -r requirements.txt
```

## 3. Own your PDI

1. Create an account on [developer.servicenow.com](https://developer.servicenow.com), sign in
   and click **Request Instance**.
2. After a few minutes you get your instance URL, like `https://devXXXXXX.service-now.com`,
   with an `admin` user and a password.
3. Open the URL and log in as `admin` in the UI.

A PDI goes to sleep after a few hours of no use. If it looks down, wake it up from the
developer portal.

## 4. Give your admin account the right roles

Do this before anything else. Basic auth was not working for me at first, and this is what fixed it. Being `admin` in the UI is not enough, the REST API needs its own roles.

In your instance:

1. Open **All** and search for **Users**.
2. In the list search, put `admin` in the **User ID** column and open that user.
3. Untick **Password reset required**. While that is on, the API keeps answering 401 even with the correct password.
4. In the **Roles** tab click **Edit** and add these:

```
admin
security_admin
snc_basic_auth_api_access
snc_required_script_writer_permission
snc_platform_rest_api_access
```

5. Save.

## 5. Fill in .env

Copy the example file and fill it in. `.env` is git ignored, so no secret ever goes into the repo.

```bash
cp .env.example .env
```

| Variable | Where to get it |
|----------|-----------------|
| `SERVICENOW_INSTANCE_URL` | your instance URL, like `https://devXXXXXX.service-now.com` |
| `SERVICENOW_USERNAME` | always `admin` on a PDI |
| `SERVICENOW_PASSWORD` | developer portal, your instance card, three dot menu, **Manage instance password** |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |

Check the credentials before going further:

```bash
python -c "import requests,app.servicenow as s;print(requests.get(s.SERVICENOW_URL+'/api/now/table/incident',auth=(s.S_USERNAME,s.S_PASSWORD),headers={'Accept':'application/json'},params={'sysparm_limit':1}).status_code)"
```

`200` means you are good. `401` means the password is wrong, or the roles in step 4 are missing.

## 6. Run the service

```bash
uvicorn app.main:app --reload --port 8000
```

Check it is alive:

```bash
curl http://127.0.0.1:8000/
# {"status":"it's workingg!!"}
```

Interactive docs are on http://127.0.0.1:8000/docs.

## 7. Expose it with ngrok

The service runs on your laptop, so ServiceNow has no way to reach it. ngrok gives it a public
URL.

1. Create a free account on [ngrok.com](https://ngrok.com) and download it.
2. Copy your authtoken from the dashboard and run `ngrok config add-authtoken <your token>`
   once.
3. Make sure the command is available, `ngrok version` should print a version. On windows,
   either add the folder to PATH or run it from that folder.
4. Start it on the **same port** the service is running on:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` line, that is your public URL.

The service and ngrok have to be on the same port. No port is special, any free one works, so if ngrok complains or the tunnel does not answer, changing the port on both sides is the first thing to try. I moved to 8010 because Docker had already taken 8000 on my machine.

ngrok gives a new URL every time it restarts, so the Business Rule `business_rule.js` in the next step has to be updated each time

## 8. Add the Business Rule

This is what makes ServiceNow send new tickets to Helpy

1. In your PDI open **All** and search for **Business Rules** (under System Definition), then
   click **New**.
2. Fill in:
   - **Name**: `Task0 - Send Incident to Agent`
   - **Table**: `Incident [incident]`
   - **Advanced**: ticked, this is what shows the Advanced tab
3. Open **When to run**: When = `after`, and tick **Insert**.
4. Open **Advanced** and paste the script from `assets/business_rule.js`.
5. In the script, replace the URL in `setEndpoint` with your ngrok URL, keeping `/webhook` at
   the end, like `https://xxxx.ngrok-free.app/webhook`.
6. **Submit** : Now your work is automated.

---

# How it works

You create a new incident, from the ServiceNow UI or by posting to the ServiceNow incident endpoint, then you write a short description and submit.

 The system is running in the background and takes it from there:

1. The Business Rule fires on insert and posts the ticket to `/webhook` as JSON.
2. Helpy answers `202` immediately so ServiceNow is not kept waiting, and does the real work in the background.
3. It calls the LLM with the prompt and the knowledge base, and the LLM decides. The answer comes back as JSON with an enum, `respond` / `ask` / `escalate`, and a message.
4. Helpy updates the same ticket with that message, and closes it when the decision is `respond`.

The whole thing is under 2 minutes end to end. The user submits, and gets an answer, without anyone touching the ticket.

## Test it

Create an incident in the PDI and watch the terminal. The three tickets in
`assets/test_incidents.json` are the ones that have to work:

| Short description | Description | Expected |
|-------------------|-------------|----------|
| Printer not printing after office move | It was working yesterday. I tried turning it off and on. | `respond`, ticket resolved |
| Cannot send email | It just doesn't work. | `ask`, question in comments |
| Request: annual leave approval | I would like to take next week off. | `escalate`, work note |

you have logger and  looks like this:

```
INFO:app.main:Received INC0010007 (sys_id=782263c3838f8310822b5a55eeaad35a)
INFO:     "POST /webhook HTTP/1.1" 202 Accepted
INFO:app.main:INC0010007 -> respond
```

Screenshots of each ticket after triage are in [docs/incidents](docs/incidents), and the Business Rule setup is in [docs/business-rule](docs/business-rule).

You can also check the LLM on its own, without ServiceNow:

```bash
python tests/test_llm.py
```

---

# The code

## Project structure

```
app/          all the service code
assets/       the data given with the task
tests/        one test per step, to debug each piece on its own
docs/         screenshots, and any document needed later
prompt.txt    the prompt, exactly as the service sends it
requirements.txt
.env.example
.gitignore
```

Everything is split by what it is, so each piece can be opened and fixed on its own without reading the rest.

- **app/** is the only place with code that runs the service.
- **assets/** is the data that came with the task.
- **tests/** is there to debug each step separately. When the loop breaks you need to know if it was ServiceNow, the LLM, or the service.
- **docs/** holds the screenshots and anything documented later.
- **prompt.txt** is kept outside the code because the prompt is dynamic. The knowledge base and the ticket are formatted into it at runtime, and it can be changed and tested without touching Python.
- **.env.example** lists the variable names with empty values, so anyone cloning the repo knows exactly what to fill in.
- **.gitignore** keeps `.env` out of the repo, so no key or password is ever pushed, and keeps the virtual environment and caches out of it too.
- **requirements.txt** is the dependency list, and it is a security requirement as much as a convenience, the versions are pinned so everyone runs the same ones. After installing anything new, update it with `pip freeze > requirements.txt`.

## The assets

| File | What it is |
|------|------------|
| `kb_articles.json` | the five knowledge base articles, the only thing the LLM is allowed to answer from |
| `business_rule.js` | the script that goes in the Business Rule and sends the ticket to the service |
| `payload_contract.json` | the exact JSON the service receives, field by field |
| `test_incidents.json` | the three test tickets and the decision each one must produce |
| `pdi_guide.md` | the ServiceNow setup guide |

## app/models.py

Two pydantic models, one for each direction:

- `IncidentPayload` is what comes in from ServiceNow, the five fields from the payload
  contract. Pydantic validates them, so a missing field or a priority outside 1 to 5 is
  rejected with `422` before any work starts.
- `Decision` is what the LLM answers, a `Literal` of `ask` / `respond` / `escalate` plus the
  message. Making the decision a `Literal` means an invalid decision cannot exist in the code
  at all.

## app/gemini.py

Builds the prompt and asks the LLM. It loads `prompt.txt` and `kb_articles.json` once at startup, then formats the ticket into the prompt for every call.

1- I used **Gemini 2.5 Flash**, it is free, fast, and good enough for classifying a ticket.

2- Temperature is `0` so the same ticket always gives the same decision, which matters for a classification like this.

The `Decision` model is passed to the API as the response schema, so Gemini validates its own answer and returns the object directly. There is no JSON parsing, no code fences to strip, and no way to get back a decision outside the three. If the call fails for any reason it returns `escalate` instead of raising, so a ticket always ends with something written on it.

## app/servicenow.py

Writes the answer back on the ticket with the ServiceNow REST API, a `PATCH` on `/api/now/table/incident/{sys_id}` with basic auth.

Each decision writes different fields, and that is the whole difference between them:

- `respond` writes the solution in `work_notes` and `close_notes`, and sets the state to
  Resolved with a close code.
- `ask` writes the question in `comments`, which is the customer visible field, so the user
  actually sees it.
- `escalate` writes a note in `work_notes`, which is internal, so the support team sees why it
  needs a human and the user is not told anything confusing.

## app/main.py

The bridge, and the only part that knows about all the others. It is the FastAPI service with
the `/webhook` endpoint that ServiceNow calls.

It does three things:

**Answers fast, works after.** `/webhook` validates the payload and returns `202` straight
away, then runs the LLM call and the write back in a background task. Gemini takes a few
seconds and ServiceNow should not be kept waiting.

**Never handles the same ticket twice.** The sys_id goes into a set in memory. It is added
before the background work starts, so two webhooks arriving at the same moment cannot both go
through, and it is removed again if the work fails, so a ticket that failed on a Gemini or
ServiceNow error can still be retried. The set is empty again after a restart.

**Never crashes.** Any failure in the background task is logged and swallowed, so one bad
ticket cannot take the service down for the next one.

---

# Next steps

- Add more knowledge base articles, so more tickets can be answered instead of escalated.
- Integrate the ticket endpoints properly, creating with `POST` and removing with `DELETE`, so
  tickets can be managed from the service itself.
- A full UI for submitting tickets and tracking them, so the user does not need the ServiceNow
  interface at all.

---

# Troubleshooting

**Nothing arrives when you create a ticket.** Check the ngrok window for a `POST /webhook`
line. If it is not there, the Business Rule did not fire or is pointing at an old ngrok URL.
In the PDI open System Logs > System Log > All and search for `Task0`, the script writes its own log lines there.

**401 on the write back.** The password is wrong, or the roles in step 4 are missing. The REST API Explorer in the browser can still work at the same time, because it uses your browser session and not the password, so it is not proof that basic auth works.

**You changed `.env` and nothing changed.** Restart uvicorn. `.env` is read once when the app starts, and `--reload` only watches `.py` files.

**Port already in use, or `WinError 10013` on windows.** Something else has the port, Docker takes 8000 for example. Use another port and give ngrok the same one.

**429 from Gemini.** The free quota is per project and per model, so a new key in the same
project does not help. Use a different model or wait for the daily reset.

**The instance returns a login page.** The PDI is asleep, wake it up from the developer portal.

---

All rights reserved ©BassantHossam — bassanthosamm1@outlook.com
