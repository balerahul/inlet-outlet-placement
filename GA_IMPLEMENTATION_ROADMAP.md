# GA Implementation Roadmap for Stratified Placement System

> **Last Updated**: 2025-10-01
> **Based On**: `ga_integration_plan_for_stratified_placement_system_implementation_guide.md`
> **Implementation Mode**: External Fitness, Non-Intrusive

---

## Executive Summary

This roadmap implements a **genetic algorithm (GA)** extension that evolves existing CSV placement layouts through band-aware crossover and mutation, with external fitness evaluation. The implementation is **non-intrusive** (no changes to existing code), **opt-in** (separate CLI tool), and **external-fitness driven** (no internal selection/scoring).

### Key Principles
1. **External Fitness**: GA accepts pre-selected fit parents, performs only generation operations
2. **Non-Intrusive**: Zero changes to existing `src/` modules or `main.py`
3. **On-Demand**: Only runs when user explicitly invokes the new tool
4. **Band-Aware**: All operations respect stratified band structure and quotas

---

## Implementation Phases

### Phase 1: Foundation & Structure (Days 1-2)
**Goal**: Set up directory structure, configuration system, and I/O utilities

#### 1.1 Directory Structure
```
/ga_ext/
  __init__.py
  ga_ext_config.yaml        # External-fitness GA parameters
  io_utils.py               # CSV I/O, manifest handling, lineage logs
  data_models.py            # Individual, ParentManifest, LineageRecord classes
  cli.py                    # Main CLI entry point (evolve_from_layouts)
```

#### 1.2 Configuration Schema (`ga_ext_config.yaml`)
```yaml
# Generation parameters
crossover_rate: 0.7           # Probability of crossover vs. direct copy
mutation_rate: 0.3            # Per-individual mutation probability
repair_max_iters: 20          # Max iterations for repair/refinement

# Anisotropic distance weight (from existing config)
wy: 2.0                       # Y-axis weight for separation

# Diversity maintenance
immigrants: 2                 # Fresh random layouts per generation

# Reproducibility
random_seed: null             # null = random each run, int = fixed seed

# Default output
output_root: "ga_ext"         # Root folder for generations
```

#### 1.3 Data Models (`ga_ext/data_models.py`)
```python
@dataclass
class Individual:
    """Represents a single placement layout."""
    id: str                           # Unique identifier
    path: Path                        # CSV file path
    placements: dict[str, list]       # {entity_type: [(x,y), ...]}
    metadata: dict                    # repair_notes, lineage, etc.
    external_score: Optional[float]   # If provided by external evaluator

@dataclass
class ParentManifest:
    """External evaluator's parent selection."""
    parents: list[Individual]
    metadata: dict                    # Optional scores, weights, tags

@dataclass
class LineageRecord:
    """Tracks provenance of generated children."""
    child_path: Path
    parent_ids: list[str]
    mode: str                         # "variant" or "offspring"
    crossover_mask: Optional[dict]    # Band-wise parent selection
    mutation_ops: list[str]           # Operations applied
    repair_notes: str                 # Conflicts resolved, quota adjustments
    seed: int                         # Random seed used
```

#### 1.4 I/O Utilities (`ga_ext/io_utils.py`)
- `load_csv_to_individual(path: Path) -> Individual`
- `save_individual_to_csv(ind: Individual, path: Path)`
- `load_parent_manifest(path: Path) -> ParentManifest`
- `save_lineage_log(records: list[LineageRecord], path: Path)`
- `create_generation_folder(root: Path, gen: int) -> Path`

**Deliverables**:
- ✅ Directory structure created
- ✅ Configuration file with documented parameters
- ✅ Data models with type hints
- ✅ I/O utilities with CSV round-trip tests

---

### Phase 2: Band-Aware Operations (Days 3-5)
**Goal**: Implement crossover and mutation that respect band structure

#### 2.1 Band Utilities (`ga_ext/band_utils.py`)
Extract band information from existing placement without modifying source:
```python
def partition_by_band(individual: Individual, config) -> dict:
    """
    Returns: {
        (entity_type, band_id): [(x, y), ...],
        ...
    }
    """
    # Import band calculation from existing config_loader
    # Use grid dimensions and num_bands from config

def get_band_quotas(individual: Individual, config) -> dict:
    """
    Returns: {
        (entity_type, band_id): expected_count,
        ...
    }
    """
    # Calculate quotas using existing logic (non-invasive import)
```

#### 2.2 Crossover (`ga_ext/crossover.py`)

