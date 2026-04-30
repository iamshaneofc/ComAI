from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DebugChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    message: str
    timestamp: datetime
