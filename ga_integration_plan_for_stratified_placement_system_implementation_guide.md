# GA Integration Plan for Stratified Placement System (Implementation Guide)

> **Purpose**: Add a file-driven **Genetic Algorithm (GA)** that evolves CSV placements produced by the stratified placement engine. The GA will: (1) read existing CSVs as individuals, (2) score them using `placement_metrics.py`, (3) produce children via **band-wise crossover** and **band-respecting mutations**, (4) **repair & refine** children using a short Phase‑C pass, and (5) iterate across generations with **elitism** and **immigrants**.

---

## 0A. Addendum — External Fitness & Non‑Intrusive Integration (Overrides)

**This section adapts the plan to your three constraints:**

1) **External Fitness**: The GA **does not** compute fitness. It **accepts a curated set of fit parents** (CSV layouts) selected by an external solver/evaluator and **only** performs crossover, mutation, repair/refinement, and output. Selection and ranking are out‑of‑scope.

2) **Non‑Intrusive**: The **existing code paths remain unchanged**. GA features live in a new, optional tool that **imports** but does **not modify** current modules. Nothing changes in `run_placement.py` behavior unless the new tool is explicitly invoked.

3) **On‑Demand Trigger**: GA is executed **only when the user asks to generate new layouts from given layout(s)**. Two modes are provided:
   - **Variant Mode (single‑parent)**: produce N mutated variants of a **given CSV** layout, preserving bands/quotas.
   - **Offspring Mode (multi‑parent)**: given a **parent set** (all externally judged fit), produce a next‑gen **offspring set** via band‑wise crossover + band‑respecting mutation + repair. No internal selection.

### Practical Consequences (overrides to prior sections)
- **(Replaces Section 5 – Fitness)**: Remove any internal fitness calculation. Keep only **logging** of external scores if they are provided alongside parents (for traceability).
- **(Replaces Section 6 – Selection)**: Remove internal selection. The **input parent set** **is** the selection. GA generates children from this set and stops.
- **(Modifies Section 10 – Orchestrator)**: The driver takes **parents** (via manifest or directory) and outputs **children**. Optionally repeats if the external process supplies the next curated parent set. No internal stop conditions based on fitness; only **count‑based** or **generation‑count** limits.
- **(Modifies Section 12 – Logging)**: Logs should capture **lineage** (which parents produced which child), operation mode (variant/offspring), repair notes, and any externally supplied scores; no internal fitness math.
- **(Modifies Section 14 – Integration)**: Provide a **separate CLI** (e.g., `evolve_from_layouts`) under a new folder. Do **not** add GA flags to `run_placement.py` unless desired later.

---

## 0B. External‑Fitness Evolution Flow (One‑Shot & Handshake)

**Inputs** (provided by the external evaluator/solver):
- **Parent layouts**: one or more CSV files in the existing schema.
- **Optional parent manifest** (CSV): rows with `id,path[,score,weight,tags]`. Scores/weights are **not used for selection** (already done externally) but are logged.

**Outputs**:
- **Children layouts**: CSVs in a new generation folder (e.g., `ga_ext/gen_001/child_000.csv`, …).
- **Lineage log**: CSV mapping each child to its parents and listing operations (crossover mask, mutation ops applied, repair notes).

**One‑Shot Runs**:
- **Variant Mode**: given `parent.csv` and a desired count `N`, produce `N` **mutated variants** only, then exit.
- **Offspring Mode**: given `P` parents, produce `C` children via crossover+mutation+repair, then exit. (External process then evaluates and passes back a new parent set.)

**Handshake Loop (for multiple generations)**:
- Tool runs **per generation** and **exits**. External system evaluates children and, if continuing, provides the next curated parent set. This keeps responsibilities clean and avoids background/asynchronous GA logic.

---

## 0C. New Optional Tooling (Non‑Intrusive)

- Add a new folder (e.g., `/ga_ext/`) that **imports** existing modules (`config_loader`, band helpers, repair/refinement helpers) **without modifying** them.
- Provide a **standalone CLI** (e.g., `evolve_from_layouts`) with flags:
  - `--parents-manifest <file>` **or** `--parents-dir <folder>`
  - `--mode variant|offspring`
  - `--children <int>` (offspring count) **or** `--variants <int>` (variant count)
  - `--output-root <folder>` (default: `ga_ext/`)
  - `--wy <float>`, `--repair-max-iters <int>`, `--crossover-rate <0..1>`, `--mutation-rate <0..1>`
  - `--immigrants <int>` (optional: inject a few fresh random layouts using current generator)
  - `--seed <int|null>` for reproducibility
