#!/usr/bin/env python3
"""
foamBatchGen.py — Generate OpenFOAM cases from a reference case and a CSV of parameters.

USAGE
-----
python3 foamBatchGen.py --csv runs.csv --ref ref --out ./cases_out --map mapping.json
# Optional flags
  [--dry-run]              : print what would change; do not write files
  [--overwrite]            : overwrite existing case directories
  [--only CASE1,CASE2]     : only build specified case_name(s) from the CSV (comma-separated)
  [--verbose]              : print more details

CSV FORMAT
----------
First column must be "case_name". Remaining columns are parameter names.
Example:
case_name,Re,endTime,deltaT,rho1,rho2,mu1,mu2,U0
e0.0_Re500,500,20,0.005,1000,1200,1e-3,5e-3,0.1

MAPPING FILE (JSON)
-------------------
Defines how CSV parameters map to files & keys/regex in the case.
Schema:
{
  "files": [
    {
      "path": "system/controlDict",
      "updates": [
        {"type": "key", "key": "endTime", "param": "endTime"},
        {"type": "key", "key": "deltaT", "param": "deltaT"}
      ]
    },
    {
      "path": "constant/transportProperties",
      "updates": [
        {"type": "key", "key": "rho1", "param": "rho1"},
        {"type": "key", "key": "rho2", "param": "rho2"},
        {"type": "key", "key": "mu1",  "param": "mu1"},
        {"type": "key", "key": "mu2",  "param": "mu2"}
      ]
    },
    {
      "path": "0/U",
      "updates": [
        {"type": "regex",
         "pattern": "(?m)^(\\s*internalField\\s+uniform\\s+).+?\\s*;",
         "replacement": "\\1(0 0 {U0});",
         "params": {"U0": "U0"}
        }
      ]
    }
  ]
}

NOTES
-----
- "type": "key" targets OpenFOAM-style entries:  <key>   <value>;
  The script replaces the value up to the semicolon, preserving leading whitespace and comments.
- "type": "regex" applies a Python regex replacement. Use "params" to reference CSV fields inside the replacement
  via {name}. All {name} placeholders in "replacement" will be formatted using a dict built from the CSV row.
- Values are inserted as-is. For vectors, pass CSV text like "(1 0 0)". For words, pass "on", "off", etc.
- You can include the same param in multiple files/updates.
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List

def read_mapping(map_path: Path) -> Dict[str, Any]:
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_csv(csv_path: Path) -> List[Dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty.")
    if "case_name" not in rows[0]:
        raise ValueError('CSV must include a "case_name" column (first column recommended).')
    return rows

def copy_reference_case(ref_path: Path, dest_path: Path, overwrite: bool) -> None:
    if dest_path.exists():
        if overwrite:
            shutil.rmtree(dest_path)
        else:
            raise FileExistsError(f"Destination already exists: {dest_path}")
    shutil.copytree(ref_path, dest_path, symlinks=True)

def set_foam_key(text: str, key: str, value: str) -> str:
    """
    Replace 'key  oldvalue;' with 'key  value;' (value inserted as given).
    Preserves leading whitespace and trailing comment on the same line.
    Matches the first occurrence of 'key' as a standalone token followed by anything up to ';'.
    """
    pattern = re.compile(rf'(?m)^(\s*{re.escape(key)}\s+)(.*?)(\s*;)([^\n\r]*)$')
    def repl(m):
        before, oldval, semi, after = m.groups()
        return f"{before}{value}{semi}{after}"
    new_text, n = pattern.subn(repl, text, count=1)
    if n == 0:
        raise KeyError(f"Key '{key}' not found")
    return new_text

def apply_regex(text: str, pattern: str, replacement: str, params_map: Dict[str, str], row: Dict[str, str]) -> str:
    """
    Apply regex with optional {placeholders} formatted from the row using params_map (name->csv_column).
    """
    # Build format dict from mapping
    fmt = {}
    for name, csv_col in (params_map or {}).items():
        if csv_col not in row:
            raise KeyError(f"Mapping references CSV column '{csv_col}' which is missing in the row")
        fmt[name] = row[csv_col]
    try:
        replacement_fmt = replacement.format(**fmt)
    except KeyError as e:
        raise KeyError(f"Replacement placeholder {e} not provided in params") from e
    return re.sub(pattern, replacement_fmt, text, flags=re.MULTILINE)

def apply_updates_to_file(file_path: Path, updates: List[Dict[str, Any]], row: Dict[str, str], dry_run: bool, verbose: bool) -> None:
    # Read text
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    original_text = text
    for upd in updates:
        utype = upd.get("type")
        if utype == "key":
            key = upd["key"]
            param = upd["param"]
            if param not in row:
                raise KeyError(f"CSV missing column '{param}' required for key '{key}' in {file_path}")
            value = row[param]
            if verbose:
                print(f"  - set key {key} = {value}")
            text = set_foam_key(text, key, value)
        elif utype == "regex":
            pattern = upd["pattern"]
            replacement = upd["replacement"]
            params_map = upd.get("params", {})
            if verbose:
                print(f"  - regex {pattern} -> {replacement}")
            text = apply_regex(text, pattern, replacement, params_map, row)
        else:
            raise ValueError(f"Unknown update type: {utype}")

    if text != original_text and not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

def build_case(row: Dict[str, str], ref: Path, out_dir: Path, mapping: Dict[str, Any], overwrite: bool, dry_run: bool, verbose: bool) -> None:
    case_name = row["case_name"]
    dest = out_dir / case_name
    if verbose:
        print(f"\n==> Building case: {case_name}")
        print(f"    from: {ref}")
        print(f"    to  : {dest}")
    if not dry_run:
        copy_reference_case(ref, dest, overwrite=overwrite)
    for fdesc in mapping.get("files", []):
        rel = fdesc["path"]
        updates = fdesc.get("updates", [])
        fpath = dest / rel
        if not fpath.exists():
            raise FileNotFoundError(f"File not found in case: {fpath}")
        if verbose:
            print(f" Editing: {rel}")
        apply_updates_to_file(fpath, updates, row, dry_run=dry_run, verbose=verbose)

def main():
    ap = argparse.ArgumentParser(description="Generate OpenFOAM cases from a reference and a CSV")
    ap.add_argument("--csv", required=True, help="CSV with case_name and parameters")
    ap.add_argument("--ref", required=True, help="Path to reference case directory")
    ap.add_argument("--out", required=True, help="Output directory for generated cases")
    ap.add_argument("--map", required=True, help="JSON mapping file")
    ap.add_argument("--dry-run", action="store_true", help="Analyze and print changes, do not write files")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing case directories")
    ap.add_argument("--only", type=str, default="", help="Comma separated list of case_name to build")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    ref_path = Path(args.ref).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    map_path = Path(args.map).expanduser().resolve()

    mapping = read_mapping(map_path)
    rows = read_csv(csv_path)

    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        rows = [r for r in rows if r["case_name"] in wanted]
        if not rows:
            print("No matching case_name rows for --only selection", file=sys.stderr)
            sys.exit(1)

    out_path.mkdir(parents=True, exist_ok=True)

    errors = 0
    for row in rows:
        try:
            build_case(row, ref_path, out_path, mapping, overwrite=args.overwrite, dry_run=args.dry_run, verbose=args.verbose)
        except Exception as e:
            errors += 1
            print(f"[ERROR] {row.get('case_name','<unknown>')}: {e}", file=sys.stderr)

    if errors:
        print(f"\nCompleted with {errors} error(s).", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll cases processed successfully.")

if __name__ == "__main__":
    main()
