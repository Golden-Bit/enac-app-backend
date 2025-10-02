# Omnia8 File-API — README

Questa guida riassume **tutto** ciò che serve per usare e capire l’API file–based: struttura dati su filesystem, modelli Pydantic, endpoint REST, viste/indici, document store con blob deduplicati e script di esempio. La documentazione è stata redatta leggendo direttamente i sorgenti dell’app (router, modelli, servizi e utility). 

---

## Indice

* [Panoramica & avvio rapido](#panoramica--avvio-rapido)
* [Struttura storage su filesystem](#struttura-storage-su-filesystem)
* [Modelli dati (Pydantic)](#modelli-dati-pydantic)
* [Endpoint REST](#endpoint-rest)

  * [Entities](#entities)
  * [Contracts](#contracts)
  * [Titles](#titles)
  * [Claims](#claims)
  * [Diary (note di sinistro)](#diary-note-di-sinistro)
  * [Documents (contratto/sinistro/titolo)](#documents-contrattosinistrotitolo)
  * [Viste & Ricerche](#viste--ricerche)
* [Gestione blob & deduplica](#gestione-blob--deduplica)
* [Regole ID & scrittura atomica](#regole-id--scrittura-atomica)
* [Script di utilizzo (seed / query / mutate & cleanup)](#script-di-utilizzo-seed--query--mutate--cleanup)
* [Errori & codici di stato](#errori--codici-di-stato)

---

## Panoramica & avvio rapido

* **Stack**: FastAPI + Pydantic. CORS abilitato per `*` (restringere in produzione).
* **Versione app**: `1.0.1`.
* **Ping**: `GET /ping → {"status":"ok"}`.
* **Storage root**: `USERS_DATA` (configurabile modificando `app/config.py`).
* **Avvio locale (sviluppo)**:

  ```bash
  uvicorn app.main:app --host 127.0.0.1 --port 8111 --reload
  ```

  Swagger UI su `http://127.0.0.1:8111/docs`.

---

## Struttura storage su filesystem

Per ogni `user_id` si crea una gerarchia sotto `USERS_DATA/<user_id>/`:

```
USERS_DATA/<user_id>/
├── entities/
│   └── <entity_id>/
│       ├── entity.json
│       ├── contracts/
│       │   └── <contract_id>/
│       │       ├── contract.json
│       │       ├── documents/                  # metadati doc contratto
│       │       │   └── <doc_id>.json
│       │       ├── titles/
│       │       │   ├── <title_id>.json         # 1 file per titolo
│       │       │   └── documents/              # cartella condivisa per TUTTI i titoli del contratto
│       │       │       └── <doc_id>.json       # contiene meta.title_id
│       │       └── claims/
│       │           ├── documents/              # ⛳️ cartella condivisa per TUTTI i sinistri del contratto
│       │           │   └── <doc_id>.json       # contiene meta.claim_id
│       │           └── <claim_id>/
│       │               ├── claim.json
│       │               └── diary/
│       │                   └── <entry_id>.json
│       └── views/
│           ├── titles_index.json               # vista aggregata titoli
│           └── claims_index.json               # vista aggregata sinistri
├── indexes/
│   ├── by_policy/
│   │   └── <NumeroPolizza>.json → { entity_id, contract_id }
│   └── due/                                    # (generato on-demand)
└── blobs/
    └── <shard>/<sha1>                          # dedup globale per utente
```

**Nota importante sui documenti dei CLAIMS**
Lo schema “nuovo” usa la cartella **condivisa** `contracts/<contract_id>/claims/documents/` con `meta.claim_id` per associare un doc al sinistro. È supportata in **lettura/aggiornamento/cancellazione** anche la **compatibilità legacy** (`contracts/<contract_id>/claims/<claim_id>/documents/`). Le API cercano prima nel nuovo schema, poi nel legacy.

---

## Modelli dati (Pydantic)

### Entity

Campi principali: `name` (obbl.), contatti e `admin_data` (dict libero).

### Contratto (`ContrattoOmnia8`)

Strutturato in sezioni (con alias “camel” usati nel JSON):

* `Identificativi` → **Compagnia** (obbl.), **NumeroPolizza** (obbl.), `Tipo`, `TpCar`, `Ramo`.
* `Amministrativi` → `Effetto`, `Scadenza`, `Frazionamento`, ecc.
* `RamiEl` → `Descrizione` (rischio).
* Altre sezioni: `UnitaVendita`, `Premi`, `Rinnovo`, `Operativita`.

> Suggerimento: inviare i payload **usando gli alias** (es. `NumeroPolizza`, `Compagnia`) come fa lo script `seed_many_data.py`.

### Titolo (`Titolo`)

Obbligatori: `tipo` (`RATA|QUIETANZA|APPENDICE|VARIAZIONE`), `effetto_titolo`, `scadenza_titolo`.
Facoltativi: importi (`premio_lordo`, `imponibile`, …), `stato`, `pv/pv2`, ecc.
Denormalizzazioni: `numero_polizza`, `entity_id` (iniettati alla creazione).

### Sinistro (`Sinistro`)

Obbligatori: `esercizio` (int), `numero_sinistro` (str), `data_avvenimento` (date).
Facoltativi: luogo (`città`, `provincia`, …), `dinamica`, `stato_compagnia`, `data_apertura/chiusura`, e denorm (`numero_polizza`, `compagnia`, `rischio`).

### Diario (`DiarioEntry`)

`autore` (obbl.), `testo` (obbl.), `timestamp` auto-UTC.

### Documento (`DocumentoMeta` + `CreateDocumentRequest`)

`meta` obbligatoria:

* `scope`: `CONTRATTO|TITOLO|SINISTRO|GARA`
* `categoria`: `CND|APP|CLAIM|ALTRO`
* `mime`, `nome_originale`, `size`
* opzionali: `hash`, `path_relativo`, `metadati` (dict libero)
  `content_base64` opzionale: se presente viene salvato nel blobstore e `meta.hash`/`meta.path_relativo` vengono impostati.

---

## Endpoint REST

### Entities

* **POST** `/users/{user_id}/entities/{entity_id}` → crea entity (409 se esiste).
* **GET**  `/users/{user_id}/entities` → lista `entity_id`.
* **GET**  `/users/{user_id}/entities/{entity_id}` → entity.json.
* **PUT**  `/users/{user_id}/entities/{entity_id}` → aggiorna.
* **DELETE** `/users/{user_id}/entities/{entity_id}` → rimuove intera cartella.

### Contracts

* **POST** `/users/{user_id}/entities/{entity_id}/contracts` → crea contratto, indicizza `NumeroPolizza`.

  * Payload usa gli **alias** (es. `Identificativi.Compagnia`, `RamiEl.Descrizione`, …).
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts` → lista `contract_id`.
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}` → contract.json.
* **PUT**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}` → aggiorna + refresh indice by-policy + rebuild viste.
* **DELETE** `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}` → elimina cartella contratto.

### Titles

* **POST** `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles` → crea titolo (denorm: `numero_polizza`, `entity_id`).
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles` → lista `title_id` (solo file, **esclude** `titles/documents/`).
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}` → titolo.
* **PUT**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}` → aggiorna + rebuild viste.
* **DELETE** `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}` → elimina file + rebuild viste.

### Claims

* **POST** `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims` → crea sinistro (denorm: `numero_polizza`, `compagnia`, `rischio`).
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims` → lista `claim_id` (nomi cartelle).
* **GET**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}` → claim.json.
* **PUT**  `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}` → aggiorna + rebuild viste.
* **DELETE** `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}` → elimina cartella + rebuild viste.

### Diary (note di sinistro)

Prefisso: `/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary`

* **POST** `""` → crea nota diario → `{ "id": "<entry_id>" }`.
* **GET**  `""` → lista note con `entry_id`.
* **GET**  `/{entry_id}` → dettaglio.
* **PUT**  `/{entry_id}` → aggiorna.
* **DELETE** `/{entry_id}` → elimina.

### Documents (contratto/sinistro/titolo)

**Documenti contratto**

* **GET**  `/contracts/{contract_id}/documents` → lista `doc_id`.
* **POST** `/contracts/{contract_id}/documents` → crea doc (imposta `meta.level="CONTRATTO"`).
* **GET**  `/contracts/{contract_id}/documents/{doc_id}` → metadati.
* **GET**  `/contracts/{contract_id}/documents/{doc_id}/download` → blob.
* **PUT**  `/contracts/{contract_id}/documents/{doc_id}` → aggiorna meta/contenuto (conserva `hash/path` se non arriva nuovo blob).
* **DELETE** `/contracts/{contract_id}/documents/{doc_id}?delete_blob=bool` → cancella meta; se `delete_blob=true` elimina anche il blob **solo** se il suo SHA1 non è referenziato altrove.

**Documenti sinistro (schema condiviso + legacy)**

* **GET**  `/claims/{claim_id}/documents` → lista `doc_id`:

  * legge la cartella **condivisa** `claims/documents/` filtrando `meta.claim_id == {claim_id}`
  * unisce eventuali file presenti nella cartella **legacy** `claims/<claim_id>/documents/`.
* **POST** `/claims/{claim_id}/documents` → crea doc: imposta `meta.claim_id = {claim_id}`, `meta.level="SINISTRO"`, salva meta in **cartella condivisa**.
* **GET**  `/claims/{claim_id}/documents/{doc_id}` → metadati (nuovo o legacy).
* **GET**  `/claims/{claim_id}/documents/{doc_id}/download` → blob.
* **PUT**  `/claims/{claim_id}/documents/{doc_id}` → aggiorna (mantiene `claim_id` e `hash/path` se non ricaricati).
* **DELETE** `/claims/{claim_id}/documents/{doc_id}?delete_blob=bool` → come sopra (con GC condizionale).

**Documenti titolo (cartella condivisa)**

* **GET**  `/titles/{title_id}/documents` → lista `doc_id` filtrando meta per `title_id`.
* **POST** `/titles/{title_id}/documents` → crea doc: `meta.title_id = {title_id}`, `meta.level="TITOLO"`.
* **GET**  `/titles/{title_id}/documents/{doc_id}` → metadati.
* **GET**  `/titles/{title_id}/documents/{doc_id}/download` → blob.
* **PUT**  `/titles/{title_id}/documents/{doc_id}` → aggiorna (mantiene `title_id` e `hash/path` se non ricaricati).
* **DELETE** `/titles/{title_id}/documents/{doc_id}?delete_blob=bool` → come sopra.

#### Esempio upload documento (curl)

```bash
# "Hello" in base64 → SGVsbG8=
curl -X POST "http://127.0.0.1:8111/users/u1/entities/e1/contracts/c1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "scope": "CONTRATTO",
      "categoria": "ALTRO",
      "mime": "text/plain",
      "nome_originale": "hello.txt",
      "size": 5,
      "metadati": {"seed": true}
    },
    "content_base64": "SGVsbG8="
  }'
```

### Viste & Ricerche

* **Titoli per entità**
  `GET /users/{user_id}/entities/{entity_id}/titles`
  Lista di record arricchiti (`title_id`, `contract_id`, `compagnia`, `numero_polizza`, `rischio`, `scadenza_titolo`, ecc.). Se l’indice manca viene rigenerato.

* **Sinistri per entità**
  `GET /users/{user_id}/entities/{entity_id}/claims`
  Ogni record contiene il contenuto del `claim.json` + `claim_id` + `contract_id`. Rigenerazione analoga.

* **Ricerca per Numero Polizza**
  `GET /users/{user_id}/search/policy/{NumeroPolizza}` → `{ "entity_id": "...", "contract_id": "..." }` (404 se non indicizzato).

* **Dashboard scadenze**
  `GET /users/{user_id}/dashboard/due?days=120` → `{ "contracts_due": [...], "titles_due": [...] }`, filtrati per date entro `days`.

Le viste vengono **rigenerate** automaticamente da `contracts.py`, `titles.py`, `claims.py` dopo create/update/delete.

---

## Gestione blob & deduplica

* I contenuti binari (opzionali) vengono salvati in `blobs/<shard>/<sha1>`.
* Il riferimento al blob sta in `meta.hash` e `meta.path_relativo` del **metadato documento**.
* In DELETE doc: se `delete_blob=true`, il blob viene rimosso **solo** se `sha1` non è usato da altri metadati (conteggio via scansione `**/documents/*.json`).

---

## Regole ID & scrittura atomica

* **ID validi** (tutti i segmenti usati in path): regex `^[a-zA-Z0-9._-]+$`. Spazi → `_`. Se invalido: **400**.
* **Scrittura JSON atomica**: i file vengono scritti su temp file **nella stessa cartella** e sostituiti con `os.replace` (compatibile Windows). Le cartelle sono sempre create/garantite.

---

## Script di utilizzo (seed / query / mutate & cleanup)

Sono inclusi tre script CLI che parlano con l’API (base default: `http://127.0.0.1:8111`):

1. **Seed massivo** — `app/usage_examples/seed_many_data.py`
   Crea varie entità/contratti/titoli/sinistri, note diario e documenti; salva un **MANIFEST** JSON.

   ```bash
   python app/usage_examples/seed_many_data.py \
     --user-id testuser --entities 2 --contracts 2 --titles 3 --claims 2 \
     --base-url http://127.0.0.1:8111
   ```

   Output: `omnia8_manifest_<user>.json`.

2. **Query & Views** — `app/usage_examples/query_views_and_searches.py`
   Legge il **manifest**, verifica viste (titoli/sinistri), ricerca per polizza, dashboard scadenze, presenza documenti.

   ```bash
   python app/usage_examples/query_views_and_searches.py \
     --manifest omnia8_manifest_testuser.json \
     --base-url http://127.0.0.1:8111
   ```

3. **Mutazioni & Cleanup** — `app/usage_examples/mutate_and_cleanup.py`
   Aggiorna dati (es. `stato_compagnia`, pagamento titolo, scadenze), prova CRUD documenti (update/download/delete con GC blob) e poi **ripulisce tutto**.

   ```bash
   python app/usage_examples/mutate_and_cleanup.py \
     --manifest omnia8_manifest_testuser.json \
     --base-url http://127.0.0.1:8111
   ```

---

## Errori & codici di stato

* **200 / 201**: operazioni riuscite (POST entity usa 201).
* **400**: ID non valido (regex).
* **404**: risorsa non trovata (entità/contratto/titolo/sinistro/doc/diario), blob mancante, documento senza blob.
* **409**: creazione entità esistente.

Le risposte di **DELETE** usano:

```json
{ "deleted": true, "id": "<resource_id>" }
```

---

### Esempi rapidi (curl)

```bash
# 1) Crea Entity
curl -X POST "http://127.0.0.1:8111/users/testuser/entities/ACME_SPA" \
  -H "Content-Type: application/json" \
  -d '{"name":"ACME S.p.A.","admin_data":{"source":"manual"}}'

# 2) Crea Contract (minimo indispensabile)
curl -X POST "http://127.0.0.1:8111/users/testuser/entities/ACME_SPA/contracts" \
  -H "Content-Type: application/json" \
  -d '{
        "Identificativi": {"Compagnia":"Allianz","NumeroPolizza":"POL-123"},
        "RamiEl": {"Descrizione":"RC Aeromobili"}
      }'

# 3) Crea Title
curl -X POST "http://127.0.0.1:8111/users/testuser/entities/ACME_SPA/contracts/<contract_id>/titles" \
  -H "Content-Type: application/json" \
  -d '{"tipo":"RATA","effetto_titolo":"2025-10-01","scadenza_titolo":"2026-10-01"}'

# 4) Crea Claim
curl -X POST "http://127.0.0.1:8111/users/testuser/entities/ACME_SPA/contracts/<contract_id>/claims" \
  -H "Content-Type: application/json" \
  -d '{"esercizio":2025,"numero_sinistro":"1001","data_avvenimento":"2025-09-25"}'

# 5) Aggiungi nota diario
curl -X POST "http://127.0.0.1:8111/users/testuser/entities/ACME_SPA/contracts/<contract_id>/claims/<claim_id>/diary" \
  -H "Content-Type: application/json" \
  -d '{"autore":"op","testo":"presa in carico"}'
```

---

Se ti serve, posso fornirti un **postman collection**/insomnia o adattare la guida a casi d’uso specifici (workflow di caricamento massivo, policy automation, integrazioni, ecc.).
