from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

class Sinistro(BaseModel):
    esercizio: int = Field(..., description="Anno esercizio")                 # obblig.
    numero_sinistro: str = Field(..., description="Numero sinistro interno") # obblig.
    numero_sinistro_compagnia: Optional[str] = Field(None)
    # legami denorm
    numero_polizza: Optional[str] = Field(None)
    compagnia: Optional[str] = Field(None)
    rischio: Optional[str] = Field(None)
    intermediario: Optional[str] = Field(None)
    descrizione_assicurato: Optional[str] = Field(None)
    # avvenimento
    data_avvenimento: date = Field(..., description="Data avvenimento")       # obblig.
    città: Optional[str] = Field(None)
    indirizzo: Optional[str] = Field(None)
    cap: Optional[str] = Field(None)
    provincia: Optional[str] = Field(None)
    codice_stato: Optional[str] = Field(None)
    targa: Optional[str] = Field(None)
    dinamica: Optional[str] = Field(None)
    # stato
    stato_compagnia: Optional[str] = Field(None)
    data_apertura: date = Field(default_factory=date.today)
    data_chiusura: Optional[date] = Field(None)

class DiarioEntry(BaseModel):
    autore: str = Field(..., description="Autore/ruolo")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC")
    testo: str = Field(..., description="Contenuto")
