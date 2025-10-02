# query_views_and_searches.py
"""
Query & Views test per Omnia8 File-API (localhost:8111).
- Legge il MANIFEST prodotto da seed_many_data.py
- Esegue viste aggregate (titoli/sinistri per entità)
- Verifica coerenza con il manifest (conteggi e ID)
- Ricerca per Numero Polizza (indice secondario) e cross-check
- Dashboard scadenze (30/120/365 giorni) con assert di monotonicità
- Verifica documenti associati a contratti/sinistri/titoli

Esecuzione:
    python query_views_and_searches.py --manifest omnia8_manifest_testuser.json
Opzioni:
    --base-url http://127.0.0.1:8111  (se diverso da quello nel manifest)
    --strict-checks                    (default: attivo) fallisce su mismatch
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pprint import pformat
import requests

def pretty(x): return pformat(x, width=120)

def api(base_url, method, path, *, params=None, json_body=None, ok_codes=(200, 201), stream=False):
    url = base_url + path
    r = requests.request(method, url, params=params, json=json_body, stream=stream)
    if r.status_code not in ok_codes:
        raise RuntimeError(f"{method} {path} -> {r.status_code}\n{r.text}")
    return r

def banner(title: str):
    print("\n" + "="*10 + f" {title} " + "="*10)

def assert_equal(a, b, msg):
    if a != b:
        raise AssertionError(f"{msg}: atteso={b}, ottenuto={a}")

def load_manifest(path):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)

def map_policy_to_contract(manifest):
    mapping = {}
    for e in manifest["entities"]:
        entity_id = e["entity_id"]
        for c in e["contracts"]:
            mapping[c["numero_polizza"]] = (entity_id, c["contract_id"])
    return mapping

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--strict-checks", action="store_true", default=True)
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    base_url = args.base_url or manifest["base_url"]
    user_id = manifest["user_id"]

    banner("PING")
    api(base_url, "GET", "/ping")
    print("API raggiungibile.")

    pol_map = map_policy_to_contract(manifest)

    # ===========================
    # VISTE PER ENTITA'
    # ===========================
    for ent in manifest["entities"]:
        entity_id = ent["entity_id"]
        banner(f"VISTA TITOLI — Entity {entity_id}")
        r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/titles")
        titles = r.json()
        print(f"Totale titoli in vista: {len(titles)}")
        # Conteggi attesi dal manifest
        expected_titles = sum(len(c["titles"]) for c in ent["contracts"])
        print(f"Titoli attesi da manifest: {expected_titles}")
        if args.strict_checks:
            assert_equal(len(titles), expected_titles, f"Mismatch count titoli per {entity_id}")

        # breakdown per stato / compagnia / rischio
        stato_ctr = Counter(t.get("stato") for t in titles)
        comp_ctr = Counter(t.get("compagnia") for t in titles)
        rischio_ctr = Counter(t.get("rischio") for t in titles)
        print("Per STATO:", stato_ctr)
        print("Per COMPAGNIA:", comp_ctr)
        print("Per RISCHIO:", rischio_ctr)

        # Controllo copertura ID (tutti i title_id del manifest devono essere presenti nella vista)
        view_title_ids = {t["title_id"] for t in titles}
        manifest_title_ids = {tt["title_id"] for c in ent["contracts"] for tt in c["titles"]}
        missing = manifest_title_ids - view_title_ids
        if args.strict_checks and missing:
            raise AssertionError(f"Titoli mancanti in vista per {entity_id}: {missing}")
        # Stampa esempio
        if titles:
            print("Esempio record titolo:", pretty(titles[0]))

        banner(f"VISTA SINISTRI — Entity {entity_id}")
        r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/claims")
        claims = r.json()
        print(f"Totale sinistri in vista: {len(claims)}")
        expected_claims = sum(len(c["claims"]) for c in ent["contracts"])
        print(f"Sinistri attesi da manifest: {expected_claims}")
        if args.strict_checks:
            assert_equal(len(claims), expected_claims, f"Mismatch count sinistri per {entity_id}")

        # breakdown per esercizio / stato compagnia
        esercizio_ctr = Counter(c.get("esercizio") for c in claims)
        stato_comp_ctr = Counter(c.get("stato_compagnia") for c in claims)
        print("Per ESERCIZIO:", esercizio_ctr)
        print("Per STATO_COMPAGNIA:", stato_comp_ctr)

        view_claim_ids = {c["claim_id"] for c in claims}
        manifest_claim_ids = {s["claim_id"] for c in ent["contracts"] for s in c["claims"]}
        missing_c = manifest_claim_ids - view_claim_ids
        if args.strict_checks and missing_c:
            raise AssertionError(f"Sinistri mancanti in vista per {entity_id}: {missing_c}")
        if claims:
            print("Esempio record sinistro:", pretty(claims[0]))

    # ===========================
    # RICERCA PER NUMERO POLIZZA
    # ===========================
    banner("RICERCA PER NUMERO POLIZZA (indice secondario)")
    searched = set()
    for pol, (entity_id, contract_id) in pol_map.items():
        r = api(base_url, "GET", f"/users/{user_id}/search/policy/{pol}")
        found = r.json()
        print(f"{pol}: {found}")
        if args.strict_checks:
            assert_equal(found["entity_id"], entity_id, f"entity_id by-policy per {pol}")
            assert_equal(found["contract_id"], contract_id, f"contract_id by-policy per {pol}")
        searched.add(pol)

    # Prova policy inesistente (si attende 404)
    fake = "POL-NON-ESISTE-XYZ"
    try:
        api(base_url, "GET", f"/users/{user_id}/search/policy/{fake}", ok_codes=(200,),)
        print("ATTENZIONE: la ricerca fittizia non ha prodotto 404 come atteso.")
    except RuntimeError as e:
        print(f"OK (atteso 404) ricerca policy inesistente '{fake}':", str(e).splitlines()[0])

    # ===========================
    # DASHBOARD SCADENZE
    # ===========================
    banner("DASHBOARD SCADENZE (30 / 120 / 365 giorni)")
    def get_due(days):
        r = api(base_url, "GET", f"/users/{user_id}/dashboard/due", params={"days": days})
        return r.json()

    due30  = get_due(30)
    due120 = get_due(120)
    due365 = get_due(365)

    def sizes(d): return len(d.get("contracts_due", [])), len(d.get("titles_due", []))
    c30, t30   = sizes(due30)
    c120, t120 = sizes(due120)
    c365, t365 = sizes(due365)
    print(f"Entro  30 gg → contratti: {c30}, titoli: {t30}")
    print(f"Entro 120 gg → contratti: {c120}, titoli: {t120}")
    print(f"Entro 365 gg → contratti: {c365}, titoli: {t365}")

    if args.strict_checks:
        # monotonicità: finestre più ampie non devono restituire meno elementi
        assert c30  <= c120 <= c365, "Monotonicità contratti_due violata"
        assert t30  <= t120 <= t365, "Monotonicità titles_due violata"

    # Stampa top 5 prossime scadenze (titoli)
    def parse_date(dstr):
        try: return date.fromisoformat(dstr)
        except: return None

    titles_sorted = sorted(due120.get("titles_due", []), key=lambda x: (parse_date(x.get("scadenza_titolo")) or date.max))
    print("\nProssimi TITOLI in scadenza (entro 120gg) [top 5]:")
    for row in titles_sorted[:5]:
        print(" -", row)

    contracts_sorted = sorted(due120.get("contracts_due", []), key=lambda x: (parse_date(x.get("scadenza")) or date.max))
    print("\nProssimi CONTRATTI in scadenza (entro 120gg) [top 5]:")
    for row in contracts_sorted[:5]:
        print(" -", row)

    # ===========================
    # VERIFICA DOCUMENTI
    # ===========================
    banner("VERIFICA DOCUMENTI associati")
    for ent in manifest["entities"]:
        entity_id = ent["entity_id"]
        for c in ent["contracts"]:
            contract_id = c["contract_id"]

            # Contratto
            r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/documents")
            contract_docs = r.json()
            print(f"[{entity_id}/{contract_id}] docs contratto: {len(contract_docs)} → {contract_docs}")
            if args.strict_checks:
                assert len(contract_docs) >= 1, "Atteso almeno 1 documento su contratto (seed)"

            # Sinistri
            for s in c["claims"]:
                claim_id = s["claim_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/claims/{claim_id}/documents")
                claim_docs = r.json()
                print(f"[{entity_id}/{contract_id}/{claim_id}] docs sinistro: {len(claim_docs)} → {claim_docs}")
                if args.strict_checks:
                    assert len(claim_docs) >= 1, "Atteso almeno 1 documento su sinistro (seed)"

            # Titoli
            for t in c["titles"]:
                title_id = t["title_id"]
                r = api(base_url, "GET", f"/users/{user_id}/entities/{entity_id}/contracts/{contract_id}/titles/{title_id}/documents")
                title_docs = r.json()
                print(f"[{entity_id}/{contract_id}/{title_id}] docs titolo: {len(title_docs)} → {title_docs}")
                if args.strict_checks:
                    assert len(title_docs) >= 1, "Atteso almeno 1 documento su titolo (seed)"

    banner("RIASSUNTO")
    print("• Viste titoli/sinistri coerenti con il manifest.")
    print("• Ricerca Numero Polizza allineata a entity/contract attesi.")
    print("• Dashboard scadenze coerente (monotonicità verificata).")
    print("• Documenti presenti su contratto/sinistro/titolo come da seed.")
    print("\n✅ Tutti i test di viste & ricerche sono passati.\n")

if __name__ == "__main__":
    main()
