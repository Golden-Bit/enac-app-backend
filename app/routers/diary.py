from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Body, HTTPException
from app.models.claim import DiarioEntry
from app.utils.utils import diary_dir, diary_file, claim_file
from app.utils.utils import atomic_write_json, read_json
import uuid

router = APIRouter(prefix="/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary", tags=["Claims"])

@router.post("", response_model=dict)
def add_diary_entry(user_id: str, entity_id: str, contract_id: str, claim_id: str, payload: DiarioEntry = Body(...)):
    if not claim_file(user_id, entity_id, contract_id, claim_id).exists():
        raise HTTPException(status_code=404, detail="Sinistro non trovato.")
    entry_id = uuid.uuid4().hex
    atomic_write_json(diary_file(user_id, entity_id, contract_id, claim_id, entry_id), payload.dict())
    return {"id": entry_id}

@router.get("", response_model=List[Dict[str, Any]])
def list_diary_entries(user_id: str, entity_id: str, contract_id: str, claim_id: str):
    ddir = diary_dir(user_id, entity_id, contract_id, claim_id)
    if not ddir.exists(): return []
    items = []
    for f in sorted(ddir.glob("*.json")):
        e = read_json(f); e["entry_id"] = f.stem; items.append(e)
    return items

@router.get("/{entry_id}", response_model=Dict[str, Any])
def get_diary_entry(user_id: str, entity_id: str, contract_id: str, claim_id: str, entry_id: str):
    f = diary_file(user_id, entity_id, contract_id, claim_id, entry_id)
    if not f.exists(): raise HTTPException(status_code=404, detail="Nota diario non trovata.")
    e = read_json(f); e["entry_id"] = entry_id; return e

@router.put("/{entry_id}", response_model=Dict[str, Any])
def update_diary_entry(user_id: str, entity_id: str, contract_id: str, claim_id: str, entry_id: str, payload: DiarioEntry = Body(...)):
    f = diary_file(user_id, entity_id, contract_id, claim_id, entry_id)
    if not f.exists(): raise HTTPException(status_code=404, detail="Nota diario non trovata.")
    atomic_write_json(f, payload.dict()); return {"entry_id": entry_id, **payload.dict()}

@router.delete("/{entry_id}", response_model=dict)
def delete_diary_entry(user_id: str, entity_id: str, contract_id: str, claim_id: str, entry_id: str):
    f = diary_file(user_id, entity_id, contract_id, claim_id, entry_id)
    if not f.exists(): raise HTTPException(status_code=404, detail="Nota diario non trovata.")
    f.unlink(); return {"deleted": True, "id": entry_id}
