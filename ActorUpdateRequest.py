from datetime import date
from typing import Optional
from pydantic import BaseModel


class ActorUpdateRequest(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    