##### Band-Wise Crossover (Primary Strategy)
```python
def bandwise_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: dict,
    rng: np.random.Generator
) -> Individual:
    """
    Combines parents band-by-band, respecting stratification.

    Algorithm:
    1. Partition each parent by (entity_type, band_id)
    2. For each band-entity combination:
       - Flip coin based on crossover_rate
       - Inherit entire band from selected parent
    3. Combine into provisional child
    4. Return child (may have conflicts → send to repair)

    Returns:
        Provisional child (not yet validated)
    """
```

##### Optional: 2D Block Crossover
```python
def block_2d_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: dict,
    rng: np.random.Generator,
    blocks_x: int = 4,
    blocks_y: int = 4
) -> Individual:
    """
    Partitions grid into rectangular blocks, inherits per block.
    Less band-aware, more spatial diversity.
    """
```

**Configuration Choice**:
```yaml
crossover_strategy: "bandwise"  # or "block_2d"
```

#### 2.3 Mutation (`ga_ext/mutation.py`)

##### Mutation Operators (Band-Respecting)
```python
def within_band_swap(
    individual: Individual,
    entity_type: str,
    config: dict,
    rng: np.random.Generator
) -> Individual:
    """
    Swaps positions of two placements of same entity within same band.
    Only accepts swap if it improves minimum distance.
    """

def band_local_jitter(
    individual: Individual,
    entity_type: str,
    config: dict,
    rng: np.random.Generator
) -> Individual:
    """
    Moves one placement to nearby free cell in same band.
    Respects allowed regions and improves separation.
    """

def micro_reseed(
    individual: Individual,
    entity_type: str,
    fraction: float,
    config: dict,
    rng: np.random.Generator
) -> Individual:
    """
    Drops and re-places a small fraction (5-10%) of entities
    within their original bands using existing Phase-B logic.
    """
```

##### Mutation Orchestrator
```python
def mutate(
    individual: Individual,
    config: dict,
    rng: np.random.Generator
) -> Individual:
    """
    Applies mutation operators with probabilities from config.

    Strategy:
    - mutation_rate controls per-individual probability
    - Each operator has sub-probability (e.g., 40% swap, 40% jitter, 20% reseed)
    - Randomly select 1-2 entity types to mutate
    - Apply 1-3 operations total (bounded)
    """
```

**Configuration**:
```yaml
mutation:
  rate: 0.3                    # Per-individual mutation probability
  operators:
    within_band_swap: 0.4
    band_local_jitter: 0.4
    micro_reseed: 0.2
  max_ops_per_individual: 3
  micro_reseed_fraction: 0.1   # 10% of entities
```

**Deliverables**:
- ✅ Band partitioning utilities with tests
- ✅ Bandwise crossover with mask logging
- ✅ Three mutation operators with band validation
- ✅ Mutation orchestrator with configurable probabilities

---

### Phase 3: Repair & Refinement (Days 6-8)
**Goal**: Validate and improve children using existing engine helpers

#### 3.1 Engine Interface Extraction (`ga_ext/engine_interface.py`)
Non-invasive wrapper around existing functionality:
```python
class EngineInterface:
    """
    Exposes existing placement engine capabilities without modification.
    Imports but does not modify src/ modules.
    """

    def __init__(self, config):
        from src.config_loader import create_placement_engine_from_config
        self.engine = create_placement_engine_from_config(config_path=config)

    def check_conflicts(self, placements: dict) -> list[tuple]:
        """Returns list of (x, y) cells with multiple entities."""

    def validate_allowed_regions(self, placements: dict) -> dict:
        """Returns violations: {entity_type: [out-of-region positions]}"""

    def calculate_min_distances(self, placements: dict) -> dict:
        """Returns min distance per entity type (anisotropic)."""

    def suggest_relocation(
        self,
        entity_type: str,
        current_pos: tuple,
        band_id: int,
        occupied: set
    ) -> Optional[tuple]:
        """
        Suggests best free cell in band for relocation.
        Uses existing farthest-point logic.
        """
```

#### 3.2 Repair Pipeline (`ga_ext/repair.py`)

##### Conflict Resolution
```python
def repair_conflicts(
    individual: Individual,
    config: dict,
    engine: EngineInterface,
    rng: np.random.Generator
) -> tuple[Individual, list[str]]:
    """
    Resolves cell conflicts (multiple entities at same position).

    Algorithm:
    1. Identify conflicting cells
    2. For each conflict:
       a. Keep one entity (random or priority-based)
       b. Relocate others to best free cell in same band
       c. Use engine.suggest_relocation() for smart placement
    3. Track all relocations in notes

    Returns:
        (repaired_individual, notes_list)
    """
```