- **No changes** to `run_placement.py`. The new tool is purely additive.

---

## 0D. Data Contracts (External Fitness Mode)

- **Parent CSV format**: unchanged (name,type,x,y).
- **Parent manifest CSV** (optional):
  - Columns: `id,path[,score,weight,tags]`.
  - `path` is relative or absolute to the project root.
- **Lineage log (output)**: per child row: `child_path,parent_ids,mode,crossover_mask,mutation_ops,repair_notes,seed`.
- **Repair notes** should include: conflicts resolved, quota borrows (if any), radius adjustments (if any), count of local improvements.

---

## 0E. Operations (What the Tool Actually Does)

- **Variant Mode** (single parent):
  1) Read a single parent CSV. 2) Apply **band‑respecting mutations** to create each variant. 3) **Repair & refine** each variant. 4) Save children + lineage log. *(No crossover.)*

- **Offspring Mode** (multi‑parent):
  1) Load the provided parent set (selection done externally). 2) Create children by **band‑wise crossover** between randomly paired parents (or pairs formed according to optional external weights), then apply **band‑respecting mutations**. 3) **Repair & refine** each child within bands using existing Phase‑C‑style local improvements. 4) Save children + lineage log.

- **Immigrants (optional)**: Add a small number of **fresh random layouts** produced by the existing generator to maintain diversity, if external process asks for it. (These are not evaluated internally.)

---

## 0F. Config (External Fitness Simplified)

- Keep a separate config file (e.g., `ga_ext_config.yaml`) with only the knobs needed for **generation**, not selection:
  - `crossover_rate`, `mutation_rate`, `variants`/`children`, `repair_max_iters`, `wy`, `immigrants`, `seed`.
  - No fitness weights or internal selection settings.

---

## 0G. Testing & Safety

- Ensure that **repair** always returns: no overlaps, allowed regions respected, quotas met or explicitly recorded with minimal borrow.
- Add tests for:
  - Variant mode from a single parent (produces N valid variants).
  - Offspring mode from two parents (produces valid children; lineage logged).
  - Edge cases: fully dense bands, conflicting parents occupying same cell, missing manifest paths.
- Persist **all** outputs; never overwrite unless `--overwrite` is explicitly passed.

---

## 0H. Backward Compatibility

- The presence of `/ga_ext/` and `evolve_from_layouts` does **not** change any existing behavior. If users continue using `run_placement.py`, they get identical results as before.
- GA functionality is **opt‑in** and only triggered by running the new tool with explicit arguments.

---


## 0. Assumptions & Constraints

- The project already contains:
  - `run_placement.py` (entry point), `stratified_placement.py` (core algorithm), `placement_metrics.py` (quality metrics), `visualization.py`, `config_loader.py`.
  - CSV schema:
    ```csv
    name,type,x,y
    acinlet_x5_y4,acinlet,5,4
    ...
    ```
- Bands/quotas are part of the algorithmic design (Phase A/B), and local union-level refinement (Phase C) exists or can be exposed via a helper.
- All children must conform to: **no overlaps**, **respect allowed regions**, **meet quotas** (or record controlled deviations), **meet/approach separation radii**.

---

## 1. New Files to Add

```
# New GA package
/ga/
  __init__.py
  ga_config.yaml                  # GA hyperparameters
  driver.py                       # Orchestrates the GA loop (CLI)
  selection.py                    # Tournament / roulette selection
  crossover.py                    # Band-wise (and optional 2D block) crossover
  mutation.py                     # Band-respecting mutations
  repair.py                       # Conflict/quota/separation repair + Phase‑C lite
  io_utils.py                     # CSV I/O, naming, folder layout, seeds
  diversity.py                    # Optional: distance metrics for diversity bonuses
  logging_utils.py                # Fitness logs, hall-of-fame, checkpoints

# Optional CLI alias at root
run_ga.py                         # Thin wrapper that calls ga/driver.py
```



## 6. Selection (`ga/selection.py`)

