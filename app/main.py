import logging
from fastapi import FastAPI , status
from .models import IncidentPayload
# for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# running app
app = FastAPI(title="Helpy ServiceNow Agent") 
 
@app.get("/")
def health():
    return {"status": "it's workingg!!"} # to check everything is fine

# wevhook endpoint post for service now 
@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
def webhook(payload: IncidentPayload):
    logger.info("Received %s (sys_id=%s)", payload.number, payload.incident_sys_id)
    return {"accepted": True}