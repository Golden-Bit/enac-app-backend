from __future__ import annotations
from typing import List
from fastapi import APIRouter, Body, HTTPException
from app.models.contract import ContrattoOmnia8
from app.models.responses import DeleteResponse
from app.utils.utils import contracts_dir, contract_dir, contract_file, entity_file
from app.utils.utils import atomic_write_json, read_json
from app.services.indexes import update_by_policy_index, rebuild_entity_views
import uuid, shutil

router = APIRouter(prefix="/users/{user_id}/entities/{entity_id}/contracts", tags=["Contracts"])

@router.post("", response_model=dict)
def create_contract(user_id: str, entity_id: str, payload: ContrattoOmnia8 = Body(...)):
    if not entity_file(user_id, entity_id).exists():
        raise HTTPException(status_code=404, detail="Entità non trovata.")
    contract_id = uuid.uuid4().hex
    atomic_write_json(contract_file(user_id, entity_id, contract_id), payload.dict(by_alias=True))
    update_by_policy_index(user_id, payload.identificativi.numero_polizza, entity_id, contract_id)
    rebuild_entity_views(user_id, entity_id)
    return {"contract_id": contract_id, "contratto": payload}

@router.get("", response_model=List[str])
def list_contracts(user_id: str, entity_id: str):
    if not entity_file(user_id, entity_id).exists():
        raise HTTPException(status_code=404, detail="Entità non trovata.")
    return [p.name for p in contracts_dir(user_id, entity_id).iterdir() if p.is_dir()]

@router.get("/{contract_id}", response_model=ContrattoOmnia8)
def get_contract(user_id: str, entity_id: str, contract_id: str):
    cf = contract_file(user_id, entity_id, contract_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Contratto non trovato.")
    return read_json(cf)

@router.put("/{contract_id}", response_model=ContrattoOmnia8)
def update_contract(user_id: str, entity_id: str, contract_id: str, payload: ContrattoOmnia8 = Body(...)):
    cf = contract_file(user_id, entity_id, contract_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Contratto non trovato.")
    atomic_write_json(cf, payload.dict(by_alias=True))
    update_by_policy_index(user_id, payload.identificativi.numero_polizza, entity_id, contract_id)
    rebuild_entity_views(user_id, entity_id)
    return payload

@router.delete("/{contract_id}", response_model=DeleteResponse)
def delete_contract(user_id: str, entity_id: str, contract_id: str):
    cdir = contract_dir(user_id, entity_id, contract_id)
    if not cdir.exists(): raise HTTPException(status_code=404, detail="Contratto non trovato.")
    shutil.rmtree(cdir); rebuild_entity_views(user_id, entity_id)
    return DeleteResponse(id=contract_id)
