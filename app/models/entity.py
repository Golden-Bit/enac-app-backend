from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    name: str = Field(..., description="Ragione sociale o nome completo")  # obblig.
    address: Optional[str] = Field(None, description="Indirizzo")
    tax_code: Optional[str] = Field(None, description="Codice fiscale")
    vat: Optional[str] = Field(None, description="Partita IVA")
    phone: Optional[str] = Field(None, description="Telefono")
    email: Optional[str] = Field(None, description="Email")
    sector: Optional[str] = Field(None, description="ATECO / settore")
    legal_rep: Optional[str] = Field(None, description="Legale rappresentante")
    legal_rep_tax_code: Optional[str] = Field(None, description="CF legale rapp.")
    admin_data: Dict[str, Any] = Field(default_factory=dict, description="Dati amministrativi liberi")
