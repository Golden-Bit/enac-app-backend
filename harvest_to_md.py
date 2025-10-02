#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Harvester → Markdown
---------------------------------
Scansiona una directory (con profondità configurabile), applica filtri su path,
globs ed eventualmente sul contenuto ("blob"), e genera un output .md che
contiene:
  1) Una sezione per ogni file incluso, con intestazione + metadati e il
     contenuto incapsulato in un blocco di codice.
  2) Un albero finale dei soli file inclusi.

Esecuzione: eseguire direttamente questo file (nessun argomento richiesto).
Configurazione: modificare la sezione CONFIG qui sotto.
"""

from __future__ import annotations

import os
import re
import io
import sys
import hashlib
import datetime as dt
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple, Optional
import fnmatch

# ============================
# ========== CONFIG ==========
# ============================
CONFIG = {
    # Radice da cui partire ('.' = directory corrente)
    "ROOT_DIR": "./app/",

    # Profondità massima (0 = solo ROOT_DIR; 1 = root + 1 livello; None = illimitata)
    "MAX_DEPTH": None,  # es.: 3 oppure None

    # Includi solo path che rispettano ALMENO UNO di questi globs (vuoto = nessun vincolo)
    # Default: tutti i file .py in root e sottocartelle
    "INCLUDE_GLOBS": ["**/*.py"],

    # Escludi path che rispettano QUALSIASI di questi globs
    "EXCLUDE_GLOBS": [
        "**/.git/**",
        "**/__pycache__/**",
        "**/.venv/**",
        "**/venv/**",
        "**/env/**",
        "**/node_modules/**",
        "**/*.pyc",
        "**/*.pyo",
    ],

    # Liste esplicite (globs) di path da includere o escludere (priorità: INCLUDE_PATHS poi EXCLUDE_PATHS)
    "INCLUDE_PATHS": [],
    "EXCLUDE_PATHS": [],

    # Filtri sul contenuto (blob). Se non vuoti:
    # - CONTENT_INCLUDE_PATTERNS: il file deve contenere almeno uno dei pattern (regex per default)
    # - CONTENT_EXCLUDE_PATTERNS: il file viene escluso se contiene almeno uno dei pattern (regex per default)
    "CONTENT_INCLUDE_PATTERNS": [],
    "CONTENT_EXCLUDE_PATTERNS": [],

    # Se True interpreta i pattern di contenuto come regex; se False come semplici sottostringhe (case-insensitive)
    "CONTENT_FILTERS_AS_REGEX": True,

    # Includi file e directory nascosti? (quelli che iniziano per ".")
    "INCLUDE_HIDDEN": False,

    # Dimensione massima del file in MiB (None = nessun limite). Usato solo come salvagente per binari accidentali.
    "MAX_FILE_SIZE_MIB": 5,

    # File di output
    "OUTPUT_MD": "harvest_output.md",

    # Normalizza i separatori di path in stile POSIX per la stampa
    "PRINT_POSIX_PATHS": True,
}

# ============================
# ========== UTILS ===========
# ============================

LANG_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".html": "html",
    ".css": "css",
    ".sh": "bash",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".sql": "sql",
    ".ps1": "powershell",
}

def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")

def is_hidden(path: Path) -> bool:
    name = path.name
    return name.startswith(".")

def posix(path: Path) -> str:
    return path.as_posix()

def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_metadata(p: Path) -> Dict[str, Any]:
    try:
        stat = p.stat()
    except OSError:
        return {"size": None, "mtime": None}
    size = stat.st_size
    mtime = dt.datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    return {"size": size, "mtime": mtime}

def ext_to_lang(ext: str) -> str:
    return LANG_EXT.get(ext.lower(), "")

def within_depth(root: Path, path: Path, max_depth: Optional[int]) -> bool:
    if max_depth is None:
        return True
    rel = path.relative_to(root)
    # Numero di separatori nel path relativo => profondità
    depth = 0 if rel == Path('app') else len(rel.parts) - 1
    return depth <= max_depth

def match_any_glob(path_posix: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path_posix, pat) for pat in patterns)

def include_by_paths(path_posix: str, include_paths: List[str], exclude_paths: List[str]) -> bool:
    if include_paths:
        if not match_any_glob(path_posix, include_paths):
            return False
    if exclude_paths:
        if match_any_glob(path_posix, exclude_paths):
            return False
    return True

def apply_globs(path_posix: str, include_globs: List[str], exclude_globs: List[str]) -> bool:
    include_ok = True if not include_globs else match_any_glob(path_posix, include_globs)
    exclude_ok = not match_any_glob(path_posix, exclude_globs) if exclude_globs else True
    return include_ok and exclude_ok

def compile_patterns(patterns: List[str], as_regex: bool) -> List[Any]:
    if not patterns:
        return []
    if as_regex:
        return [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in patterns]
    else:
        # Sotto-stringhe case-insensitive
        return [p.lower() for p in patterns]

def content_matches(text: str, includes: List[Any], excludes: List[Any], as_regex: bool) -> bool:
    if includes:
        if as_regex:
            if not any(r.search(text) for r in includes):
                return False
        else:
            t = text.lower()
            if not any(s in t for s in includes):
                return False
    if excludes:
        if as_regex:
            if any(r.search(text) for r in excludes):
                return False
        else:
            t = text.lower()
            if any(s in t for s in excludes):
                return False
    return True

def read_file_text(p: Path, size_limit_mib: Optional[int]) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
    """Ritorna (text, raw_bytes, error_message). text è sempre in str (utf-8 con 'replace')."""
    try:
        if size_limit_mib is not None:
            max_bytes = int(size_limit_mib * 1024 * 1024)
            if p.stat().st_size > max_bytes:
                return None, None, f"File troppo grande (> {size_limit_mib} MiB)"
        raw = p.read_bytes()
        # Decodifica safe
        text = raw.decode("utf-8", errors="replace")
        return text, raw, None
    except Exception as e:
        return None, None, f"Errore di lettura: {e}"

def prune_dirs_by_depth(root: Path, dirs: List[str], current_path: Path, max_depth: Optional[int], include_hidden: bool):
    """Modifica in-place la lista dirs per rispettare profondità e hidden."""
    # Escludi directory nascoste, se richiesto
    if not include_hidden:
        dirs[:] = [d for d in dirs if not d.startswith(".")]
    if max_depth is None:
        return
    # Calcola profondità del path corrente rispetto a root
    rel = current_path.relative_to(root)
    curr_depth = 0 if rel == Path('app') else len(rel.parts) - 1
    # Se aggiungere un altro livello supererebbe la profondità, svuota dirs
    if curr_depth >= max_depth:
        dirs[:] = []

def build_tree(paths: List[Path], root: Path) -> Dict[str, Any]:
    """Costruisce un albero (dict annidati) dei soli path forniti."""
    tree: Dict[str, Any] = {}
    for p in paths:
        rel = p.relative_to(root)
        cursor = tree
        parts = list(rel.parts)
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            if is_last:
                cursor.setdefault("__files__", []).append(part)
            else:
                cursor = cursor.setdefault(part, {})
    return tree

def render_tree(tree: Dict[str, Any], prefix: str = "") -> List[str]:
    """Rende un albero ASCII a partire dalla struttura prodotta da build_tree."""
    lines: List[str] = []
    # Directory entries (keys except "__files__")
    dir_items = sorted([k for k in tree.keys() if k != "__files__"])
    file_items = sorted(tree.get("__files__", []))

    total_items = len(dir_items) + len(file_items)
    for idx, name in enumerate(dir_items):
        is_last = (idx == total_items - 1) if not file_items else False
        connector = "└── " if is_last and not file_items else "├── "
        lines.append(f"{prefix}{connector}{name}/")
        sub = tree[name]
        extension = "    " if connector == "└── " and not file_items else "│   "
        lines.extend(render_tree(sub, prefix + extension))

    for idx, name in enumerate(file_items):
        is_last = (idx == len(file_items) - 1)
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}")
    return lines

def gather_files(cfg: Dict[str, Any]) -> List[Path]:
    root = Path(cfg["ROOT_DIR"]).resolve()
    include_hidden = cfg["INCLUDE_HIDDEN"]
    include_globs = cfg["INCLUDE_GLOBS"]
    exclude_globs = cfg["EXCLUDE_GLOBS"]
    include_paths = cfg["INCLUDE_PATHS"]
    exclude_paths = cfg["EXCLUDE_PATHS"]
    max_depth = cfg["MAX_DEPTH"]
    posix_print = cfg["PRINT_POSIX_PATHS"]

    matched: List[Path] = []
    for curr, dirs, files in os.walk(root):
        curr_path = Path(curr)
        prune_dirs_by_depth(root, dirs, curr_path, max_depth, include_hidden)
        # Escludi directory nascoste (già gestito in prune); per i file, controlliamo sotto
        for fname in files:
            p = curr_path / fname
            if not include_hidden and is_hidden(p):
                continue
            if not within_depth(root, p, max_depth):
                continue
            p_posix = posix(p) if posix_print else str(p)
            # Applica globs include/exclude
            if not apply_globs(p_posix, include_globs, exclude_globs):
                continue
            # Applica include/exclude paths espliciti
            if not include_by_paths(p_posix, include_paths, exclude_paths):
                continue
            matched.append(p)
    matched = sorted(set(matched))
    return matched

def generate_markdown(cfg: Dict[str, Any]) -> Tuple[str, List[Path], List[str]]:
    root = Path(cfg["ROOT_DIR"]).resolve()
    files = gather_files(cfg)
    content_inc = compile_patterns(cfg["CONTENT_INCLUDE_PATTERNS"], cfg["CONTENT_FILTERS_AS_REGEX"])
    content_exc = compile_patterns(cfg["CONTENT_EXCLUDE_PATTERNS"], cfg["CONTENT_FILTERS_AS_REGEX"])
    as_regex = cfg["CONTENT_FILTERS_AS_REGEX"]
    size_limit = cfg["MAX_FILE_SIZE_MIB"]
    posix_print = cfg["PRINT_POSIX_PATHS"]

    per_file_sections: List[str] = []
    skipped_info: List[str] = []
    included_paths: List[Path] = []

    for p in files:
        text, raw, err = read_file_text(p, size_limit)
        pmd = posix(p) if posix_print else str(p)
        meta = file_metadata(p)
        if err:
            skipped_info.append(f"- {pmd} → SKIP ({err})")
            continue

        # Filtri sul contenuto
        if not content_matches(text or "", content_inc, content_exc, as_regex):
            skipped_info.append(f"- {pmd} → SKIP (non rispetta i filtri sul contenuto)")
            continue

        included_paths.append(p)
        lang = ext_to_lang(p.suffix)
        hashval = sha256_of_bytes(raw or b"")
        header = (
            f"---8<--- START FILE: {pmd}\n"
            f"**Percorso**: `{pmd}`  \n"
            f"**Dimensione**: {meta['size']} B  —  **SHA256**: `{hashval}`  —  **Modificato**: {meta['mtime']}\n\n"
        )
        codeblock_open = f"```{lang}\n" if lang else "```\n"
        codeblock_close = "```\n"
        footer = f"\n---8<--- END FILE: {pmd}\n"
        section = header + codeblock_open + (text or "") + "\n" + codeblock_close + footer
        per_file_sections.append(section)

    # Header generale
    header_md = [
        "# Esportazione file → Markdown",
        "",
        f"- **Generato**: {now_iso()}",
        f"- **Root**: `{posix(root) if posix_print else str(root)}`",
        f"- **Profondità max**: {cfg['MAX_DEPTH']}",
        f"- **Include globs**: {cfg['INCLUDE_GLOBS']}",
        f"- **Esclude globs**: {cfg['EXCLUDE_GLOBS']}",
        f"- **Include paths**: {cfg['INCLUDE_PATHS']}",
        f"- **Esclude paths**: {cfg['EXCLUDE_PATHS']}",
        f"- **Filtri contenuto (include)**: {cfg['CONTENT_INCLUDE_PATTERNS']} (regex={cfg['CONTENT_FILTERS_AS_REGEX']})",
        f"- **Filtri contenuto (exclude)**: {cfg['CONTENT_EXCLUDE_PATTERNS']} (regex={cfg['CONTENT_FILTERS_AS_REGEX']})",
        f"- **File inclusi**: {len(included_paths)}",
        "",
        "---",
        "",
    ]

    body_md = "\n".join(per_file_sections) if per_file_sections else "_Nessun file incluso con la configurazione corrente._\n"

    # Albero finale dei soli file inclusi
    tree_md = "## Albero dei file (solo inclusi)\n\n"
    if included_paths:
        tree = build_tree(included_paths, root)
        lines = [posix(root) + "/"] + render_tree(tree, prefix="")
        tree_md += "```\n" + "\n".join(lines) + "\n```\n"
    else:
        tree_md += "_(vuoto)_\n"

    # Sezione 'skipped' per trasparenza
    if skipped_info:
        tree_md += "\n<details>\n<summary>File scartati (per dimensione/filtri/errori)</summary>\n\n"
        tree_md += "\n".join(skipped_info) + "\n\n</details>\n"

    md = "\n".join(header_md) + body_md + "\n\n" + tree_md
    return md, included_paths, skipped_info

def write_text_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def main() -> None:
    cfg = CONFIG.copy()
    output_path = Path(cfg["OUTPUT_MD"]).resolve()

    md, included, skipped = generate_markdown(cfg)
    write_text_file(output_path, md)

    print(f"[OK] Output MD scritto in: {output_path}")
    print(f"[INFO] File inclusi: {len(included)}")
    if skipped:
        print(f"[INFO] File scartati: {len(skipped)}")
    else:
        print("[INFO] Nessun file scartato.")

if __name__ == "__main__":
    main()
