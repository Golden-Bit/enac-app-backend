from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field

class TitleType:
    RATA="RATA"; QUIETANZA="QUIETANZA"; APPENDICE="APPENDICE"; VARIAZIONE="VARIAZIONE"

class TitleStatus:
    DA_PAGARE="DA_PAGARE"; PAGATO="PAGATO"; ANNULLATO="ANNULLATO"; INSOLUTO="INSOLUTO"

class Frazionamento:
    ANNUALE="ANNUALE"; SEMESTRALE="SEMESTRALE"; TRIMESTRALE="TRIMESTRALE"; MENSILE="MENSILE"

class Titolo(BaseModel):
    # obbligatori
    tipo: Literal["RATA","QUIETANZA","APPENDICE","VARIAZIONE"] = Field(..., description="Tipo titolo")
    effetto_titolo: date = Field(..., description="Data effetto titolo")
    scadenza_titolo: date = Field(..., description="Data scadenza titolo")
    # opzionali / economici
    descrizione: Optional[str] = Field(None)
    progressivo: Optional[str] = Field(None)
    stato: Literal["DA_PAGARE","PAGATO","ANNULLATO","INSOLUTO"] = Field("DA_PAGARE")
    imponibile: Decimal = Field(Decimal("0.00"))
    premio_lordo: Decimal = Field(Decimal("0.00"))
    imposte: Decimal = Field(Decimal("0.00"))
    accessori: Decimal = Field(Decimal("0.00"))
    diritti: Decimal = Field(Decimal("0.00"))
    spese: Decimal = Field(Decimal("0.00"))
    frazionamento: Literal["ANNUALE","SEMESTRALE","TRIMESTRALE","MENSILE"] = Field("ANNUALE")
    giorni_mora: int = Field(0)
    cig: Optional[str] = Field(None)
    pv: Optional[str] = Field(None)
    pv2: Optional[str] = Field(None)
    quietanza_numero: Optional[str] = Field(None)
    data_pagamento: Optional[date] = Field(None)
    metodo_incasso: Optional[str] = Field(None)
    # denormalizzazioni
    numero_polizza: Optional[str] = Field(None)
    entity_id: Optional[str] = Field(None)
