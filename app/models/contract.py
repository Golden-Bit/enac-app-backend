from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class Identificativi(BaseModel):
    tipo: str = Field("-", alias="Tipo")
    tp_car: Optional[str] = Field(None, alias="TpCar")
    ramo: str = Field("-", alias="Ramo")
    compagnia: str = Field(..., alias="Compagnia")           # obblig.
    numero_polizza: str = Field(..., alias="NumeroPolizza")  # obblig.

class UnitaVendita(BaseModel):
    punto_vendita: str = Field("-", alias="PuntoVendita")
    punto_vendita2: str = Field("-", alias="PuntoVendita2")
    account: str = Field("Account Placeholder", alias="Account")
    intermediario: str = Field("Intermediario Placeholder", alias="Intermediario")

class Amministrativi(BaseModel):
    effetto: date = Field(default_factory=date.today, alias="Effetto")
    data_emissione: date = Field(default_factory=date.today, alias="DataEmissione")
    ultima_rata_pagata: date = Field(default_factory=date.today, alias="UltRataPagata")
    frazionamento: str = Field("annuale", alias="Frazionamento")
    compreso_firma: bool = Field(False, alias="CompresoFirma")
    scadenza: date = Field(default_factory=date.today, alias="Scadenza")
    scadenza_originaria: date = Field(default_factory=date.today, alias="ScadenzaOriginaria")
    scadenza_mora: Optional[date] = Field(None, alias="ScadenzaMora")
    numero_proposta: Optional[str] = Field(None, alias="NumeroProposta")
    modalita_incasso: str = Field("-", alias="ModalitaIncasso")
    cod_convenzione: Optional[str] = Field(None, alias="CodConvenzione")
    scadenza_vincolo: Optional[date] = Field(None, alias="ScadenzaVincolo")
    scadenza_copertura: Optional[date] = Field(None, alias="ScadenzaCopertura")
    fine_copertura_proroga: Optional[date] = Field(None, alias="FineCoperturaProroga")

class Premi(BaseModel):
    premio: Decimal = Field(Decimal("0.00"), alias="Premio")
    netto: Decimal = Field(Decimal("0.00"), alias="Netto")
    accessori: Decimal = Field(Decimal("0.00"), alias="Accessori")
    diritti: Decimal = Field(Decimal("0.00"), alias="Diritti")
    imposte: Decimal = Field(Decimal("0.00"), alias="Imposte")
    spese: Decimal = Field(Decimal("0.00"), alias="Spese")
    fondo: Decimal = Field(Decimal("0.00"), alias="Fondo")
    sconto: Optional[Decimal] = Field(None, alias="Sconto")

class Rinnovo(BaseModel):
    rinnovo: str = Field("da definire", alias="Rinnovo")
    disdetta: str = Field("-", alias="Disdetta")
    giorni_mora: str = Field("0 giorni", alias="GiorniMora")
    proroga: str = Field("-", alias="Proroga")

class ParametriRegolazione(BaseModel):
    inizio: date = Field(default_factory=date.today, alias="Inizio")
    fine: date = Field(default_factory=date.today, alias="Fine")
    ultima_reg_emessa: Optional[date] = Field(None, alias="UltimaRegEmessa")
    giorni_invio_dati: Optional[int] = Field(None, alias="GiorniInvioDati")
    giorni_pag_reg: Optional[int] = Field(None, alias="GiorniPagReg")
    giorni_mora_regolazione: Optional[int] = Field(None, alias="GiorniMoraRegolazione")
    cadenza_regolazione: str = Field("annuale", alias="CadenzaRegolazione")

class Operativita(BaseModel):
    regolazione: bool = Field(False, alias="Regolazione")
    parametri_regolazione: ParametriRegolazione = Field(default_factory=ParametriRegolazione, alias="ParametriRegolazione")

class RamiEl(BaseModel):
    descrizione: str = Field("Descrizione Generica Rischio", alias="Descrizione")

class ContrattoOmnia8(BaseModel):
    identificativi: Identificativi = Field(..., alias="Identificativi")
    unita_vendita: UnitaVendita = Field(default_factory=UnitaVendita, alias="UnitaVendita")
    amministrativi: Amministrativi = Field(default_factory=Amministrativi, alias="Amministrativi")
    premi: Premi = Field(default_factory=Premi, alias="Premi")
    rinnovo: Rinnovo = Field(default_factory=Rinnovo, alias="Rinnovo")
    operativita: Operativita = Field(default_factory=Operativita, alias="Operativita")
    rami_el: RamiEl = Field(default_factory=RamiEl, alias="RamiEl")

    class Config:
        allow_population_by_field_name = True
