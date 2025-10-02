# mutate_and_cleanup.py
"""
Aggiorna i dati creati da seed_many_data.py e poi pulisce tutto.
- Legge MANIFEST JSON con gli ID creati
- Aggiorna entità/contratti/titoli/sinistri/diario/documenti
- Verifica viste/indici
- Elimina note diario, documenti, titoli, sinistri, contratti, entità

Esecuzione:
    python mutate_and_cleanup.py --manifest omnia8_manifest_testuser.json
Opzioni:
    --base-url (se diverso da quello nel manifest)
"""

import argparse
import base64
import json
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

def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="Manifest JSON prodotto dal seed")
    ap.add_argument("--base-url", default=None)
    args = ap.parse_args()

    with open(args.manifest, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)

    base_url = args.base_url or manifest["base_url"]
    user_id = manifest["user_id"]

    print(f"\n== PING ==")
    api(base_url, "GET", "/ping")
    print("API OK.")

    TODAY = date.today()
    IN_1Y = TODAY + timedelta(days=365)

    # ------------------ UPDATE MASSIVO ------------------
    for e in manifest["entities"]:
        entity_id = e["entity_id"]

        # ENTITA' update
        r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}")
        entity = r.json()
        entity.setdefault("admin_data", {})["verified"] = True
        entity["admin_data"]["updated_by"] = "mutate_and_cleanup.py"
        api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}", json_body=entity)
        print(f"✓ Updated entity {entity_id}")

        for c in e["contracts"]:
            contract_id = c["contract_id"]

            # CONTRATTO update (RamiEl.Descrizione + Scadenza)
            r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}")
            contract = r.json()
            contract["RamiEl"]["Descrizione"] = contract["RamiEl"].get("Descrizione", "") + " (agg.)"
            contract["Amministrativi"]["Scadenza"] = IN_1Y.isoformat()
            api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}", json_body=contract)
            print(f"✓ Updated contract {contract_id}")

            # TITOLI update (primo titolo -> PAGATO)
            if c["titles"]:
                t0 = c["titles"][0]["title_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{t0}")
                titolo = r.json()
                titolo["stato"] = "PAGATO"
                titolo["data_pagamento"] = TODAY.isoformat()
                titolo["metodo_incasso"] = "BONIFICO"
                api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{t0}", json_body=titolo)
                print(f"✓ Updated title {t0}")

            # SINISTRI update (stato compagnia)
            for s in c["claims"]:
                claim_id = s["claim_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}")
                claim = r.json()
                claim["stato_compagnia"] = "Liquidato parziale"
                api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}", json_body=claim)
                print(f"✓ Updated claim {claim_id}")

                # Diario: update prima nota poi delete tutte
                if s["diary"]:
                    first = s["diary"][0]
                    upd = {"autore": "mutator", "testo": "nota aggiornata dal mutator"}
                    api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary/{first}", json_body=upd)
                    # get singola per verifica
                    r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary/{first}")
                    print(f"  Diario entry (after update): {pretty(r.json())}")

                # delete tutte le note
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary")
                for entry in r.json():
                    api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/diary/{entry['entry_id']}")
                print(f"✓ Cleared diary for claim {claim_id}")

            # DOCUMENTI: update + download + delete con GC blob
            # -- contract docs
            r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents")
            for doc_id in r.json():
                # update
                upd = {
                    "meta": {
                        "scope": "CONTRATTO",
                        "categoria": "ALTRO",
                        "mime": "text/plain",
                        "nome_originale": "contract_doc_updated.txt",
                        "size": len("updated contract content"),
                        "metadati": {"updated": True},
                    },
                    "content_base64": b64("updated contract content"),
                }
                api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}", json_body=upd)
                # get meta + download
                r_meta = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}")
                print(f"  Contract doc meta: {pretty(r_meta.json())}")
                r_dl = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}/download", stream=True)
                print(f"  Contract doc download bytes: {len(r_dl.content)}")
                # delete
                api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents/{doc_id}", params={"delete_blob": True})
            # -- claim docs
            for s in c["claims"]:
                claim_id = s["claim_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents")
                for doc_id in r.json():
                    upd = {
                        "meta": {
                            "scope": "SINISTRO",
                            "categoria": "CLAIM",
                            "mime": "text/plain",
                            "nome_originale": "claim_doc_updated.txt",
                            "size": len("updated claim content"),
                            "metadati": {"updated": True},
                        },
                        "content_base64": b64("updated claim content"),
                    }
                    api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}", json_body=upd)
                    r_meta = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}")
                    print(f"  Claim doc meta: {pretty(r_meta.json())}")
                    r_dl = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}/download", stream=True)
                    print(f"  Claim doc download bytes: {len(r_dl.content)}")
                    api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents/{doc_id}", params={"delete_blob": True})
            # -- title docs
            for t in c["titles"]:
                title_id = t["title_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents")
                for doc_id in r.json():
                    upd = {
                        "meta": {
                            "scope": "TITOLO",
                            "categoria": "APP",
                            "mime": "text/plain",
                            "nome_originale": "title_doc_updated.txt",
                            "size": len("updated title content"),
                            "metadati": {"updated": True},
                        },
                        "content_base64": b64("updated title content"),
                    }
                    api(base_url, "PUT", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}", json_body=upd)
                    r_meta = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}")
                    print(f"  Title doc meta: {pretty(r_meta.json())}")
                    r_dl = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}/download", stream=True)
                    print(f"  Title doc download bytes: {len(r_dl.content)}")
                    api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents/{doc_id}", params={"delete_blob": True})

    # Verifica viste/indici post-update
    for e in manifest["entities"]:
        r = api(base_url, "GET", f"/users/{user_id}/entities/{e['entity_id']}/titles")
        print(f"\n-- Vista TITOLI aggiornata per {e['entity_id']} --")
        print(pretty(r.json())[:1200], "...")

        r = api(base_url, "GET", f"/users/{user_id}/entities/{e['entity_id']}/claims")
        print(f"\n-- Vista SINISTRI aggiornata per {e['entity_id']} --")
        print(pretty(r.json())[:1200], "...")

    if manifest.get("searchable_policies"):
        pol = manifest["searchable_policies"][0]
        r = api(base_url, "GET", f"/users/{user_id}/search/policy/{pol}")
        print(f"\nRicerca indice Numero Polizza {pol}: {pretty(r.json())}")

    # ------------------ CLEANUP COMPLETO ------------------
    print("\n== CLEANUP ==")
    for e in manifest["entities"]:
        entity_id = e["entity_id"]
        for c in e["contracts"]:
            contract_id = c["contract_id"]

            # titoli -> delete
            r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles")
            for tid in r.json():
                api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{tid}")

            # sinistri -> delete (diario già ripulito sopra)
            r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims")
            for sid in r.json():
                api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{sid}")

            # contratti -> delete
            api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}")

        # entità -> delete
        api(base_url, "DELETE", f"/users/{user_id}/entities/{entity_id}")

    # verifica finale: lista entità
    r = api(base_url, "GET", f"/users/{user_id}/entities")
    print("\nEntità residue:", r.json())
    assert len(r.json()) == 0, "Cleanup incompleto: esistono ancora entità!"

    print("\n✅ Aggiornamento + Cleanup completati senza errori.\n")

if __name__ == "__main__":
    main()
