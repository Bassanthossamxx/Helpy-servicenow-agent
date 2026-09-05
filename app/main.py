import logging

from fastapi import BackgroundTasks, FastAPI, status

from .gemini import decide
from .models import IncidentPayload
from .servicenow import update_incident

# for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# running app
app = FastAPI(title="Helpy ServiceNow Agent")

# sys_ids already handled, so a retried webhook does not triage the same , in memory handling
processed: set[str] = set()


@app.get("/")
def health():
    return {"status": "it's workingg!!"} # to check everything is fine


def triage(payload: IncidentPayload) -> None:
    # Ask Gemini, then write the answer back on the incident
    try:
        result = decide(
            short_description=payload.short_description,
            description=payload.description,
            priority=payload.priority,
        )
        logger.info("%s -> %s", payload.number, result.decision)

        update_incident(payload.incident_sys_id, result)

    except Exception:
        # nothing was written on the ticket, so let servicenow send it again
        processed.discard(payload.incident_sys_id)
        # never let a background failure kill the service
        logger.exception("Triage failed for %s", payload.number)


# wehook endpoint post for service now
@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
def webhook(payload: IncidentPayload, background_tasks: BackgroundTasks):
    logger.info("Received %s (sys_id=%s)", payload.number, payload.incident_sys_id)

    if payload.incident_sys_id in processed:
        logger.info("Ignoring duplicate %s", payload.number)
        return {"accepted": False, "reason": "already processed"}

    # claim it before the work starts so two webhooks cannot both go through
    processed.add(payload.incident_sys_id)

    # answer ServiceNow straight away, triage in the background
    background_tasks.add_task(triage, payload)
    return {"accepted": True}