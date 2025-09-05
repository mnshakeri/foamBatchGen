
# OpenFOAM Case Builder (CSV → cases)

**Files created here:**
- `foamBatchGen.py` — the generator app
- `mapping.json` — starter mapping
- You uploaded: `ExplanatoryCases.csv` — your runs list

## Quick start
```bash
chmod +x foamBatchGen.py
python3 foamBatchGen.py --csv ExplanatoryCases.csv --ref ref --out cases_out --map mapping.json --dry-run --verbose
# If everything looks good:
python3 foamBatchGen.py --csv ExplanatoryCases.csv --ref ref --out cases_out --map mapping.json --overwrite --verbose
```

- The `ref` directory should be your reference OpenFOAM case folder (with `system/`, `constant/`, `0/` etc.).
- Edit `mapping.json` to point parameters to the correct files/keys/regex for your solver and setup.
- Use `--only name1,name2` to build a subset by `case_name`.

## CSV expectations
- Must have a `case_name` column (unique name per row). Other columns define parameters you want to inject.
- Example columns you might include: `endTime, deltaT, rho1, rho2, mu1, mu2, U0, Re, e, caseNotes`.

## Mapping mechanics
- `"type": "key"` updates lines like `key   value;` in OpenFOAM dictionaries.
- `"type": "regex"` lets you surgically edit lines/blocks. You can interpolate CSV values into the `replacement`
  using `{name}` placeholders defined in `params` (name→CSV column).

## Tips
- Start with `--dry-run` to verify.
- For vector/scalar values, pass the exact OpenFOAM text in CSV (e.g. `(1 0 0)` or `1e-3`).
- You can add more files to `mapping.json` (e.g., `0/alpha`, `system/fvSchemes`, custom dictionaries, etc.).