##### Quota Adjustment
```python
def repair_quotas(
    individual: Individual,
    config: dict,
    engine: EngineInterface,
    rng: np.random.Generator
) -> tuple[Individual, list[str]]:
    """
    Adjusts placements to meet per-band quotas.

    Algorithm:
    1. Calculate quota surplus/deficit per (entity, band)
    2. Move surplus entities to adjacent underfull bands
    3. If impossible, record "quota_borrow" in notes
    4. Penalize minimally (external evaluator will judge)

    Returns:
        (repaired_individual, notes_list)
    """
```

##### Separation Refinement (Phase-C Lite)
```python
def refine_separation(
    individual: Individual,
    config: dict,
    engine: EngineInterface,
    max_iters: int = 20
) -> tuple[Individual, list[str]]:
    """
    Iteratively improves worst-case minimum distances.

    Algorithm:
    1. Identify entity with worst minimum distance
    2. Attempt local swaps/nudges within band
    3. Accept if improves global min distance (lexicographic maximin)
    4. Repeat for max_iters or until no improvement
    5. Respect band boundaries and allowed regions

    Returns:
        (refined_individual, notes_list)
    """
```

##### Master Repair Function
```python
def repair_and_refine(
    individual: Individual,
    config: dict,
    engine: EngineInterface,
    rng: np.random.Generator
) -> Individual:
    """
    Complete repair pipeline.

    Steps:
    1. Resolve conflicts
    2. Adjust quotas
    3. Refine separation
    4. Validate (no overlaps, regions respected)
    5. Attach all notes to individual.metadata['repair_notes']

    Invariant: Output always valid (or fails with clear error)
    """
```

**Deliverables**:
- ✅ Engine interface with non-invasive imports
- ✅ Conflict resolution with relocation tracking
- ✅ Quota repair with borrow logging
- ✅ Separation refinement (limited iterations)
- ✅ Integration tests with intentionally broken children

---

### Phase 4: CLI & Orchestration (Days 9-11)
**Goal**: Create user-facing tool with two modes (variant/offspring)

#### 4.1 CLI Interface (Minimal YAML-Based Design)

**Architecture**: Consistent with existing `main.py` pattern - all parameters in YAML configuration files.

**File Structure**:
```
ga_cli.py                       # Root-level CLI entry point (~20 lines)
ga_ext/
  cli.py                        # CLI logic & run config loading
  orchestration.py              # Variant/offspring mode implementations
```

**Usage** (Minimal CLI):
```bash
# Only argument: run configuration file
python3 ga_cli.py variant_run.yaml
python3 ga_cli.py offspring_run.yaml

# Optional explicit flag
python3 ga_cli.py --config variant_run.yaml
```

##### Run Configuration Files

**Variant Mode** (`variant_run.yaml`):
```yaml
# Run configuration for variant mode
mode: "variant"

input:
  parent: "layouts/best_layout.csv"

output:
  root: "ga_ext/variant_001"
  overwrite: false

generation:
  variants: 20

# References to system configs
placement_config: "config.yaml"        # Grid, entities, bands
ga_config: "ga_ext/ga_ext_config.yaml" # Mutation, crossover params

# Optional overrides
random_seed: null  # null = random, int = fixed seed
```

**Offspring Mode** (`offspring_run.yaml`):
```yaml
# Run configuration for offspring mode
mode: "offspring"

input:
  # Option 1: Manifest with scores/weights
  parents_manifest: "ga_ext/gen_000/selected_parents.csv"

  # Option 2: All CSVs from directory (uncomment to use)
  # parents_dir: "ga_ext/gen_000"

output:
  root: "ga_ext/gen_001"
  overwrite: false

generation:
  children: 30
  immigrants: 5

# References to system configs
placement_config: "config.yaml"
ga_config: "ga_ext/ga_ext_config.yaml"

random_seed: 42
```

##### CLI Implementation

**`ga_cli.py`** (Root entry point):
```python
#!/usr/bin/env python3
"""
GA Evolution CLI - Minimal entry point.

Usage:
    python3 ga_cli.py run_config.yaml
    python3 ga_cli.py --config run_config.yaml
"""

import sys
from ga_ext.cli import run_from_config

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 1)

    config_path = sys.argv[1]
    if config_path.startswith('--config='):
        config_path = config_path.split('=')[1]
    elif config_path == '--config':
        config_path = sys.argv[2]

    run_from_config(config_path)
```

