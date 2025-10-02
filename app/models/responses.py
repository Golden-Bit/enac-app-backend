from __future__ import annotations
from pydantic import BaseModel, Field

class DeleteResponse(BaseModel):
    deleted: bool = Field(True)
    id: str
