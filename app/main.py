"""api_contratto_omnia8_fastapi.py
=================================================

API REST **Omnia 8 File‑API** (utenti → clienti → contratti)
------------------------------------------------------------

> Gestione completa e auto‑contenuta di **utenti**, **clienti** e **contratti**
> Omnia 8, archiviati come file JSON sul filesystem.
>
> - Percorso base configurabile (`USERS_DATA/` per default).
> - Ogni livello (utente ➜ cliente ➜ contratto) viene creato **on‑demand**.
> - Modelli Pydantic con esempi integrati: `Client`, `ContrattoOmnia8`.
> - End‑point CRUD altamente documentati, raggruppati nei tag **Clients** e
>   **Contracts**.
>
> Avvio rapido:
>
> ```bash
> pip install fastapi uvicorn[standard] pydantic
> uvicorn api_contratto_omnia8_fastapi:app --reload
> ```
> Visita <http://127.0.0.1:8000/docs> per la documentazione Swagger.
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import Body, FastAPI, HTTPException, Path as FPath, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.client_model import Client
from app.models.contract_model import ContrattoOmnia8  # modello contratti
from fastapi.middleware.cors import CORSMiddleware


###############################################################################
#  Costanti & helper                                                            #
###############################################################################
ROOT_DATA_DIR: Path = Path("USERS_DATA")


# ----------------------------- directory helpers -----------------------------

def _user_dir(user_id: str) -> Path:
    """Ritorna `<ROOT_DATA_DIR>/<user_id>` creandolo se mancante."""
    user_path = ROOT_DATA_DIR / user_id
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


def _client_dir(user_id: str, client_id: str) -> Path:
    """Ritorna `<ROOT_DATA_DIR>/<user_id>/<client_id>` creandolo se mancante."""
    client_path = _user_dir(user_id) / client_id
    client_path.mkdir(parents=True, exist_ok=True)
    return client_path


def _client_info_file(user_id: str, client_id: str) -> Path:
    """Path del file JSON contenente i dati anagrafici del cliente."""
    return _client_dir(user_id, client_id) / "client.json"


def _contract_file(user_id: str, client_id: str, contract_id: str) -> Path:
    """Path del file JSON che rappresenta un contratto."""
    return _client_dir(user_id, client_id) / f"{contract_id}.json"


###############################################################################
#  Modelli Pydantic                                                             #
###############################################################################


class ClientListItem(BaseModel):
    client_id: str = Field(..., description="Identificativo cartella cliente")


class ContractListItem(BaseModel):
    contract_id: str = Field(..., description="UUID del contratto")


class CreateContractResponse(BaseModel):
    contract_id: str = Field(..., description="UUID del contratto creato")
    contratto: ContrattoOmnia8


class DeleteResponse(BaseModel):
    deleted: bool = Field(True, description="Operazione andata a buon fine")
    id: str = Field(..., description="ID eliminato (client_id o contract_id)")


###############################################################################
#  FastAPI app                                                                  #
###############################################################################
app = FastAPI(
    title="Omnia 8 File‑API",
    description="Gestione utenti, clienti e contratti Omnia 8 (archiviazione filesystem locale).",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # oppure ["http://localhost:5000"] ecc.
    allow_credentials=True,
    allow_methods=["*"],          # GET, POST, PUT, DELETE, OPTIONS…
    allow_headers=["*"],          # Content-Type, Authorization…
)

# ---------------------------------------------------------------------------
#  Costanti descrizioni parametri                                               #
# ---------------------------------------------------------------------------
USER_ID_DOC = "ID univoco dell’utente (cartella di primo livello)."
CLIENT_ID_DOC = "ID univoco del cliente (cartella dell’utente)."
CONTRACT_ID_DOC = "UUID (hex) che identifica il contratto."

###############################################################################
#                         End‑points CLIENTI (tag: Clients)                    #
###############################################################################

@app.post(
    "/users/{user_id}/clients/{client_id}",
    response_model=Client,
    status_code=status.HTTP_201_CREATED,
    tags=["Clients"],
    summary="Crea un nuovo cliente per un utente",
)
async def create_client(
    user_id: str = FPath(..., description=USER_ID_DOC, example="user_123"),
    client_id: str = FPath(..., description=CLIENT_ID_DOC, example="client_456"),
    payload: Client = Body(..., description="Dati anagrafici del cliente."),
):
    """Crea la cartella `<user_id>/<client_id>` e salva `client.json`."""
    info_file = _client_info_file(user_id, client_id)
    if info_file.exists():
        raise HTTPException(status_code=409, detail="Cliente già esistente.")
    with info_file.open("w", encoding="utf-8") as fp:
        json.dump(payload.dict(), fp, indent=2)
    return payload


@app.get(
    "/users/{user_id}/clients",
    response_model=List[ClientListItem],
    tags=["Clients"],
    summary="Elenca tutti i clienti di un utente",
)
async def list_clients(user_id: str = FPath(..., description=USER_ID_DOC)):
    """Restituisce l’elenco delle cartelle cliente presenti per l’utente."""
    return [ClientListItem(client_id=p.name) for p in _user_dir(user_id).iterdir() if p.is_dir()]


@app.get(
    "/users/{user_id}/clients/{client_id}",
    response_model=Client,
    tags=["Clients"],
    summary="Recupera i dettagli di un cliente",
)
async def get_client(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
):
    info_file = _client_info_file(user_id, client_id)
    if not info_file.exists():
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    return json.loads(info_file.read_text("utf-8"))


@app.put(
    "/users/{user_id}/clients/{client_id}",
    response_model=Client,
    tags=["Clients"],
    summary="Aggiorna (sostituisce) i dati di un cliente",
)
async def update_client(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
    payload: Client = Body(..., description="Nuovi dati cliente."),
):
    info_file = _client_info_file(user_id, client_id)
    if not info_file.exists():
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    info_file.write_text(payload.json(indent=2, ensure_ascii=False))
    return payload


@app.delete(
    "/users/{user_id}/clients/{client_id}",
    response_model=DeleteResponse,
    tags=["Clients"],
    summary="Elimina un cliente e tutti i suoi contratti",
)
async def delete_client(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
):
    client_path = _client_dir(user_id, client_id)
    if not client_path.exists():
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    shutil.rmtree(client_path)
    return DeleteResponse(id=client_id)

###############################################################################
#                      End‑points CONTRATTI (tag: Contracts)                   #
###############################################################################

@app.post(
    "/users/{user_id}/clients/{client_id}/contracts",
    response_model=CreateContractResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Contracts"],
    summary="Crea un nuovo contratto per un cliente",
)
async def create_contract(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
    payload: ContrattoOmnia8 = Body(..., description="Contratto da registrare."),
):
    # verifica che il cliente esista
    if not _client_info_file(user_id, client_id).exists():
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    contract_id = uuid.uuid4().hex
    file_path = _contract_file(user_id, client_id, contract_id)
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(payload.dict(by_alias=True), fp, indent=2, default=str)
    return CreateContractResponse(contract_id=contract_id, contratto=payload)


@app.get(
    "/users/{user_id}/clients/{client_id}/contracts",
    response_model=List[ContractListItem],
    tags=["Contracts"],
    summary="Elenca i contratti di un cliente",
)
async def list_contracts(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
):
    if not _client_info_file(user_id, client_id).exists():
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    files = _client_dir(user_id, client_id).glob("*.json")
    return [ContractListItem(contract_id=p.stem) for p in files if p.name != "client.json"]


@app.get(
    "/users/{user_id}/clients/{client_id}/contracts/{contract_id}",
    response_model=ContrattoOmnia8,
    tags=["Contracts"],
    summary="Recupera un contratto specifico",
)
async def get_contract(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
    contract_id: str = FPath(..., description=CONTRACT_ID_DOC),
):
    file_path = _contract_file(user_id, client_id, contract_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Contratto non trovato.")
    return json.loads(file_path.read_text("utf-8"))


@app.put(
    "/users/{user_id}/clients/{client_id}/contracts/{contract_id}",
    response_model=ContrattoOmnia8,
    tags=["Contracts"],
    summary="Aggiorna (sostituisce) un contratto",
)
async def update_contract(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
    contract_id: str = FPath(..., description=CONTRACT_ID_DOC),
    payload: ContrattoOmnia8 = Body(..., description="Nuovo contenuto completo del contratto."),
):
    file_path = _contract_file(user_id, client_id, contract_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Contratto non trovato.")
    file_path.write_text(json.dumps(payload.dict(by_alias=True), indent=2, default=str))
    return payload


@app.delete(
    "/users/{user_id}/clients/{client_id}/contracts/{contract_id}",
    response_model=DeleteResponse,
    tags=["Contracts"],
    summary="Elimina un contratto",
)
async def delete_contract(
    user_id: str = FPath(..., description=USER_ID_DOC),
    client_id: str = FPath(..., description=CLIENT_ID_DOC),
    contract_id: str = FPath(..., description=CONTRACT_ID_DOC),
):
    file_path = _contract_file(user_id, client_id, contract_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Contratto non trovato.")
    file_path.unlink()
    return DeleteResponse(id=contract_id)

###############################################################################
#                                Misc.                                        #
###############################################################################

@app.get("/ping", summary="Ping di salute API")
async def ping():
    """Ritorna *status: ok* se l’app è attiva."""
    return {"status": "ok"}