**`ga_ext/cli.py`** (Main logic):
```python
def load_run_config(config_path: str) -> dict:
    """Load and validate run configuration."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate required fields
    required_fields = ['mode', 'input', 'output', 'generation']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    return config

def run_from_config(config_path: str):
    """Load run config and execute appropriate mode."""
    config = load_run_config(config_path)

    mode = config['mode']

    if mode == 'variant':
        from .orchestration import run_variant_mode
        run_variant_mode(config)
    elif mode == 'offspring':
        from .orchestration import run_offspring_mode
        run_offspring_mode(config)
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'variant' or 'offspring'")
```

**Benefits**:
- ✅ Minimal CLI (just pass config file)
- ✅ Reproducible (config files are self-documenting)
- ✅ Versionable (commit run configs to git)
- ✅ Consistent with existing `main.py` + `config.yaml` pattern
- ✅ Batch-friendly (easy to run multiple configurations)

#### 4.2 Orchestration Logic (`ga_ext/orchestration.py`)

##### Variant Mode
```python
def run_variant_mode(run_config: dict):
    """
    Generate mutated variants from single parent.

    Args:
        run_config: Run configuration dict from YAML

    Algorithm:
    1. Load GA config and placement config (from run_config references)
    2. Setup RNG (use run_config['random_seed'] or ga_config seed)
    3. Load parent CSV from run_config['input']['parent']
    4. Create output directory: run_config['output']['root']
    5. For i in range(run_config['generation']['variants']):
       a. Copy parent
       b. Apply mutation (no crossover)
       c. Repair & refine
       d. Save to output_root/variant_{i:03d}.csv
       e. Create LineageRecord
    6. Save lineage log to output_root/lineage_log.csv
    7. Print summary report

    Returns:
        None (writes to disk)
    """
    # Load configs
    ga_config = load_config(run_config.get('ga_config', 'ga_ext/ga_ext_config.yaml'))
    placement_config_path = run_config.get('placement_config', 'config.yaml')

    # Setup RNG
    seed = run_config.get('random_seed', ga_config.get('random_seed'))
    if seed is None:
        seed = np.random.randint(0, 2**31)
    rng = np.random.default_rng(seed)

    # Load parent
    parent_path = run_config['input']['parent']
    parent = load_csv_to_individual(parent_path)

    # Create output directory
    output_root = Path(run_config['output']['root'])
    output_root.mkdir(parents=True, exist_ok=run_config['output'].get('overwrite', False))

    # Generate variants
    num_variants = run_config['generation']['variants']
    children = []
    lineage_records = []

    for i in range(num_variants):
        # Copy and mutate
        child = parent.copy()
        child.id = f"variant_{i:03d}"

        # Apply mutation
        child, mutation_ops = mutate(child, ga_config, grid_config, band_config, rng)

        # Repair & refine
        child = repair_and_refine(child, placement_config_path, ga_config, rng)

        # Save
        child_path = output_root / f"variant_{i:03d}.csv"
        save_individual_to_csv(child, child_path)

        # Record lineage
        lineage_records.append(
            LineageRecord(
                child_path=child_path,
                parent_ids=[parent.id],
                mode='variant',
                crossover_mask=None,
                mutation_ops=mutation_ops,
                repair_notes=child.metadata.get('repair_notes', ''),
                seed=seed + i
            )
        )

        children.append(child)

    # Save lineage
    save_lineage_log(lineage_records, output_root / 'lineage_log.csv')

    # Print summary
    print(f"Generated {len(children)} variants in {output_root}")
```

