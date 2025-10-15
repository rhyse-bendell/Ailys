from pydantic import BaseModel
from typing import Optional, Literal, Dict
from datetime import datetime

EventType = Literal["created","edited","commented","renamed","moved","copied","deleted"]

class Artifact(BaseModel):
    id: str
    path: str
    type: str            # "text","pdf","docx","md","json","diagram","other"
    title: Optional[str] = None
    created_at: Optional[datetime] = None

class Event(BaseModel):
    id: str
    source: str          # "filesystem","git","export","changelog"
    event_type: EventType
    artifact_id: str
    version_id: str
    actor: Optional[str] = None
    ts: datetime
    raw: Dict

class Delta(BaseModel):
    id: str
    version_id: str
    kind: str            # "text_edit","json_change","diagram_change","format","log_entry"
    summary: str
    payload_json: Dict
