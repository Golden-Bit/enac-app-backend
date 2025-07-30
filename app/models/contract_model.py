"""
Modello dati “Contratto Omnia8”  – versione *generic defaults* (rev. A‑2025‑07‑28)
==========================================================================

Rappresenta la struttura JSON del tab **Dati Amministrativi** della piattaforma
*Omnia 8 – Gestione Contratti/Polizze* eliminando qualunque informazione
riconducibile a persone, aziende o date fiscali reali. Tutti i valori di default
sono ora *place‑holder* generici, utili come esempio e facilmente
sovrascrivibili in fase di popolamento.

• Ogni sezione del form è mappata su un modello Pydantic dedicato.
• Le descrizioni sono mantenute per generare documentazione completa
  (es. swagger / OpenAPI in FastAPI).

Python ≥ 3.9.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
#  Sezione Identificativi (NUOVA)
# ---------------------------------------------------------------------------
class Identificativi(BaseModel):
    """Dati identificativi principali della polizza/contratto."""

    tipo: str = Field(
        "-",
        description="Tipo record/polizza (es. Nuova, Rinnovo, Appendice, ecc.).",
        alias="Tipo",
    )
    tp_car: Optional[str] = Field(
        None,
        description="TP CAR. – tipologia di caricamento o di carattere del contratto.",
        alias="TpCar",
    )
    ramo: str = Field(
        "-",
        description="Codice ramo assicurativo (es. R = Responsabilità civile).",
        alias="Ramo",
    )
    compagnia: str = Field(
        "-",
        description="Compagnia assicuratrice che emette la polizza.",
        alias="Compagnia",
    )
    numero_polizza: str = Field(
        "-",
        description="Numero identificativo della polizza/contratto.",
        alias="NumeroPolizza",
    )


# ---------------------------------------------------------------------------
#  Sezione Unità Vendita
# ---------------------------------------------------------------------------
class UnitaVendita(BaseModel):
    """Informazioni sull’unità di vendita che ha originato il contratto."""

    punto_vendita: str = Field(
        "-",
        description="Codice o denominazione del primo punto vendita (\"-\" se non valorizzato).",
        alias="PuntoVendita",
    )
    punto_vendita2: str = Field(
        "-",
        description="Codice o denominazione del secondo punto vendita (\"-\" se non presente).",
        alias="PuntoVendita2",
    )
    account: str = Field(
        "Account Placeholder",
        description="Referente commerciale interno assegnato al contratto (valore generico).",
        alias="Account",
    )
    intermediario: str = Field(
        "Intermediario Placeholder",
        description="Compagnia o broker che ha intermediato la polizza (valore generico).",
        alias="Intermediario",
    )


# ---------------------------------------------------------------------------
#  Sezione Amministrativi (ESTESA)
# ---------------------------------------------------------------------------
class Amministrativi(BaseModel):
    """Dati amministrativi di base."""

    effetto: date = Field(date.today(), description="Data di effetto del contratto.", alias="Effetto")
    data_emissione: date = Field(date.today(), description="Data di emissione della polizza.", alias="DataEmissione")
    ultima_rata_pagata: date = Field(
        date.today(), description="Data di pagamento dell’ultima rata.", alias="UltRataPagata"
    )
    frazionamento: str = Field(
        "annuale", description="Periodicità di frazionamento del premio.", alias="Frazionamento"
    )
    compreso_firma: bool = Field(False, description="Flag clausola ‘compreso firma’.", alias="CompresoFirma")
    scadenza: date = Field(date.today(), description="Data di scadenza corrente.", alias="Scadenza")
    scadenza_originaria: date = Field(
        date.today(), description="Data di scadenza originaria (pre‑proroga).", alias="ScadenzaOriginaria"
    )
    scadenza_mora: Optional[date] = Field(
        None, description="Data di scadenza post‑mora, se prevista.", alias="ScadenzaMora"
    )
    numero_proposta: Optional[str] = Field(
        None, description="Numero proposta collegato alla polizza.", alias="NumeroProposta"
    )
    modalita_incasso: str = Field(
        "-", description="Modalità di incasso del premio.", alias="ModalitaIncasso"
    )
    cod_convenzione: Optional[str] = Field(
        None, description="Codice convenzione (se presente).", alias="CodConvenzione"
    )
    scadenza_vincolo: Optional[date] = Field(
        None, description="Scadenza di eventuale vincolo sul contratto.", alias="ScadenzaVincolo"
    )
    # ---- Campi aggiunti ----
    scadenza_copertura: Optional[date] = Field(
        None,
        description="Data di fine copertura (SCAD. COPERTURA).",
        alias="ScadenzaCopertura",
    )
    fine_copertura_proroga: Optional[date] = Field(
        None,
        description="Eventuale data di proroga copertura indicata tra parentesi.",
        alias="FineCoperturaProroga",
    )


# ---------------------------------------------------------------------------
#  Sezione Premi
# ---------------------------------------------------------------------------
class Premi(BaseModel):
    """Dettaglio economico del premio."""

    premio: Decimal = Field(
        Decimal("0.00"), description="Premio annuale lordo (placeholder).", alias="Premio"
    )
    netto: Decimal = Field(Decimal("0.00"), description="Premio netto imponibile.", alias="Netto")
    accessori: Decimal = Field(Decimal("0.00"), description="Totale accessori.", alias="Accessori")
    diritti: Decimal = Field(Decimal("0.00"), description="Diritti di emissione.", alias="Diritti")
    imposte: Decimal = Field(Decimal("0.00"), description="Totale imposte.", alias="Imposte")
    spese: Decimal = Field(Decimal("0.00"), description="Spese amministrative.", alias="Spese")
    fondo: Decimal = Field(Decimal("0.00"), description="Contributo fondo garanzia.", alias="Fondo")
    sconto: Optional[Decimal] = Field(
        None, description="Sconto applicato al premio.", alias="Sconto"
    )


# ---------------------------------------------------------------------------
#  Sezione Rinnovo
# ---------------------------------------------------------------------------
class Rinnovo(BaseModel):
    """Informazioni relative al rinnovo contrattuale."""

    rinnovo: str = Field(
        "da definire", description="Tipologia di rinnovo (placeholder).", alias="Rinnovo"
    )
    disdetta: str = Field("-", description="Dettagli disdetta.", alias="Disdetta")
    giorni_mora: str = Field("0 giorni", description="Giorni di mora concessi.", alias="GiorniMora")
    proroga: str = Field("-", description="Eventuale proroga.", alias="Proroga")


# ---------------------------------------------------------------------------
#  Parametri Regolazione (tab Reg. Premio)
# ---------------------------------------------------------------------------
class ParametriRegolazione(BaseModel):
    """Parametri utilizzati per la regolazione del premio."""

    inizio: date = Field(date.today(), description="Data inizio periodo.", alias="Inizio")
    fine: date = Field(date.today(), description="Data fine periodo.", alias="Fine")
    ultima_reg_emessa: Optional[date] = Field(
        None, description="Data ultima regolazione emessa.", alias="UltimaRegEmessa"
    )
    giorni_invio_dati: Optional[int] = Field(
        None, description="Giorni per invio dati.", alias="GiorniInvioDati"
    )
    giorni_pag_reg: Optional[int] = Field(
        None, description="Giorni pagamento regolazione.", alias="GiorniPagReg"
    )
    giorni_mora_regolazione: Optional[int] = Field(
        None, description="Giorni di mora su regolazione.", alias="GiorniMoraRegolazione"
    )
    cadenza_regolazione: str = Field(
        "annuale", description="Frequenza regolazione.", alias="CadenzaRegolazione"
    )


# ---------------------------------------------------------------------------
#  Sezione Operatività
# ---------------------------------------------------------------------------
class Operativita(BaseModel):
    """Opzioni operative del contratto."""

    regolazione: bool = Field(
        False,
        description="True se la polizza prevede regolazione premio.",
        alias="Regolazione",
    )
    parametri_regolazione: ParametriRegolazione = Field(
        default_factory=ParametriRegolazione,
        description="Dettaglio parametri regolazione.",
        alias="ParametriRegolazione",
    )


# ---------------------------------------------------------------------------
#  Tab Rami El. (NON MODIFICATA)
# ---------------------------------------------------------------------------
class RamiEl(BaseModel):
    """Ramo / descrizione di rischio."""

    descrizione: str = Field(
        "Descrizione Generica Rischio",
        description="Descrizione del ramo o estensione di garanzia.",
        alias="Descrizione",
    )


# ---------------------------------------------------------------------------
#  Modello Contratto completo (AGGIORNATO)
# ---------------------------------------------------------------------------
class ContrattoOmnia8(BaseModel):
    """Modello completo di contratto Omnia 8 con valori di default generici."""

    identificativi: Identificativi = Field(default_factory=Identificativi, alias="Identificativi")
    unita_vendita: UnitaVendita = Field(default_factory=UnitaVendita, alias="UnitaVendita")
    amministrativi: Amministrativi = Field(default_factory=Amministrativi, alias="Amministrativi")
    premi: Premi = Field(default_factory=Premi, alias="Premi")
    rinnovo: Rinnovo = Field(default_factory=Rinnovo, alias="Rinnovo")
    operativita: Operativita = Field(default_factory=Operativita, alias="Operativita")
    rami_el: RamiEl = Field(default_factory=RamiEl, alias="RamiEl")

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "Identificativi": {
                    "Tipo": "-",
                    "TpCar": None,
                    "Ramo": "-",
                    "Compagnia": "-",
                    "NumeroPolizza": "-",
                },
                "UnitaVendita": {
                    "PuntoVendita": "-",
                    "PuntoVendita2": "-",
                    "Account": "Account Placeholder",
                    "Intermediario": "Intermediario Placeholder",
                },
                "Amministrativi": {
                    "Effetto": date.today().isoformat(),
                    "DataEmissione": date.today().isoformat(),
                    "UltRataPagata": date.today().isoformat(),
                    "Frazionamento": "annuale",
                    "CompresoFirma": False,
                    "Scadenza": date.today().isoformat(),
                    "ScadenzaOriginaria": date.today().isoformat(),
                    "ScadenzaMora": None,
                    "NumeroProposta": None,
                    "ModalitaIncasso": "-",
                    "CodConvenzione": None,
                    "ScadenzaVincolo": None,
                    "ScadenzaCopertura": None,
                    "FineCoperturaProroga": None,
                },
                "Premi": {
                    "Premio": "0.00",
                    "Netto": "0.00",
                    "Accessori": "0.00",
                    "Diritti": "0.00",
                    "Imposte": "0.00",
                    "Spese": "0.00",
                    "Fondo": "0.00",
                    "Sconto": None,
                },
                "Rinnovo": {
                    "Rinnovo": "da definire",
                    "Disdetta": "-",
                    "GiorniMora": "0 giorni",
                    "Proroga": "-",
                },
                "Operativita": {
                    "Regolazione": False,
                    "ParametriRegolazione": {
                        "Inizio": date.today().isoformat(),
                        "Fine": date.today().isoformat(),
                        "UltimaRegEmessa": None,
                        "GiorniInvioDati": None,
                        "GiorniPagReg": None,
                        "GiorniMoraRegolazione": None,
                        "CadenzaRegolazione": "annuale",
                    },
                },
                "RamiEl": {"Descrizione": "Descrizione Generica Rischio"},
            }
        }


# ---------------------------------------------------------------------------
#  Esempio rapido d’uso (da rimuovere in produzione)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Costruzione con default generici
    contratto = ContrattoOmnia8()

    # Visualizza JSON serializzato con alias
    print(contratto.json(by_alias=True, indent=2))
