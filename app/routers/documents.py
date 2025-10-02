from __future__ import annotations
import base64
import uuid
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from app.models.document import CreateDocumentRequest, CreateResponse
from app.models.responses import DeleteResponse
from app.utils.utils import (
    contract_docs_dir, claim_docs_dir, title_docs_dir, doc_meta_file,
    user_dir, contract_file, claim_file, title_file, claim_dir,
    atomic_write_json, read_json, write_blob, ensure_dir
)
from app.services.indexes import count_blob_references

router = APIRouter(tags=["Documents"])

# ============================================================================
# Helpers
# ============================================================================
def _list_docs_in_dir(base_dir: Path) -> List[str]:
    if not base_dir.exists():
        return []
    return [p.stem for p in base_dir.glob("*.json")]

def _read_meta(base_dir: Path, doc_id: str) -> Dict[str, Any]:
    mf = doc_meta_file(base_dir, doc_id)
    if not mf.exists():
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    return read_json(mf)

def _write_meta(base_dir: Path, doc_id: str, meta: Dict[str, Any]) -> None:
    # garantisce la cartella e scrive in modo atomico
    ensure_dir(base_dir)
    path = doc_meta_file(base_dir, doc_id)
    ensure_dir(path.parent)
    atomic_write_json(path, meta)

def _download(user_id: str, meta: Dict[str, Any]) -> FileResponse:
    rel = meta.get("path_relativo")
    if not rel:
        raise HTTPException(status_code=404, detail="Documento senza blob.")
    path = user_dir(user_id) / rel
    if not path.exists():
        raise HTTPException(status_code=404, detail="Blob non trovato.")
    return FileResponse(
        path,
        media_type=meta.get("mime") or "application/octet-stream",
        filename=meta.get("nome_originale") or "download.bin",
    )

# ---- supporto compatibilità: percorso legacy dei claim-docs -----------------
def _claim_legacy_docs_dir(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> Path:
    # vecchio schema: claims/<claim_id>/documents/
    return claim_dir(user_id, entity_id, contract_id, claim_id) / "documents"

def _claim_doc_bases(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> List[Path]:
    # nuovo schema (condiviso) + legacy (per lettura/compatibilità)
    return [claim_docs_dir(user_id, entity_id, contract_id, claim_id),
            _claim_legacy_docs_dir(user_id, entity_id, contract_id, claim_id)]

# ============================================================================
# CONTRACT DOCS
# ============================================================================
@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents", response_model=List[str])
def list_contract_docs(user_id: str, entity_id: str, contract_id: str):
    return _list_docs_in_dir(contract_docs_dir(user_id, entity_id, contract_id))

@router.post("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents", response_model=CreateResponse)
def create_contract_doc(user_id: str, entity_id: str, contract_id: str, payload: CreateDocumentRequest = Body(...)):
    if not contract_file(user_id, entity_id, contract_id).exists():
        raise HTTPException(status_code=404, detail="Contratto non trovato.")
    doc_id = uuid.uuid4().hex
    meta = payload.meta.dict()
    meta.setdefault("metadati", {})["level"] = "CONTRATTO"
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    _write_meta(contract_docs_dir(user_id, entity_id, contract_id), doc_id, meta)
    return CreateResponse(id=doc_id)

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}", response_model=Dict[str, Any])
def get_contract_doc_meta(user_id: str, entity_id: str, contract_id: str, doc_id: str):
    return _read_meta(contract_docs_dir(user_id, entity_id, contract_id), doc_id)

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}/download")
def download_contract_doc(user_id: str, entity_id: str, contract_id: str, doc_id: str):
    meta = _read_meta(contract_docs_dir(user_id, entity_id, contract_id), doc_id)
    return _download(user_id, meta)

@router.put("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}", response_model=Dict[str, Any])
def update_contract_doc(user_id: str, entity_id: str, contract_id: str, doc_id: str, payload: CreateDocumentRequest = Body(...)):
    base_dir = contract_docs_dir(user_id, entity_id, contract_id)
    old = _read_meta(base_dir, doc_id)
    meta = payload.meta.dict()
    meta.setdefault("metadati", {})["level"] = "CONTRATTO"
    for k in ("hash", "path_relativo"):
        if old.get(k):
            meta.setdefault(k, old[k])
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    _write_meta(base_dir, doc_id, meta)
    return {"doc_id": doc_id, **meta}

