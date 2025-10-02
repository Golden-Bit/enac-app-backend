from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Body, HTTPException
from app.models.title import Titolo
from app.models.responses import DeleteResponse
from app.utils.utils import titles_dir, title_file, contract_file
from app.utils.utils import atomic_write_json, read_json
from app.services.indexes import rebuild_entity_views
import uuid

router = APIRouter(prefix="/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles", tags=["Titles"])

@router.post("", response_model=dict)
def create_title(user_id: str, entity_id: str, contract_id: str, payload: Titolo = Body(...)):
    cf = contract_file(user_id, entity_id, contract_id)
    if not cf.exists(): raise HTTPException(status_code=404, detail="Contratto non trovato.")
    contract = read_json(cf)
    payload.numero_polizza = contract["Identificativi"]["NumeroPolizza"]
    payload.entity_id = entity_id
    title_id = uuid.uuid4().hex
    atomic_write_json(title_file(user_id, entity_id, contract_id, title_id), payload.dict())
    rebuild_entity_views(user_id, entity_id)
    return {"title_id": title_id, "titolo": payload}

@router.get("", response_model=List[str])
def list_titles(user_id: str, entity_id: str, contract_id: str):
    return [p.stem for p in titles_dir(user_id, entity_id, contract_id).rglob("*.json") if p.parent.name != "documents"]

@router.get("/{title_id}", response_model=Titolo)
def get_title(user_id: str, entity_id: str, contract_id: str, title_id: str):
    tf = title_file(user_id, entity_id, contract_id, title_id)
    if not tf.exists(): raise HTTPException(status_code=404, detail="Titolo non trovato.")
    return read_json(tf)

@router.put("/{title_id}", response_model=Titolo)
def update_title(user_id: str, entity_id: str, contract_id: str, title_id: str, payload: Titolo = Body(...)):
    tf = title_file(user_id, entity_id, contract_id, title_id)
    if not tf.exists(): raise HTTPException(status_code=404, detail="Titolo non trovato.")
    atomic_write_json(tf, payload.dict()); rebuild_entity_views(user_id, entity_id); return payload

@router.delete("/{title_id}", response_model=DeleteResponse)
def delete_title(user_id: str, entity_id: str, contract_id: str, title_id: str):
    tf = title_file(user_id, entity_id, contract_id, title_id)
    if not tf.exists(): raise HTTPException(status_code=404, detail="Titolo non trovato.")
    tf.unlink(); rebuild_entity_views(user_id, entity_id); return DeleteResponse(id=title_id)
