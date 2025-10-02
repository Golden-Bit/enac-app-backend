from __future__ import annotations
import os
import json
import re
import hashlib
import tempfile
from pathlib import Path
from typing import Any
from fastapi import HTTPException

from app.config import ALLOWED_ID_PATTERN, ROOT_DATA_DIR

# ============================================================================
# Validazione ID
# ============================================================================
_ALLOWED_ID = re.compile(ALLOWED_ID_PATTERN)

def sanitize_id(raw: str, what: str) -> str:
    s = raw.strip().replace(" ", "_")
    if not _ALLOWED_ID.match(s):
        raise HTTPException(status_code=400, detail=f"ID {what!r} non valido: usare [a-zA-Z0-9._-]")
    return s

# ============================================================================
# FS helpers
# ============================================================================
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def atomic_write_json(path: Path, obj: Any) -> None:
    """
    Scrittura JSON atomica davvero robusta:
    - garantisce l'esistenza della cartella del file finale
    - crea il tmp nella STESSA directory (compatibile con Windows)
    - sostituzione atomica con os.replace
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(obj, fp, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise

def read_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))

# ============================================================================
# Layout base  users/<user_id>/...
# ============================================================================
def user_dir(user_id: str) -> Path:
    return ensure_dir(Path(ROOT_DATA_DIR) / sanitize_id(user_id, "user_id"))

def entities_dir(user_id: str) -> Path:
    return ensure_dir(user_dir(user_id) / "entities")

def entity_dir(user_id: str, entity_id: str) -> Path:
    return ensure_dir(entities_dir(user_id) / sanitize_id(entity_id, "entity_id"))

def entity_file(user_id: str, entity_id: str) -> Path:
    return entity_dir(user_id, entity_id) / "entity.json"

def contracts_dir(user_id: str, entity_id: str) -> Path:
    return ensure_dir(entity_dir(user_id, entity_id) / "contracts")

def contract_dir(user_id: str, entity_id: str, contract_id: str) -> Path:
    return ensure_dir(contracts_dir(user_id, entity_id) / sanitize_id(contract_id, "contract_id"))

def contract_file(user_id: str, entity_id: str, contract_id: str) -> Path:
    return contract_dir(user_id, entity_id, contract_id) / "contract.json"

# ============================================================================
# Titoli
#   - Ogni titolo è un FILE: titles/<title_id>.json
#   - Documenti in cartella condivisa: titles/documents/<doc_id>.json
# ============================================================================
def titles_dir(user_id: str, entity_id: str, contract_id: str) -> Path:
    return ensure_dir(contract_dir(user_id, entity_id, contract_id) / "titles")

def title_file(user_id: str, entity_id: str, contract_id: str, title_id: str) -> Path:
    return titles_dir(user_id, entity_id, contract_id) / f"{sanitize_id(title_id, 'title_id')}.json"

def title_docs_dir(user_id: str, entity_id: str, contract_id: str, title_id: str) -> Path:
    # cartella condivisa per TUTTI i titoli del contratto
    return ensure_dir(titles_dir(user_id, entity_id, contract_id) / "documents")

# ============================================================================
# Sinistri
#   - Ogni sinistro ha una CARTELLA: claims/<claim_id>/claim.json (+ diary)
#   - Documenti in cartella condivisa: claims/documents/<doc_id>.json
#     (l'associazione avviene con meta["claim_id"])
# ============================================================================
def claims_dir(user_id: str, entity_id: str, contract_id: str) -> Path:
    return ensure_dir(contract_dir(user_id, entity_id, contract_id) / "claims")

def claim_dir(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> Path:
    return ensure_dir(claims_dir(user_id, entity_id, contract_id) / sanitize_id(claim_id, "claim_id"))

def claim_file(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> Path:
    return claim_dir(user_id, entity_id, contract_id, claim_id) / "claim.json"

def diary_dir(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> Path:
    return ensure_dir(claim_dir(user_id, entity_id, contract_id, claim_id) / "diary")

def diary_file(user_id: str, entity_id: str, contract_id: str, claim_id: str, entry_id: str) -> Path:
    return diary_dir(user_id, entity_id, contract_id, claim_id) / f"{sanitize_id(entry_id, 'entry_id')}.json"

# --- Documenti (contratti/sinistri/titoli) ----------------------------------
def contract_docs_dir(user_id: str, entity_id: str, contract_id: str) -> Path:
    return ensure_dir(contract_dir(user_id, entity_id, contract_id) / "documents")

def claim_docs_dir(user_id: str, entity_id: str, contract_id: str, claim_id: str) -> Path:
    """
    ⛳️ **Nuovo schema**: cartella condivisa per TUTTI i claim del contratto.
    `claim_id` è ignorato qui (rimane nel signature per compatibilità).
    """
    return ensure_dir(claims_dir(user_id, entity_id, contract_id) / "documents")

def doc_meta_file(base_dir: Path, doc_id: str) -> Path:
    return ensure_dir(base_dir) / f"{sanitize_id(doc_id, 'doc_id')}.json"

# ============================================================================
# Viste & indici
# ============================================================================
def views_dir_for_entity(user_id: str, entity_id: str) -> Path:
    return ensure_dir(entity_dir(user_id, entity_id) / "views")

def indexes_dir(user_id: str) -> Path:
    return ensure_dir(user_dir(user_id) / "indexes")

def by_policy_dir(user_id: str) -> Path:
    return ensure_dir(indexes_dir(user_id) / "by_policy")

def due_dir(user_id: str) -> Path:
    return ensure_dir(indexes_dir(user_id) / "due")

# ============================================================================
# Blobstore deduplicato  users/<user_id>/blobs/ab/abcdef... (sha1)
# ============================================================================
def blobs_dir(user_id: str) -> Path:
    return ensure_dir(user_dir(user_id) / "blobs")

def blob_path_for_hash(user_id: str, h: str) -> Path:
    base = blobs_dir(user_id)
    shard = h[:2]
    return ensure_dir(base / shard) / h

def write_blob(user_id: str, content: bytes) -> tuple[str, str]:
    """
    Scrive il blob se assente. Ritorna (sha1, path_relativo_da_user_dir).
    """
    sha1 = hashlib.sha1(content).hexdigest()
    bp = blob_path_for_hash(user_id, sha1)
    if not bp.exists():
        ensure_dir(bp.parent)
        with bp.open("wb") as fp:
            fp.write(content)
    rel = str(bp.relative_to(user_dir(user_id)))
    return sha1, rel
