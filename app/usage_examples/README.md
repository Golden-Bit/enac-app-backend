# README — Script di demo (seed, query, mutate/cleanup)

Questi tre script popolano l’API File con dati di test, fanno query/verifiche e infine aggiornano + ripuliscono tutto.

* `seed_many_data.py` – crea entità, contratti, titoli, sinistri, diario, documenti e salva un **manifest** con tutti gli ID.
* `query_views_and_searches.py` – legge il manifest, chiama le viste/ricerche e verifica coerenza e documenti associati.
* `mutate_and_cleanup.py` – aggiorna dati e documenti (con download), poi **cancella tutto** ciò che è stato creato.

---

## Prerequisiti

* Python 3.10+
* Dipendenze Python (almeno `requests`):

  ```bash
  pip install -r requirements.txt
  # oppure
  pip install requests
  ```
* Backend FastAPI **in esecuzione** (di default sugli esempi: `http://127.0.0.1:8111`).
  Esempio tipico:

  ```bash
  uvicorn app.main:app --host 127.0.0.1 --port 8111 --reload
  ```

> Suggerimento (Windows): dopo modifiche al codice backend, **chiudi** il processo `uvicorn` e riavvialo.

---

## 1) Seed massivo

Crea N entità, per ciascuna M contratti; per ogni contratto crea X titoli e Y sinistri, aggiunge note diario, carica documenti (contratto/sinistro/titolo) e scrive un **manifest** JSON.

### Sintassi

```bash
python seed_many_data.py \
  --user-id <USER> \
  --entities <N_ENTITA> \
  --contracts <M_CONTRATTI> \
  --titles <X_TITOLI> \
  --claims <Y_SINISTRI> \
  [--base-url http://127.0.0.1:8111] \
  [--manifest <path_manifest.json>]
```

### Parametri

* `--user-id` (string) – ID utente, es. `testuser`.
* `--entities` (int) – numero entità da creare (default: 2).
* `--contracts` (int) – contratti per entità (default: 2).
* `--titles` (int) – titoli per contratto (default: 3).
* `--claims` (int) – sinistri per contratto (default: 2).
* `--base-url` (string) – base URL API (default: `http://127.0.0.1:8111`).
* `--manifest` (path) – dove salvare il manifest (default: `omnia8_manifest_<user>.json`).

### Esempi

**Seed piccolo di prova**

```bash
python seed_many_data.py --user-id testuser --entities 1 --contracts 1 --titles 1 --claims 1
```

**Seed più corposo + manifest personalizzato**

```bash
python seed_many_data.py \
  --user-id testuser \
  --entities 3 --contracts 2 --titles 3 --claims 2 \
  --base-url http://127.0.0.1:8111 \
  --manifest ./data/omnia8_manifest_testuser.json
```

Al termine vedrai `✅ Seed completato. Manifest salvato in: <path>`.

---

## 2) Query, viste e ricerche

Legge il manifest, chiama viste titoli/sinistri per entità, ricerca per numero polizza, dashboard scadenze e verifica i documenti associati.

### Sintassi

```bash
python query_views_and_searches.py \
  --manifest <path_manifest.json> \
  [--base-url http://127.0.0.1:8111] \
  [--strict-checks]
```

### Parametri

* `--manifest` (path) – **obbligatorio**, manifest prodotto dal seed.
* `--base-url` (string) – base URL API (se diverso da quello nel manifest).
* `--strict-checks` – controlli/asserzioni **attivi** (già di default). Lascialo così per far fallire lo script in caso di mismatch.

### Esempi

**Uso standard (legge il base-url dal manifest)**

```bash
python query_views_and_searches.py --manifest ./data/omnia8_manifest_testuser.json
```

**Forza un base-url diverso**

```bash
python query_views_and_searches.py --manifest omnia8_manifest_testuser.json --base-url http://localhost:8111
```

---

## 3) Mutazione e cleanup

Aggiorna entità/contratti/titoli/sinistri, modifica e **scarica** i documenti, poi **elimina** note diario, documenti, titoli, sinistri, contratti ed entità. Alla fine non deve restare nulla.

⚠️ **Attenzione:** questo script cancella tutto ciò che è elencato nel manifest.

### Sintassi

```bash
python mutate_and_cleanup.py \
  --manifest <path_manifest.json> \
  [--base-url http://127.0.0.1:8111]
```

### Parametri

* `--manifest` (path) – **obbligatorio**, manifest prodotto dal seed.
* `--base-url` (string) – base URL API (se diverso da quello nel manifest).

### Esempi

**Aggiorna e pulisce i dati creati col seed**

```bash
python mutate_and_cleanup.py --manifest ./data/omnia8_manifest_testuser.json
```

**Base-url esplicito**

```bash
python mutate_and_cleanup.py --manifest omnia8_manifest_testuser.json --base-url http://127.0.0.1:8111
```

---

## Flusso consigliato (end-to-end)

```bash
# 1) avvia il backend
uvicorn app.main:app --host 127.0.0.1 --port 8111 --reload

# 2) SEED
python seed_many_data.py --user-id testuser --entities 2 --contracts 2 --titles 2 --claims 2 --manifest ./data/omnia8_manifest_testuser.json

# 3) QUERY & VERIFICHE
python query_views_and_searches.py --manifest ./data/omnia8_manifest_testuser.json

# 4) MUTATE + CLEANUP
python mutate_and_cleanup.py --manifest ./data/omnia8_manifest_testuser.json
```

---

## Troubleshooting

* **Connessione rifiutata / 404** → verifica che il backend sia in esecuzione all’URL usato da `--base-url`.
* **500 su create-doc** → backend non aggiornato o processi pendenti. **Riavvia** completamente `uvicorn`.
* **Permessi/Path manifest** → usa un path esistente e scrivibile (es. `./data/...`), oppure lancia lo script dalla radice del progetto.