##### Offspring Mode
```python
def run_offspring_mode(run_config: dict):
    """
    Generate children from parent set via crossover + mutation.

    Args:
        run_config: Run configuration dict from YAML

    Algorithm:
    1. Load GA config and placement config
    2. Setup RNG
    3. Load parents (from manifest or directory)
    4. Create output directory
    5. For i in range(run_config['generation']['children']):
       a. Select two parents (uniform random or weighted if manifest provides)
       b. Apply crossover (bandwise or block_2d)
       c. Apply mutation (with probability)
       d. Repair & refine
       e. Save to output_root/child_{i:03d}.csv
       f. Create LineageRecord (parent IDs, crossover mask, mutation ops)
    6. Generate immigrants (if requested):
       a. Use PlacementEngine to generate fresh random layouts
       b. Save as output_root/immigrant_{j:03d}.csv
    7. Save lineage log
    8. Print summary report

    Returns:
        None (writes to disk)
    """
    # Load configs
    ga_config = load_config(run_config.get('ga_config', 'ga_ext/ga_ext_config.yaml'))
    placement_config_path = run_config.get('placement_config', 'config.yaml')

    # Setup RNG
    seed = run_config.get('random_seed', ga_config.get('random_seed'))
    if seed is None:
        seed = np.random.randint(0, 2**31)
    rng = np.random.default_rng(seed)

    # Load parents
    input_config = run_config['input']
    if 'parents_manifest' in input_config:
        parent_manifest = load_parent_manifest(input_config['parents_manifest'])
        parents = parent_manifest.parents
        weights = parent_manifest.get_weights()
    elif 'parents_dir' in input_config:
        parents = load_parents_from_directory(input_config['parents_dir'])
        weights = None
    else:
        raise ValueError("Must specify either 'parents_manifest' or 'parents_dir'")

    # Create output directory
    output_root = Path(run_config['output']['root'])
    output_root.mkdir(parents=True, exist_ok=run_config['output'].get('overwrite', False))

    # Generate children
    num_children = run_config['generation']['children']
    children = []
    lineage_records = []

    for i in range(num_children):
        # Select parents
        parent_a, parent_b = select_two_parents(parents, weights, rng)

        # Crossover
        child, crossover_mask = bandwise_crossover(
            parent_a, parent_b, ga_config, grid_config, band_config, rng
        )
        child.id = f"child_{i:03d}"

        # Mutation (with probability)
        mutation_ops = []
        if rng.random() < ga_config.get('mutation_rate', 0.3):
            child, mutation_ops = mutate(child, ga_config, grid_config, band_config, rng)

        # Repair & refine
        child = repair_and_refine(child, placement_config_path, ga_config, rng)

        # Save
        child_path = output_root / f"child_{i:03d}.csv"
        save_individual_to_csv(child, child_path)

        # Record lineage
        lineage_records.append(
            LineageRecord(
                child_path=child_path,
                parent_ids=[parent_a.id, parent_b.id],
                mode='offspring',
                crossover_mask=crossover_mask,
                mutation_ops=mutation_ops,
                repair_notes=child.metadata.get('repair_notes', ''),
                seed=seed + i
            )
        )

        children.append(child)

    # Generate immigrants
    num_immigrants = run_config['generation'].get('immigrants', 0)
    if num_immigrants > 0:
        immigrants = generate_immigrants(
            num_immigrants, placement_config_path, output_root, rng
        )
        lineage_records.extend([
            create_immigrant_record(imm.path, seed + num_children + j)
            for j, imm in enumerate(immigrants)
        ])

    # Save lineage
    save_lineage_log(lineage_records, output_root / 'lineage_log.csv')

    # Print summary
    print(f"Generated {num_children} children + {num_immigrants} immigrants in {output_root}")
```

##### Helper Functions

```python
def select_two_parents(
    parents: list[Individual],
    weights: Optional[list[float]],
    rng: np.random.Generator
) -> tuple[Individual, Individual]:
    """
    Select two distinct parents for crossover.

    Uses weighted sampling if weights provided, else uniform random.
    """
    if weights:
        # Weighted random selection
        idx_a = rng.choice(len(parents), p=weights/np.sum(weights))
        # Ensure different parent for idx_b
        remaining_indices = [i for i in range(len(parents)) if i != idx_a]
        remaining_weights = [weights[i] for i in remaining_indices]
        idx_b = remaining_indices[
            rng.choice(len(remaining_indices), p=remaining_weights/np.sum(remaining_weights))
        ]
    else:
        # Uniform random selection (without replacement)
        idx_a, idx_b = rng.choice(len(parents), size=2, replace=False)

    return parents[idx_a], parents[idx_b]


def generate_immigrants(
    num_immigrants: int,
    config_path: str,
    output_root: Path,
    rng: np.random.Generator
) -> list[Individual]:
    """
    Generate fresh random layouts using existing placement engine.

    Implementation:
    - Import from src.config_loader
    - Create PlacementEngine instance for each immigrant (with different seeds)
    - Run placement
    - Save CSVs to output_root/immigrant_{j:03d}.csv
    - Return as Individual objects

    This maintains diversity without external input.
    """
    from src.config_loader import create_placement_engine_from_config

    immigrants = []

    for j in range(num_immigrants):
        # Create engine with unique seed
        seed = int(rng.integers(0, 2**31))
        engine = create_placement_engine_from_config(
            config_path=config_path,
            random_seed=seed
        )

        # Generate placement
        result = engine.place_all_entities()

        # Convert to Individual
        immigrant_path = output_root / f"immigrant_{j:03d}.csv"
        placements_dict = {
            entity_type.value: [(cell.x, cell.y) for cell in cells]
            for entity_type, cells in result.placements.items()
        }

        immigrant = Individual(
            id=f"immigrant_{j:03d}",
            path=immigrant_path,
            placements=placements_dict,
            metadata={'generated_by': 'PlacementEngine', 'seed': seed}
        )

        # Save to CSV
        save_individual_to_csv(immigrant, immigrant_path)
        immigrants.append(immigrant)

    return immigrants
```

