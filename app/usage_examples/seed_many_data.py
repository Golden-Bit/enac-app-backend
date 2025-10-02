# seed_many_data.py
"""
Seed massivo per Omnia8 File-API (localhost:8111).
- Crea N entità per un utente
- Per ogni entità: M contratti
- Per ogni contratto: X titoli, Y sinistri
- Aggiunge note diario ai sinistri
- Carica documenti (contratto/sinistro/titolo) come base64
- Salva un MANIFEST JSON con tutti gli ID creati (da usare nello script 2)

Esecuzione:
    python seed_many_data.py --user-id testuser --entities 3 --contracts 2 --titles 3 --claims 2
Opzioni:
    --base-url http://127.0.0.1:8111
"""

import argparse
import base64
import json
import random
import uuid
from datetime import date, timedelta
from pprint import pformat
import requests

def pretty(x): return pformat(x, width=110)

def api(base_url, method, path, *, params=None, json_body=None, stream=False, ok_codes=(200,201)):
    url = base_url + path
    r = requests.request(method, url, params=params, json=json_body, stream=stream)
    if r.status_code not in ok_codes:
        raise RuntimeError(f"{method} {path} -> {r.status_code} : {r.text}")
    return r

def make_txt_bytes(text: str) -> bytes:
    return text.encode("utf-8")

def create_entity(base_url, user_id, entity_id, name, extra_note):
    payload = {
        "name": name,
        "admin_data": {"source": "seed", "note": extra_note}
    }
    api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}", json_body=payload)
    return payload

def create_contract(base_url, user_id, entity_id, compagnia, numero_polizza, rischio_descr="ARD"):
    payload = {
        "Identificativi": {
            "Tipo": "Nuova",
            "TpCar": None,
            "Ramo": "ARD",
            "Compagnia": compagnia,
            "NumeroPolizza": numero_polizza,
        },
        "RamiEl": {"Descrizione": rischio_descr},
    }
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts", json_body=payload)
    return r.json()["contract_id"]

def create_title(base_url, user_id, entity_id, contract_id, tipo, effetto, scadenza, stato="DA_PAGARE"):
    payload = {
        "tipo": tipo,
        "effetto_titolo": effetto.isoformat(),
        "scadenza_titolo": scadenza.isoformat(),
        "premio_lordo": "1000.00",
        "imponibile": "820.00",
        "imposte": "180.00",
        "frazionamento": "SEMESTRALE",
        "stato": stato,
        "pv": "PV-001",
        "pv2": "PV-002",
    }
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles", json_body=payload)
    return r.json()["title_id"]

def create_claim(base_url, user_id, entity_id, contract_id, esercizio, num):
    payload = {
        "esercizio": esercizio,
        "numero_sinistro": num,
        "data_avvenimento": (date.today() - timedelta(days=5)).isoformat(),
        "città": "Roma",
        "provincia": "RM",
        "dinamica": "Urto in retromarcia su mezzi aeroportuali",
    }
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims", json_body=payload)
    return r.json()["claim_id"]

def add_diary(base_url, user_id, entity_id, contract_id, claim_id, testo, autore="seed"):
    payload = {"autore": autore, "testo": testo}
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary", json_body=payload)
    return r.json()["id"]

def create_doc_payload(scope, categoria, filename, content: bytes):
    return {
        "meta": {
            "scope": scope,
            "categoria": categoria,
            "mime": "text/plain",
            "nome_originale": filename,
            "size": len(content),
            "metadati": {"seed": True},
        },
        "content_base64": base64.b64encode(content).decode("ascii"),
    }

def create_contract_doc(base_url, user_id, entity_id, contract_id, content_text):
    payload = create_doc_payload("CONTRATTO", "ALTRO", "doc_contract.txt", make_txt_bytes(content_text))
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents", json_body=payload)
    return r.json()["id"]

def create_claim_doc(base_url, user_id, entity_id, contract_id, claim_id, content_text):
    payload = create_doc_payload("SINISTRO", "CLAIM", "doc_claim.txt", make_txt_bytes(content_text))
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents", json_body=payload)
    return r.json()["id"]

