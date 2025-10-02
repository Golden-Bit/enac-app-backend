from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from app.services.indexes import rebuild_entity_views, compute_due_indexes
from app.utils.utils import views_dir_for_entity, by_policy_dir
from app.utils.utils import read_json

router = APIRouter(tags=["Views"])

@router.get("/users/{user_id}/entities/{entity_id}/titles", response_model=List[Dict[str, Any]], summary="Vista titoli per Entità")
def view_entity_titles(user_id: str, entity_id: str):
    f = views_dir_for_entity(user_id, entity_id) / "titles_index.json"
    if not f.exists(): rebuild_entity_views(user_id, entity_id)
    return read_json(f) if f.exists() else []

@router.get("/users/{user_id}/entities/{entity_id}/claims", response_model=List[Dict[str, Any]], summary="Vista sinistri per Entità")
def view_entity_claims(user_id: str, entity_id: str):
    f = views_dir_for_entity(user_id, entity_id) / "claims_index.json"
    if not f.exists(): rebuild_entity_views(user_id, entity_id)
    return read_json(f) if f.exists() else []

@router.get("/users/{user_id}/search/policy/{numero_polizza}", response_model=Dict[str, Any], summary="Ricerca per Numero Polizza")
def search_by_policy(user_id: str, numero_polizza: str):
    f = by_policy_dir(user_id) / f"{numero_polizza}.json"
    if not f.exists(): raise HTTPException(status_code=404, detail="Numero polizza non indicizzato.")
    return read_json(f)

@router.get("/users/{user_id}/dashboard/due", response_model=Dict[str, Any], summary="Scadenze contratti/titoli entro N giorni")
def dashboard_due(user_id: str, days: int = 120):
    return compute_due_indexes(user_id, days)
