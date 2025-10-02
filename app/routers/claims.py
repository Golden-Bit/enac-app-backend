from __future__ import annotations
from typing import List
from fastapi import APIRouter, Body, HTTPException
from app.models.claim import Sinistro
from app.models.responses import DeleteResponse
from app.utils.utils import claim_file, claims_dir, contract_file
from app.utils.utils import atomic_write_json, read_json
from app.services.indexes import rebuild_entity_views
import uuid, shutil

router = APIRouter(prefix="/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims", tags=["Claims"])

@router.post("", response_model=dict)
def create_claim(user_id: str, entity_id: str, contract_id: str, payload: Sinistro = Body(...)):
    cf = contract_file(user_id, entity_id, contract_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Contratto non trovato.")
    contract = read_json(cf)
    payload.numero_polizza = contract["Identificativi"]["NumeroPolizza"]
    payload.compagnia = contract["Identificativi"]["Compagnia"]
    payload.rischio = contract.get("RamiEl", {}).get("Descrizione")
    claim_id = uuid.uuid4().hex
    atomic_write_json(claim_file(user_id, entity_id, contract_id, claim_id), payload.dict())
    rebuild_entity_views(user_id, entity_id)
    return {"claim_id": claim_id, "sinistro": payload}

@router.get("", response_model=List[str])
def list_claims(user_id: str, entity_id: str, contract_id: str):
    return [p.name for p in claims_dir(user_id, entity_id, contract_id).iterdir() if p.is_dir()]

@router.get("/{claim_id}", response_model=Sinistro)
def get_claim(user_id: str, entity_id: str, contract_id: str, claim_id: str):
    cf = claim_file(user_id, entity_id, contract_id, claim_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Sinistro non trovato.")
    return read_json(cf)

@router.put("/{claim_id}", response_model=Sinistro)
def update_claim(user_id: str, entity_id: str, contract_id: str, claim_id: str, payload: Sinistro = Body(...)):
    cf = claim_file(user_id, entity_id, contract_id, claim_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Sinistro non trovato.")
    atomic_write_json(cf, payload.dict()); rebuild_entity_views(user_id, entity_id); return payload

@router.delete("/{claim_id}", response_model=DeleteResponse)
def delete_claim(user_id: str, entity_id: str, contract_id: str, claim_id: str):
    cdir = claims_dir(user_id, entity_id, contract_id) / claim_id
    if not cdir.exists(): raise HTTPException(status_code=404, detail="Sinistro non trovato.")
    shutil.rmtree(cdir); rebuild_entity_views(user_id, entity_id); return DeleteResponse(id=claim_id)