**Deliverables**:
- ✅ Root-level `ga_cli.py` script (minimal CLI)
- ✅ `ga_ext/cli.py` (config loading and mode dispatching)
- ✅ `ga_ext/orchestration.py` (variant and offspring mode implementations)
- ✅ YAML run configuration system
- ✅ Variant mode implementation
- ✅ Offspring mode implementation
- ✅ Parent selection (weighted/uniform)
- ✅ Immigrant generation via existing engine
- ✅ Lineage logging with full provenance
- ✅ Example run config files (variant_run.yaml, offspring_run.yaml)

---

### Phase 5: Validation & Testing (Days 12-14)
**Goal**: Comprehensive testing and edge case handling

#### 5.1 Unit Tests (`tests/test_ga_ext/`)

```
tests/test_ga_ext/
  __init__.py
  test_io_utils.py              # CSV round-trip, manifest parsing
  test_band_utils.py            # Band partitioning, quota calculation
  test_crossover.py             # Band-wise recombination correctness
  test_mutation.py              # Operator validity (band preservation)
  test_repair.py                # Conflict resolution, quota adjustment
  test_engine_interface.py      # Non-invasive integration
  test_cli.py                   # End-to-end CLI tests
```

##### Key Test Cases

**Crossover Tests**:
- Band cardinalities preserved before repair
- Crossover mask correctly applied
- Parent IDs logged in lineage

**Mutation Tests**:
- `within_band_swap`: entities stay in same band
- `band_local_jitter`: respects allowed regions
- `micro_reseed`: quota maintained per band

**Repair Tests**:
- Conflict resolution eliminates overlaps
- Quota repair achieves balance or logs borrow
- Separation refinement improves min distance
- Invalid inputs raise clear errors

**Integration Tests**:
- Variant mode produces N valid variants
- Offspring mode handles 2-parent crossover
- Immigrants integrate seamlessly
- Lineage log matches outputs

#### 5.2 Edge Cases & Robustness

**Handling Infeasible Children**:
```python
class RepairFailureException(Exception):
    """Raised when repair cannot produce valid individual within limits."""

def repair_and_refine(individual, config, engine, rng, fallback=True):
    """
    If repair fails after max_iters:
    - If fallback=True: return best parent with warning
    - If fallback=False: raise RepairFailureException
    """
```

**Dense Band Scenarios**:
- If band is fully occupied, allow controlled radius reduction
- Log in repair_notes with penalty indicator
- External evaluator can decide if acceptable

**Missing/Invalid Paths**:
- Validate all parent paths exist before starting
- Fail fast with clear error messages
- Provide example manifest format in error

**Configuration Validation**:
```python
def validate_ga_config(config: dict):
    """
    Checks:
    - crossover_rate in [0, 1]
    - mutation_rate in [0, 1]
    - repair_max_iters > 0
    - wy > 0
    - immigrants >= 0
    """
```

**Deliverables**:
- ✅ 20+ unit tests covering all modules
- ✅ Edge case handling with fallbacks
- ✅ Integration tests (variant & offspring modes)
- ✅ Configuration validation
- ✅ Test coverage > 80%

---

### Phase 6: Documentation & Examples (Days 15-16)
**Goal**: User-facing documentation and example workflows

#### 6.1 User Documentation (`ga_ext/README.md`)

```markdown
# GA Extension for Stratified Placement System

## Overview
Evolves existing CSV placement layouts through genetic operations
while preserving band structure and quotas.

## Modes

### Variant Mode
Generate mutated variants from a single parent layout.

**Use Case**: Explore local variations of a known good layout.

**Example**:
```bash
python3 -m ga_ext.cli \
  --mode variant \
  --parent results/best_layout.csv \
  --variants 20 \
  --output-root ga_ext/variants
```

### Offspring Mode
Generate children from multiple parent layouts via crossover.

**Use Case**: Combine features from multiple good layouts.

**Example**:
```bash
python3 -m ga_ext.cli \
  --mode offspring \
  --parents-dir ga_ext/gen_000 \
  --children 30 \
  --immigrants 5 \
  --output-root ga_ext/gen_001
