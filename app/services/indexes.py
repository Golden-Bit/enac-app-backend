from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List
from app.utils.utils import (
    contracts_dir, contract_file, titles_dir, claims_dir,
    views_dir_for_entity, by_policy_dir, entities_dir, user_dir
)
from app.utils.utils import read_json, atomic_write_json
from pathlib import Path
import json

def update_by_policy_index(user_id: str, numero_polizza: str, entity_id: str, contract_id: str) -> None:
    if not numero_polizza:
        return
    f = by_policy_dir(user_id) / f"{numero_polizza}.json"
    atomic_write_json(f, {"entity_id": entity_id, "contract_id": contract_id})

def rebuild_entity_views(user_id: str, entity_id: str) -> None:
    """Rigenera titles_index/claims_index per l'Entità."""
    titles: List[Dict[str, Any]] = []
    claims: List[Dict[str, Any]] = []

    croot = contracts_dir(user_id, entity_id)
    if not croot.exists():
        return
    for cdir in croot.iterdir():
        if not cdir.is_dir(): continue
        cjson = contract_file(user_id, entity_id, cdir.name)
        if not cjson.exists(): continue
        contract = read_json(cjson)
        n_pol = contract["Identificativi"]["NumeroPolizza"]
        compagnia = contract["Identificativi"]["Compagnia"]
        rischio = contract.get("RamiEl", {}).get("Descrizione")

        # titoli
        troot = titles_dir(user_id, entity_id, cdir.name)
        if troot.exists():
            for tf in troot.rglob("*.json"):
                if tf.parent.name == "documents":  # salta metadati documenti
                    continue
                t = read_json(tf)
                titles.append({
                    "contract_id": cdir.name,
                    "title_id": tf.stem,
                    "compagnia": compagnia,
                    "numero_polizza": n_pol,
                    "rischio": rischio,
                    "scadenza_titolo": t.get("scadenza_titolo"),
                    "stato": t.get("stato"),
                    "pv": t.get("pv"),
                    "pv2": t.get("pv2"),
                    "premio": t.get("premio_lordo"),
                })

        # sinistri
        sroot = claims_dir(user_id, entity_id, cdir.name)
        if sroot.exists():
            for sdir in sroot.iterdir():
                cf = sdir / "claim.json"
                if cf.exists():
                    s = read_json(cf); s["claim_id"] = sdir.name; s["contract_id"] = cdir.name
                    claims.append(s)

    vdir = views_dir_for_entity(user_id, entity_id)
    atomic_write_json(vdir / "titles_index.json", titles)
    atomic_write_json(vdir / "claims_index.json", claims)

def compute_due_indexes(user_id: str, days: int = 120) -> Dict[str, Any]:
    today = date.today(); limit = today + timedelta(days=days)
    contracts_due: List[Dict[str, Any]] = []; titles_due: List[Dict[str, Any]] = []
    for edir in entities_dir(user_id).iterdir():
        if not edir.is_dir(): continue
        for cdir in (edir / "contracts").iterdir():
            if not cdir.is_dir(): continue
            cj = cdir / "contract.json"
            if cj.exists():
                c = read_json(cj)
                scad = c.get("Amministrativi", {}).get("Scadenza")
                try:
                    d = date.fromisoformat(scad)
                    if today <= d <= limit:
                        contracts_due.append({
                            "entity_id": edir.name, "contract_id": cdir.name,
                            "numero_polizza": c["Identificativi"]["NumeroPolizza"],
                            "compagnia": c["Identificativi"]["Compagnia"],
                            "scadenza": scad,
                        })
                except Exception:
                    pass
            troot = cdir / "titles"
            if troot.exists():
                for tf in troot.rglob("*.json"):
                    if tf.parent.name == "documents": continue
                    t = read_json(tf); scadt = t.get("scadenza_titolo")
                    try:
                        dt = date.fromisoformat(scadt)
                        if today <= dt <= limit:
                            titles_due.append({
                                "entity_id": edir.name, "contract_id": cdir.name,
                                "title_id": tf.stem, "scadenza_titolo": scadt,
                                "stato": t.get("stato"), "premio": t.get("premio_lordo"),
                            })
                    except Exception:
                        pass
    return {"contracts_due": contracts_due, "titles_due": titles_due}

def iter_all_document_meta_files(user_id: str) -> list[Path]:
    base = user_dir(user_id)
    return list(base.glob("**/documents/*.json"))

def count_blob_references(user_id: str, sha1: str) -> int:
    total = 0
    for mf in iter_all_document_meta_files(user_id):
        try:
            meta = read_json(mf)
            if meta.get("hash") == sha1:
                total += 1
        except Exception:
            continue
    return total