### Tournament Selection (recommended)
```python
def tournament_select(pop: list[Individual], k: int) -> Individual:
    """Pick k random individuals, return the one with max fitness."""
```

(Optionally add roulette-wheel later.)

---

## 7. Crossover (`ga/crossover.py`)

### 7.1 Band‑Wise Crossover (Primary)
**Goal**: combine parents while respecting vertical stratification.

**Algorithm**:
1. Partition each parent’s placements by `(entity_type, band_id)`.
2. For each `(entity_type, band_id)`:
   - Flip a biased/unbiased coin according to `crossover_rate` to choose Parent A or B’s subset.
   - Append chosen subset to child’s provisional list.
3. Record **conflicts** (duplicate cells) and **quota imbalances** for later repair.

```python
def bandwise_crossover(A: Individual, B: Individual, cfg) -> Individual:
    # returns provisional child (possibly invalid → send to repair)
```

### 7.2 Optional Block‑2D Crossover
- Partition into `Nx × Ny` rectangular cells; inherit per cell per entity from A or B.

### 7.3 Entity‑Wise Crossover (Coarse)
- Take all `vinlet` from A and all `acinlet` from B, etc.; expect more repair.

---

## 8. Mutation (`ga/mutation.py`)

### 8.1 Operators (Band‑Respecting)
1. **within_band_swap**(entity_type)
   - Swap x (or positions) of two placements of the same entity inside the same band if it increases min distance.
2. **band_local_jitter**
   - Move one placement to a nearby free cell in the same band that improves separation and respects allowed region.
3. **micro_reseed**
   - Select a small fraction (e.g., 5–10%) of placements of one entity; drop and re-place using Phase‑B logic **within the same band**.

```python
def mutate(ind: Individual, cfg, engine_helpers) -> Individual:
    # apply operators with probabilities from cfg; bound changes per gene
```

---

## 9. Repair & Local Refinement (`ga/repair.py`)

**Purpose**: Make children valid and improve worst-case distances (Phase‑C lite). Implement as a constrained local search.

### 9.1 Engine Hooks to Expose in `stratified_placement.py`
```python
def repair_conflicts_and_quotas(rows: list[Placement], cfg) -> tuple[list[Placement], dict]:
    """Fix cell conflicts, adjust to meet per-band quotas (allow controlled borrow)."""

def refine_union_within_bands(rows: list[Placement], cfg) -> list[Placement]:
    """Run limited iterations of local swaps/nudges to increase worst min distance
    under anisotropic metric (wy), without breaking quotas or allowed regions."""
```

### 9.2 Repair Pipeline
1. **Cell conflicts**: if two entities occupy same `(x,y)`, attempt within‑band swaps; else relocate one to best free cell maximizing min distance.
2. **Quota fixes**: if band/entity overfull, move surplus to underfull bands (prefer adjacent). Record `quota_borrow` in notes if needed.
3. **Separation pass**: limited iterations of local improvement (lexicographic maximin objective on min distance) with constraints.

```python
def repair_and_refine(child: Individual, cfg) -> Individual:
    rows, notes = repair_conflicts_and_quotas(child.rows, cfg)
    rows = refine_union_within_bands(rows, cfg)
    child.rows, child.meta['repair_notes'] = rows, notes
    return child
```

---

## 10. GA Orchestrator (`ga/driver.py`)

### 10.1 CLI
```bash
python3 -m ga.driver \
  --config ga/ga_config.yaml \
  --init-from-run-placement 80 \
  --output-root ga/
```

### 10.2 High‑Level Flow
```python
def run_ga(cfg_path: str, output_root: str):
    cfg = load_yaml(cfg_path)
    rng = make_rng(cfg["random_seed"])  # numpy + random seeded

    # Gen 0: initialize
    pop = init_population(output_root, cfg, rng)
    score_all(pop, cfg)
    log_fitness(pop, gen=0)

    best = get_best(pop)
    no_improve = 0

    for gen in range(1, cfg["max_generations"] + 1):
        next_pop = []
        # Elitism
        next_pop += top_k(pop, cfg["elitism_k"])  # deep copy

        # Create children
        while len(next_pop) < cfg["population_size"]:
            A = tournament_select(pop, cfg["tournament_size"], rng)
            B = tournament_select(pop, cfg["tournament_size"], rng)
            child = bandwise_crossover(A, B, cfg)  # or strategy switch
            child = mutate(child, cfg, engine_helpers)
            child = repair_and_refine(child, cfg)
            next_pop.append(child)

        # Immigrants
        next_pop += immigrants_from_run_placement(cfg, output_root, rng)

        # Evaluate and downselect to P best
        score_all(next_pop, cfg)
        pop = best_P(next_pop, cfg["population_size"])  # trims extra

        log_fitness(pop, gen)
        update_hof(pop)

        new_best = get_best(pop)
        if new_best.fitness > best.fitness:
            best = new_best
            no_improve = 0
        else:
            no_improve += 1

        if no_improve >= cfg["stagnation_patience"]:
            break
```

