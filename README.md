
# OpenFOAM Bath Case Generator (CSV → cases)

# Significance of foamBatchGen

In **computational fluid dynamics (CFD)** and particularly in **OpenFOAM workflows**, researchers and engineers often need to run many simulations to explore parameter spaces. 
Examples include changing:
- Reynolds numbers
- Fluid properties
- Time-step sizes
- Mesh resolutions
- Physical settings like eccentricity in wellbore geometries

Traditionally, this involves **cloning a reference case** and manually editing multiple files:
- `system/controlDict`
- `constant/transportProperties`
- `0/U`
- SLURM job scripts

This process is **slow and error-prone**. A single typo or missed update can invalidate results.

## Why foamCaseBuilder matters

**foamCaseBuilder** automates the process of creating new cases from a **reference case** and a **CSV parameter table**.

- ✅ **Consistency** – every case comes from the same clean baseline.
- ✅ **Scalability** – one CSV row = one simulation case. From 2 to 200 cases with no extra effort.
- ✅ **Reproducibility** – the CSV becomes a record of experiment design that can be rerun at any time.
- ✅ **Flexibility** – `mapping.json` lets you update any OpenFOAM dictionary or SLURM script entries.
- ✅ **Productivity** – focus on physics and analysis instead of repetitive file edits.

## When to use

- You already have a validated **reference case**.
- You want to **sweep parameters** systematically (eccentricity, viscosity, densities, time step, etc.).
- You run on **HPC clusters** where job scripts must reflect the correct settings (`#SBATCH --job-name`, `Ecc`, etc.).
- You need systematic, traceable simulation studies for a **paper or thesis**.

By automating repetitive edits, **foamBatchGen** accelerates research, reduces human error, and ensures your workflows remain reproducible and scalable.


**Files created here:**
- `foamBatchGen.py` — the generator app
- `mapping.json` — starter mapping
- You uploaded: `Example.csv` — your runs list

## Quick start
```bash
chmod +x foamBatchGen.py
python3 foamBatchGen.py --csv Example.csv --ref ref --out cases_out --map mapping.json --dry-run --verbose
# If everything looks good:
python3 foamBatchGen.py --csv Example.csv --ref ref --out cases_out --map mapping.json --overwrite --verbose
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

