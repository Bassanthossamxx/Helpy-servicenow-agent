import logging
import requests
from app.config import SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD

logger = logging.getLogger(__name__)

AUTH = (SERVICENOW_USERNAME, SERVICENOW_PASSWORD) # our secret envs
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


# build the body for each decision, fields come from pdi_guide.md
def build_body(decision: str, message: str) -> dict:

    if decision == "respond":
        return {
            "work_notes": message,
            "close_notes": message,
            "close_code": "Solved (Permanently)",
            "state": "6",  # resolved
        }
    if decision == "ask":
        return {"comments": message}  # comments are customer visible

    return {"work_notes": message}  # escalate, internal note "work_notes" only


def write_back(incident_sys_id: str, decision: str, message: str) -> bool:
    url = f"{SERVICENOW_INSTANCE_URL}/api/now/table/incident/{incident_sys_id}" # service-now endpoint
    body = build_body(decision, message)

    try:
        response = requests.patch(url, json=body, auth=AUTH, headers=HEADERS, timeout=30) #call endpoint

    except Exception as exc:
        logger.error("ServiceNow request failed: %s", exc)
        return False

    # check status of service now for error handling
    if response.status_code != 200:
        logger.error("ServiceNow returned %s: %s", response.status_code, response.text[:300])
        return False
    # final result
    logger.info("Updated %s with decision %s", incident_sys_id, decision)
    return True