@router.delete("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}", response_model=DeleteResponse)
def delete_contract_doc(user_id: str, entity_id: str, contract_id: str, doc_id: str, delete_blob: bool = Query(False)):
    base_dir = contract_docs_dir(user_id, entity_id, contract_id)
    mf = doc_meta_file(base_dir, doc_id)
    if not mf.exists():
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    sha1 = read_json(mf).get("hash")
    mf.unlink()
    if delete_blob and sha1 and count_blob_references(user_id, sha1) <= 1:
        from app.utils.utils import blob_path_for_hash
        path = blob_path_for_hash(user_id, sha1)
        if path.exists():
            path.unlink()
    return DeleteResponse(id=doc_id)

# ============================================================================
# CLAIM DOCS (schema CONDIVISO + compat legacy)
# ============================================================================
@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents", response_model=List[str])
def list_claim_docs(user_id: str, entity_id: str, contract_id: str, claim_id: str):
    ids: set[str] = set()
    shared_dir, legacy_dir = _claim_doc_bases(user_id, entity_id, contract_id, claim_id)
    # nuovo schema: filtra per claim_id nel metadato
    if shared_dir.exists():
        for f in shared_dir.glob("*.json"):
            try:
                meta = read_json(f)
            except Exception:
                continue
            if meta.get("claim_id") == claim_id:
                ids.add(f.stem)
    # legacy: cartella per-claim -> tutti i file sono del claim corrente
    if legacy_dir.exists():
        ids.update(p.stem for p in legacy_dir.glob("*.json"))
    return sorted(ids)

@router.post("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents", response_model=CreateResponse)
def create_claim_doc(user_id: str, entity_id: str, contract_id: str, claim_id: str, payload: CreateDocumentRequest = Body(...)):
    if not claim_file(user_id, entity_id, contract_id, claim_id).exists():
        raise HTTPException(status_code=404, detail="Sinistro non trovato.")
    doc_id = uuid.uuid4().hex
    meta = payload.meta.dict()
    meta["claim_id"] = claim_id                    # ⛳️ associazione forte
    meta.setdefault("metadati", {})["level"] = "SINISTRO"
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    base = claim_docs_dir(user_id, entity_id, contract_id, claim_id)  # condiviso
    _write_meta(base, doc_id, meta)
    return CreateResponse(id=doc_id)

def _get_claim_doc_meta_any(user_id: str, entity_id: str, contract_id: str, claim_id: str, doc_id: str) -> tuple[Dict[str, Any], Path]:
    """Ritorna (meta, base_dir effettivo) cercando prima nello schema nuovo, poi nel legacy."""
    shared_dir, legacy_dir = _claim_doc_bases(user_id, entity_id, contract_id, claim_id)
    # nuovo schema (condiviso)
    mf = doc_meta_file(shared_dir, doc_id)
    if mf.exists():
        meta = read_json(mf)
        if meta.get("claim_id") != claim_id:
            raise HTTPException(status_code=404, detail="Documento non associato a questo sinistro.")
        return meta, shared_dir
    # legacy (per-claim)
    mf2 = doc_meta_file(legacy_dir, doc_id)
    if mf2.exists():
        return read_json(mf2), legacy_dir
    raise HTTPException(status_code=404, detail="Documento non trovato.")

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}", response_model=Dict[str, Any])
def get_claim_doc_meta(user_id: str, entity_id: str, contract_id: str, claim_id: str, doc_id: str):
    meta, _ = _get_claim_doc_meta_any(user_id, entity_id, contract_id, claim_id, doc_id)
    return meta

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}/download")
def download_claim_doc(user_id: str, entity_id: str, contract_id: str, claim_id: str, doc_id: str):
    meta, _ = _get_claim_doc_meta_any(user_id, entity_id, contract_id, claim_id, doc_id)
    return _download(user_id, meta)

@router.put("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}", response_model=Dict[str, Any])
def update_claim_doc(user_id: str, entity_id: str, contract_id: str, claim_id: str, doc_id: str, payload: CreateDocumentRequest = Body(...)):
    # prova nuovo schema, poi legacy
    meta_old, base_dir = _get_claim_doc_meta_any(user_id, entity_id, contract_id, claim_id, doc_id)
    meta = payload.meta.dict()
    # NON perdere l'associazione
    meta["claim_id"] = claim_id
    meta.setdefault("metadati", {})["level"] = "SINISTRO"
    for k in ("hash", "path_relativo"):
        if meta_old.get(k):
            meta.setdefault(k, meta_old[k])
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    _write_meta(base_dir, doc_id, meta)
    return {"doc_id": doc_id, **meta}

