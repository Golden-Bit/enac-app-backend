# app/models/claim.py
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, root_validator

class StatoSinistro(str, Enum):
    APERTO = "Aperto"
    CHIUSO = "Chiuso"
    SENZA_SEGUITO = "Senza Seguito"
    IN_VALUTAZIONE = "In Valutazione"

class Sinistro(BaseModel):
    # amministrativo base
    esercizio: int = Field(..., description="Anno esercizio")                       # obblig.
    numero_sinistro: str = Field(..., description="Numero sinistro interno")       # obblig.

    # legami denormalizzati / contesto
    compagnia: Optional[str] = Field(None)
    numero_contratto: Optional[str] = Field(None)  # ex numero_polizza
    rischio: Optional[str] = Field(None)
    intermediario: Optional[str] = Field(None)

    # evento
    descrizione_evento: Optional[str] = Field(None)
    data_accadimento: date = Field(..., description="Data accadimento")            # obblig.
    data_denuncia: Optional[date] = Field(None, description="Data di denuncia")
    indirizzo_evento: Optional[str] = Field(None)  # ex indirizzo
    cap: Optional[str] = Field(None)
    citta: Optional[str] = Field(None)            # accetta anche 'città' in input
    targa: Optional[str] = Field(None)
    dinamica: Optional[str] = Field(None)

    # economici
    danno_stimato: Optional[str] = Field(None)     # stringhe numeriche per coerenza API
    importo_riservato: Optional[str] = Field(None)
    importo_liquidato: Optional[str] = Field(None)

    # stato (vincolato)
    stato: Optional[StatoSinistro] = Field(None)

    # opzionale/legacy
    codice_stato: Optional[str] = Field(None)

    @root_validator(pre=True)
    def _compat_legacy_keys(cls, v: dict):
        if not isinstance(v, dict):
            return v
        m = dict(v)

        # alias legacy -> nuovi
        m.setdefault("numero_contratto", m.get("numero_polizza"))
        m.setdefault("descrizione_evento", m.get("descrizione_assicurato"))
        m.setdefault("data_accadimento", m.get("data_avvenimento"))
        m.setdefault("data_denuncia", m.get("data_apertura"))
        m.setdefault("indirizzo_evento", m.get("indirizzo"))

        # città / citta
        if m.get("citta") in (None, ""):
            m["citta"] = m.get("città") or m.get("citta")

        # normalizza stato da 'stato_compagnia'
        if m.get("stato") in (None, "") and m.get("stato_compagnia"):
            raw = str(m["stato_compagnia"]).strip().lower()
            mapping = {
                "aperto": StatoSinistro.APERTO,
                "chiuso": StatoSinistro.CHIUSO,
                "senza seguito": StatoSinistro.SENZA_SEGUITO,
                "in valutazione": StatoSinistro.IN_VALUTAZIONE,
                "valutazione": StatoSinistro.IN_VALUTAZIONE,
                "pendente": StatoSinistro.IN_VALUTAZIONE,
                "da valutare": StatoSinistro.IN_VALUTAZIONE,
            }
            m["stato"] = mapping.get(raw, None)

        return m

    class Config:
        use_enum_values = True  # serializza enum come stringhe


class DiarioEntry(BaseModel):
    autore: str = Field(..., description="Autore/ruolo")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC")
    testo: str = Field(..., description="Contenuto")
