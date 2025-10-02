from __future__ import annotations
from typing import List
from fastapi import APIRouter, Body, HTTPException, Path as FPath, status
from app.models.entity import Entity
from app.models.responses import DeleteResponse
from app.utils.utils import entity_file, entities_dir, entity_dir
from app.utils.utils import atomic_write_json, read_json
import shutil

router = APIRouter(prefix="/users/{user_id}/entities", tags=["Entities"])
USER_ID_DOC = "ID utente (cartella primo livello)"
ENTITY_ID_DOC = "ID entità"

@router.post("/{entity_id}", response_model=Entity, status_code=status.HTTP_201_CREATED)
def create_entity(user_id: str = FPath(..., description=USER_ID_DOC),
                  entity_id: str = FPath(..., description=ENTITY_ID_DOC),
                  payload: Entity = Body(...)):
    ef = entity_file(user_id, entity_id)
    if ef.exists(): raise HTTPException(status_code=409, detail="Entità già esistente.")
    atomic_write_json(ef, payload.dict()); return payload

@router.get("", response_model=List[str])
def list_entities(user_id: str = FPath(..., description=USER_ID_DOC)):
    return [p.name for p in entities_dir(user_id).iterdir() if p.is_dir()]

@router.get("/{entity_id}", response_model=Entity)
def get_entity(user_id: str = FPath(..., description=USER_ID_DOC),
               entity_id: str = FPath(..., description=ENTITY_ID_DOC)):
    ef = entity_file(user_id, entity_id)
    if not ef.exists(): raise HTTPException(status_code=404, detail="Entità non trovata.")
    return read_json(ef)

@router.put("/{entity_id}", response_model=Entity)
def update_entity(user_id: str = FPath(..., description=USER_ID_DOC),
                  entity_id: str = FPath(..., description=ENTITY_ID_DOC),
                  payload: Entity = Body(...)):
    ef = entity_file(user_id, entity_id)
    if not ef.exists(): raise HTTPException(status_code=404, detail="Entità non trovata.")
    atomic_write_json(ef, payload.dict()); return payload

@router.delete("/{entity_id}", response_model=DeleteResponse)
def delete_entity(user_id: str = FPath(..., description=USER_ID_DOC),
                  entity_id: str = FPath(..., description=ENTITY_ID_DOC)):
    edir = entity_dir(user_id, entity_id)
    if not edir.exists(): raise HTTPException(status_code=404, detail="Entità non trovata.")
    shutil.rmtree(edir); return DeleteResponse(id=entity_id)
