import logging
from fastapi import FastAPI
# for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# running app
app = FastAPI(title="Helpy ServiceNow Agent") 
 
@app.get("/")
def health():
    return {"status": "it's workingg!!"} # to check everything is fine

