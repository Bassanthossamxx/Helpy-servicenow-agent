from pydantic import BaseModel, Field


class IncidentPayload(BaseModel):
    incident_sys_id: str
    number: str
    short_description: str = Field(max_length=160) # small desc 
    description: str | None="" # can be empty 
    priority: int = Field(ge=1, le=5) # from json 1 to 5
    