```

## Parent Manifest Format

Optional CSV for weighted parent selection:

```csv
id,path,score,weight,tags
parent_001,ga_ext/gen_000/ind_001.csv,0.89,1.0,elite
parent_002,ga_ext/gen_000/ind_005.csv,0.85,0.8,diverse
```

- `id`: Unique identifier
- `path`: Path to CSV layout (relative or absolute)
- `score`: External fitness score (logged but not used for selection)
- `weight`: Sampling weight (higher = more likely to be selected as parent)
- `tags`: Optional metadata

## Output Structure

```
ga_ext/
  gen_001/
    child_000.csv
    child_001.csv
    ...
    immigrant_000.csv
    lineage_log.csv
```

## Lineage Log Format

Tracks provenance of all generated children:

```csv
child_path,parent_ids,mode,crossover_mask,mutation_ops,repair_notes,seed
gen_001/child_000.csv,"parent_001,parent_003",offspring,"{(vinlet,0): A, (vinlet,1): B, ...}","within_band_swap(vinlet), band_local_jitter(acinlet)","conflict_resolved: 2, quota_adjusted: 0",12345
```

## Configuration

Edit `ga_ext/ga_ext_config.yaml`:

```yaml
crossover_rate: 0.7       # 70% of offspring from crossover
mutation_rate: 0.3        # 30% chance per individual
repair_max_iters: 20      # Max repair iterations
wy: 2.0                   # Y-axis separation weight
random_seed: null         # Random each run
```

## Integration with External Evaluator

**Handshake Loop**:

1. External evaluator selects fit parents → manifest
2. Run GA to generate children:
   ```bash
   python3 -m ga_ext.cli --mode offspring \
     --parents-manifest selected_parents.csv \
     --children 50 --output-root ga_ext/gen_N
   ```
3. External evaluator scores children
4. Repeat from step 1 with new parent set

## Backward Compatibility

- No changes to existing `src/` modules
- `main.py` behavior unchanged
- GA is **opt-in only** via separate CLI
```

#### 6.2 Example Workflows (`examples/ga_ext_examples/`)

**Example 1: Variant Exploration**
```python
# examples/ga_ext_examples/01_variant_exploration.py
"""
Generate and compare variants of a single good layout.
"""
import subprocess
from pathlib import Path

# Generate initial layout
subprocess.run([
    "python3", "main.py",
    "--output", "ga_ext/initial.csv",
    "--seed", "42"
])

# Create variant run config
with open('variant_run.yaml', 'w') as f:
    f.write("""
mode: variant
input:
  parent: ga_ext/initial.csv
output:
  root: ga_ext/variants
  overwrite: false
generation:
  variants: 50
placement_config: config.yaml
ga_config: ga_ext/ga_ext_config.yaml
random_seed: null
""")

# Generate 50 variants
subprocess.run(["python3", "ga_cli.py", "variant_run.yaml"])

# Analyze variants (external evaluator)
# ... your analysis code here
```

**Example 2: Multi-Generation Evolution**
```python
# examples/ga_ext_examples/02_multi_generation.py
"""
Run multiple generations with external selection.
"""

def external_evaluator(layouts: list[Path]) -> list[Path]:
    """Placeholder for your evaluation logic."""
    # Score layouts, select top 10
    return layouts[:10]  # Simplified

# Generation 0: Random initialization
for i in range(50):
    subprocess.run([
        "python3", "main.py",
        "--output", f"ga_ext/gen_000/ind_{i:03d}.csv",
        "--seed", str(i)
    ])

# Evolve for 10 generations
for gen in range(1, 11):
    # External selection
    parent_paths = external_evaluator(
        list(Path(f"ga_ext/gen_{gen-1:03d}").glob("*.csv"))
    )

    # Create manifest
    create_manifest(parent_paths, f"ga_ext/gen_{gen:03d}/parents.csv")

    # Create offspring run config
    with open(f'offspring_gen_{gen:03d}.yaml', 'w') as f:
        f.write(f"""
mode: offspring
input:
  parents_manifest: ga_ext/gen_{gen:03d}/parents.csv
output:
  root: ga_ext/gen_{gen:03d}
  overwrite: false
generation:
  children: 40
  immigrants: 10
placement_config: config.yaml
ga_config: ga_ext/ga_ext_config.yaml
random_seed: {gen * 1000}
""")

    # Generate offspring
    subprocess.run(["python3", "ga_cli.py", f"offspring_gen_{gen:03d}.yaml"])
```

**Deliverables**:
- ✅ Comprehensive README with examples
- ✅ Two example scripts (variant & multi-gen)
- ✅ Manifest creation helper
- ✅ Configuration guide

---

## Implementation Checklist