def create_title_doc(base_url, user_id, entity_id, contract_id, title_id, content_text):
    payload = create_doc_payload("TITOLO", "APP", "doc_title.txt", make_txt_bytes(content_text))
    r = api(base_url, "POST", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents", json_body=payload)
    return r.json()["id"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8111")
    ap.add_argument("--user-id", default="testuser")
    ap.add_argument("--entities", type=int, default=2)
    ap.add_argument("--contracts", type=int, default=2)
    ap.add_argument("--titles", type=int, default=3)
    ap.add_argument("--claims", type=int, default=2)
    ap.add_argument("--manifest", default=None, help="Path manifest da salvare (default: omnia8_manifest_<user>.json)")
    args = ap.parse_args()

    base_url, user_id = args.base_url, args.user_id
    manifest_path = args.manifest or f"omnia8_manifest_{user_id}.json"

    print(f"\n== PING ==")
    api(base_url, "GET", "/ping")
    print("API OK.")

    TODAY = date.today()
    IN_3M = TODAY + timedelta(days=90)
    IN_6M = TODAY + timedelta(days=180)

    manifest = {
        "base_url": base_url,
        "user_id": user_id,
        "entities": [],
        "searchable_policies": [],
    }

    # CREAZIONE MASSIVA
    for e_idx in range(args.entities):
        entity_id = f"entity_{e_idx+1}_{uuid.uuid4().hex[:5]}"
        name = f"ENTITY {e_idx+1} S.p.A."
        ent = create_entity(base_url, user_id, entity_id, name, extra_note="seed massive")
        ent_block = {"entity_id": entity_id, "name": name, "contracts": []}

        for c_idx in range(args.contracts):
            pol = f"POL{e_idx+1}{c_idx+1}-{uuid.uuid4().hex[:6].upper()}"
            compagnia = random.choice(["Generali", "AIG Europe", "HDI", "Allianz"])
            rischio = random.choice(["RC Aeromobili", "ARD", "Infortuni", "KASKO DIP. IN MISSIONE"])
            contract_id = create_contract(base_url, user_id, entity_id, compagnia, pol, rischio_descr=rischio)
            manifest["searchable_policies"].append(pol)
            c_block = {"contract_id": contract_id, "numero_polizza": pol, "titles": [], "claims": [], "contract_docs": []}

            # Titoli
            for t_idx in range(args.titles):
                tipo = random.choice(["RATA", "QUIETANZA", "APPENDICE", "VARIAZIONE"])
                scad = IN_3M if t_idx % 2 == 0 else IN_6M
                title_id = create_title(base_url, user_id, entity_id, contract_id, tipo, TODAY, scad)
                t_block = {"title_id": title_id, "title_docs": []}
                # doc su titolo
                doc_id = create_title_doc(base_url, user_id, entity_id, contract_id, title_id, f"title content {title_id}")
                t_block["title_docs"].append(doc_id)
                c_block["titles"].append(t_block)

            # Sinistri
            for s_idx in range(args.claims):
                ns = f"{1000 + s_idx}"
                claim_id = create_claim(base_url, user_id, entity_id, contract_id, TODAY.year, ns)
                # 2 note diario
                d1 = add_diary(base_url, user_id, entity_id, contract_id, claim_id, "prima nota")
                d2 = add_diary(base_url, user_id, entity_id, contract_id, claim_id, "seconda nota")
                # doc su sinistro
                sd = create_claim_doc(base_url, user_id, entity_id, contract_id, claim_id, f"claim content {claim_id}")
                c_block["claims"].append({"claim_id": claim_id, "diary": [d1, d2], "claim_docs": [sd]})

            # doc su contratto
            cd = create_contract_doc(base_url, user_id, entity_id, contract_id, f"contract content {contract_id}")
            c_block["contract_docs"].append(cd)

            ent_block["contracts"].append(c_block)

        manifest["entities"].append(ent_block)

    # Viste & Indici
    for e in manifest["entities"]:
        r = api(base_url, "GET", f"/users/{user_id}/entities/{e['entity_id']}/titles")
        print(f"\n-- Vista TITOLI per {e['entity_id']} --")
        print(pretty(r.json())[:1200], "...")

        r = api(base_url, "GET", f"/users/{user_id}/entities/{e['entity_id']}/claims")
        print(f"\n-- Vista SINISTRI per {e['entity_id']} --")
        print(pretty(r.json())[:1200], "...")

    for pol in manifest["searchable_policies"][:2]:
        r = api(base_url, "GET", f"/users/{user_id}/search/policy/{pol}")
        print(f"\nRicerca indice Numero Polizza {pol}: {pretty(r.json())}")

    r = api(base_url, "GET", f"/users/{user_id}/dashboard/due")
    print("\n-- Dashboard scadenze (entro 120 gg) --")
    print(pretty(r.json()))

    # Salva manifest
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, indent=2, ensure_ascii=False)
    print(f"\n✅ Seed completato. Manifest salvato in: {manifest_path}\n")

if __name__ == "__main__":
    main()