---

## 11. I/O Utilities (`ga/io_utils.py`)

- **CSV parsing/serialization** for `Individual` ↔ CSV.
- Generation folders creation: `ga/gen_{gen:03d}/`.
- Deterministic naming: `ind_{idx:03d}.csv`.
- Optional sidecar YAML/JSON for provenance.

---

## 12. Logging & Reproducibility (`ga/logging_utils.py`)

- **Fitness logs** per generation: CSV with columns
  ```
gen,ind_id,path,fitness,S_quotas,S_uniform_y,S_uniform_x,S_separation,S_feasibility,notes
  ```
- **Hall of Fame**: maintain `best/hall_of_fame.csv` with top‑N individuals overall.
- Seed all random sources (`random`, `numpy.random`). Record seeds used.

---

## 13. Diversity (Optional) (`ga/diversity.py`)

- Define an occupancy vector over `(x,y)` or over `(entity_type, band)`.
- **Hamming distance** or Jaccard distance between individuals.
- Add a small diversity bonus to fitness for individuals far from current elite.

---

## 14. Integrating with `run_placement.py` (Immigrants)

Provide a small helper:
```python
def immigrants_from_run_placement(cfg, output_root, rng) -> list[Individual]:
    # Call run_placement.py with --output-name pointing to ga/gen_{gen}/imm_{k}
    # Parse CSVs into Individuals and return
```
Configure `immigrants.run_placement_args` if you need flags like `--detailed`.

---

## 15. Tests (Minimal but Targeted)

- **Parsing/serialization**: round‑trip CSV → Individual → CSV.
- **Crossover**: band‑wise recombination preserves band cardinalities before repair.
- **Mutation**: within‑band operators keep entities inside bands; no out‑of‑region cells.
- **Repair**: start from intentionally conflicted child; verify no overlaps and quotas satisfied.
- **Fitness**: components in [0,1]; weight sum = 1; deterministic under fixed seed.

Add a `run_ga_tests.py` that exercises these with small toy grids.

---

## 16. Performance & Parallelism

- Evaluation is embarrassingly parallel: use `multiprocessing` for `score_all`.
- Keep repair iterations small (e.g., 10–20). Limit mutation moves per gene.
- Cache per‑entity/band indices and neighbor lists to avoid recomputation.

---

## 17. Invariants & Edge Cases

- **Invariants**:
  - After **repair**, every individual must: (1) have unique `(x,y)` per cell, (2) respect allowed regions, (3) meet quotas or record controlled borrow, (4) store final metrics.
- **Edge cases**:
  - If crossover yields infeasible child that repair cannot fix within limits, **fallback** to best parent or rerun mutation.
  - If a band is completely blocked, allow **symmetric radius reduction** locally and record in notes (also penalize slightly via feasibility).

---

## 18. Example Run (End‑to‑End)

```bash
# 1) Initialize population with 80 random CSVs using your engine
python3 run_placement.py --trials 80 --output-name "ga/gen_000/ind"

# 2) Run GA for up to 80 generations
python3 -m ga.driver --config ga/ga_config.yaml --output-root ga/

# 3) Inspect logs and best solutions
cat ga/logs/fitness_gen_000.csv | column -t -s,
cat ga/best/hall_of_fame.csv | column -t -s,
```



### TL;DR
Create a `/ga` package with clear modules for **fitness**, **selection**, **crossover**, **mutation**, and **repair**; orchestrate with `driver.py`. Use the existing metrics and a short Phase‑C “repair & refine” to keep children valid and well‑separated. Log everything, seed randomness, and iterate with elitism and immigrants. This integrates cleanly with your CSV‑based pipeline and preserves the stratified placement philosophy throughout evolution.