@router.delete("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}", response_model=DeleteResponse)
def delete_claim_doc(user_id: str, entity_id: str, contract_id: str, claim_id: str, doc_id: str, delete_blob: bool = Query(False)):
    meta, base_dir = _get_claim_doc_meta_any(user_id, entity_id, contract_id, claim_id, doc_id)
    sha1 = meta.get("hash")
    mf = doc_meta_file(base_dir, doc_id)
    if not mf.exists():
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    mf.unlink()
    if delete_blob and sha1 and count_blob_references(user_id, sha1) <= 1:
        from app.utils.utils import blob_path_for_hash
        p = blob_path_for_hash(user_id, sha1)
        if p.exists():
            p.unlink()
    return DeleteResponse(id=doc_id)

# ============================================================================
# TITLE DOCS  (cartella condivisa titles/documents + filtro per title_id)
# ============================================================================
@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents", response_model=List[str])
def list_title_docs(user_id: str, entity_id: str, contract_id: str, title_id: str):
    base = title_docs_dir(user_id, entity_id, contract_id, title_id)
    ids: List[str] = []
    for f in base.glob("*.json"):
        try:
            meta = read_json(f)
        except Exception:
            continue
        if meta.get("title_id") == title_id:
            ids.append(f.stem)
    return ids

@router.post("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents", response_model=CreateResponse)
def create_title_doc(user_id: str, entity_id: str, contract_id: str, title_id: str, payload: CreateDocumentRequest = Body(...)):
    if not title_file(user_id, entity_id, contract_id, title_id).exists():
        raise HTTPException(status_code=404, detail="Titolo non trovato.")
    doc_id = uuid.uuid4().hex
    meta = payload.meta.dict()
    meta["title_id"] = title_id
    meta.setdefault("metadati", {})["level"] = "TITOLO"
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    _write_meta(title_docs_dir(user_id, entity_id, contract_id, title_id), doc_id, meta)
    return CreateResponse(id=doc_id)

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}", response_model=Dict[str, Any])
def get_title_doc_meta(user_id: str, entity_id: str, contract_id: str, title_id: str, doc_id: str):
    base = title_docs_dir(user_id, entity_id, contract_id, title_id)
    meta = _read_meta(base, doc_id)
    if meta.get("title_id") != title_id:
        raise HTTPException(status_code=404, detail="Documento non associato a questo titolo.")
    return meta

@router.get("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}/download")
def download_title_doc(user_id: str, entity_id: str, contract_id: str, title_id: str, doc_id: str):
    base = title_docs_dir(user_id, entity_id, contract_id, title_id)
    meta = _read_meta(base, doc_id)
    if meta.get("title_id") != title_id:
        raise HTTPException(status_code=404, detail="Documento non associato a questo titolo.")
    return _download(user_id, meta)

@router.put("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}", response_model=Dict[str, Any])
def update_title_doc(user_id: str, entity_id: str, contract_id: str, title_id: str, doc_id: str, payload: CreateDocumentRequest = Body(...)):
    base = title_docs_dir(user_id, entity_id, contract_id, title_id)
    old = _read_meta(base, doc_id)
    if old.get("title_id") != title_id:
        raise HTTPException(status_code=404, detail="Documento non associato a questo titolo.")
    meta = payload.meta.dict()
    meta["title_id"] = title_id
    meta.setdefault("metadati", {})["level"] = "TITOLO"
    for k in ("hash", "path_relativo"):
        if old.get(k):
            meta.setdefault(k, old[k])
    if payload.content_base64:
        h, rel = write_blob(user_id, base64.b64decode(payload.content_base64))
        meta["hash"] = h
        meta["path_relativo"] = rel
    _write_meta(base, doc_id, meta)
    return {"doc_id": doc_id, **meta}

@router.delete("/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}", response_model=DeleteResponse)
def delete_title_doc(user_id: str, entity_id: str, contract_id: str, title_id: str, doc_id: str, delete_blob: bool = Query(False)):
    base = title_docs_dir(user_id, entity_id, contract_id, title_id)
    mf = doc_meta_file(base, doc_id)
    if not mf.exists():
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    meta = read_json(mf)
    if meta.get("title_id") != title_id:
        raise HTTPException(status_code=404, detail="Documento non associato a questo titolo.")
    sha1 = meta.get("hash")
    mf.unlink()
    if delete_blob and sha1 and count_blob_references(user_id, sha1) <= 1:
        from app.utils.utils import blob_path_for_hash
        p = blob_path_for_hash(user_id, sha1)
        if p.exists():
            p.unlink()
    return DeleteResponse(id=doc_id)