### Phase 1: Foundation ✓
- [ ] Create `/ga_ext/` directory structure
- [ ] Write `ga_ext_config.yaml` with all parameters
- [ ] Implement `data_models.py` (Individual, ParentManifest, LineageRecord)
- [ ] Implement `io_utils.py` (CSV I/O, manifest parsing)
- [ ] Write CSV round-trip tests

### Phase 2: Operations ✓
- [ ] Implement `band_utils.py` (partition, quota calculation)
- [ ] Implement `crossover.py` (bandwise_crossover)
- [ ] Implement `mutation.py` (3 operators + orchestrator)
- [ ] Write crossover/mutation unit tests
- [ ] Validate band preservation

### Phase 3: Repair ✓
- [ ] Implement `engine_interface.py` (non-invasive wrapper)
- [ ] Implement `repair.py` (conflicts, quotas, separation)
- [ ] Write repair tests with intentionally broken inputs
- [ ] Validate repair invariants (no overlaps, regions respected)

### Phase 4: CLI ✓
- [ ] Create `ga_cli.py` root-level script (minimal CLI)
- [ ] Implement `ga_ext/cli.py` (YAML config loading and mode dispatching)
- [ ] Implement `ga_ext/orchestration.py` (variant and offspring modes)
- [ ] Create example run config files (variant_run.yaml, offspring_run.yaml)
- [ ] Implement variant mode orchestration
- [ ] Implement offspring mode orchestration
- [ ] Implement parent selection (weighted/uniform)
- [ ] Implement immigrant generation
- [ ] Write lineage logging
- [ ] Test CLI end-to-end with YAML configs

### Phase 5: Testing ✓
- [ ] Write 20+ unit tests
- [ ] Add edge case handling (repair failures, dense bands)
- [ ] Integration tests (both modes)
- [ ] Configuration validation
- [ ] Achieve 80%+ test coverage

### Phase 6: Documentation ✓
- [ ] Write `ga_ext/README.md`
- [ ] Create example workflows
- [ ] Document parent manifest format
- [ ] Document lineage log format
- [ ] Add troubleshooting guide

---

## Success Criteria

### Functional Requirements
1. ✅ Variant mode produces N valid variants from single parent
2. ✅ Offspring mode combines multiple parents via crossover
3. ✅ All outputs respect band structure and quotas
4. ✅ No overlaps or region violations in any output
5. ✅ Lineage fully traceable (parents → operations → children)
6. ✅ Immigrants integrate seamlessly with evolved layouts

### Non-Functional Requirements
1. ✅ Zero modifications to existing `src/` modules
2. ✅ `main.py` behavior unchanged
3. ✅ Reproducible with `random_seed` set
4. ✅ Fails gracefully with clear error messages
5. ✅ Performance: <1 second per child generation (excluding repair)

### Quality Metrics
- Test coverage > 80%
- All edge cases handled with fallbacks
- Clear documentation with examples
- Validated on 3+ real-world configurations

---

## Risk Mitigation

### Risk 1: Repair Failures on Dense Grids
**Mitigation**:
- Allow controlled radius reduction (logged in notes)
- Fallback to best parent if repair fails
- External evaluator can reject if unacceptable

### Risk 2: Crossover Produces Infeasible Children
**Mitigation**:
- Repair pipeline handles conflicts/quota imbalances
- Extensive testing with edge cases
- Max repair iterations configurable

### Risk 3: Immigrants Don't Integrate Well
**Mitigation**:
- Use same engine as existing system
- Same configuration ensures compatibility
- Keep immigrant count low (2-5 per generation)

### Risk 4: External Evaluator Integration Complexity
**Mitigation**:
- Simple file-based interface (CSV in/out)
- Clear manifest format
- Example handshake loop provided

---

## Timeline Estimate

- **Phase 1**: 2 days (foundation)
- **Phase 2**: 3 days (operations)
- **Phase 3**: 3 days (repair)
- **Phase 4**: 3 days (CLI)
- **Phase 5**: 3 days (testing)
- **Phase 6**: 2 days (documentation)

**Total**: ~16 days (2-3 weeks with buffer)

---

## Next Steps

1. **Review this roadmap** with stakeholders
2. **Set up development branch**: `git checkout -b feature/ga-extension`
3. **Start Phase 1**: Create directory structure and configuration
4. **Iterative development**: Complete phases sequentially with testing
5. **Final validation**: Run on real-world configurations
6. **Merge to main**: After all tests pass and documentation complete

---

## References

- Source document: `ga_integration_plan_for_stratified_placement_system_implementation_guide.md`
- Existing system: See `CLAUDE.md` for architecture overview
- Configuration: `config.yaml` for existing parameters
- Placement engine: `src/stratified_placement.py`
