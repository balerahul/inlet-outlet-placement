# GA Extension - Genetic Algorithm for Placement Optimization

A band-aware genetic algorithm extension that evolves existing placement layouts through crossover, mutation, and repair operations with **external fitness evaluation**.

## 🎯 Overview

The GA extension provides tools to:
- **Generate variants**: Create mutated versions of a single parent layout
- **Generate offspring**: Combine multiple parent layouts via crossover and mutation
- **Inject immigrants**: Add fresh random layouts for diversity
- **Track lineage**: Full provenance from parents to children

**Key Features**:
- ✅ **Non-invasive**: Zero modifications to existing `src/` code
- ✅ **External fitness**: You evaluate layouts, GA generates new ones
- ✅ **Band-aware**: All operations respect stratified structure
- ✅ **YAML-based**: Simple configuration, minimal CLI arguments

## 📦 Installation

No additional dependencies beyond the main project. Just ensure you have:
- Python 3.7+
- `matplotlib` and `PyYAML` (already required by main project)

## 🚀 Quick Start

### Step 1: Generate an Initial Layout

First, create a placement layout using the main system:

```bash
python3 main.py
```

This creates `output/placement_final.csv`. This will be your starting parent.

### Step 2: Create a Run Configuration

Create a YAML file (e.g., `my_variant_run.yaml`) to configure the GA:

```yaml
# Variant Mode: Generate mutated versions of a single parent
mode: variant

input:
  parent: output/placement_final.csv

output:
  root: ga_output/variants
  overwrite: true  # Set to false to prevent overwriting existing files

ga_config: ga_ext/ga_ext_config.yaml
placement_config: config.yaml

generation:
  variants: 10  # Generate 10 mutated variants
```

### Step 3: Run the GA

```bash
python3 ga_cli.py my_variant_run.yaml
```

**Output**:
```
=== GA Extension: Variant Mode ===
Parent: output/placement_final.csv
Output: ga_output/variants
Variants: 10

Generated 10/10 variants
Lineage log: ga_output/variants/lineage.csv

✓ Complete: 10 variants in ga_output/variants/
```

### Step 4: Evaluate Layouts

Use your external evaluator (CFD solver, ML model, etc.) to score each variant:

```bash
# Your evaluation code here
# Score each: ga_output/variants/variant_000.csv, variant_001.csv, ...
```

### Step 5: Create Parent Manifest

Select the best layouts and create a parent manifest (`parents.csv`):

```csv
csv_path,score,weight
ga_output/variants/variant_003.csv,0.89,1.0
ga_output/variants/variant_007.csv,0.92,2.0
output/placement_final.csv,0.85,1.0
```

- **csv_path**: Path to parent layout
- **score**: Fitness score (optional, for your reference)
- **weight**: Selection probability (higher = more likely to be chosen)

### Step 6: Generate Offspring

Create an offspring configuration (`my_offspring_run.yaml`):

```yaml
mode: offspring

input:
  # Option 1: Parent manifest file
  parents_manifest: parents.csv

  # Option 2: Directory containing parent CSVs (all used with equal weight)
  # parents_dir: ga_output/generation_001/

output:
  root: ga_output/generation_002
  overwrite: true

ga_config: ga_ext/ga_ext_config.yaml
placement_config: config.yaml

generation:
  children: 20       # Generate 20 children via crossover + mutation
  immigrants: 5      # Add 5 fresh random layouts for diversity
```

Run it:

```bash
python3 ga_cli.py my_offspring_run.yaml
```

**Output**:
```
=== GA Extension: Offspring Mode ===
Parents: 3 loaded from parents.csv
Output: ga_output/generation_002
Children: 20 | Immigrants: 5

Generated 10/20 children
Generated 20/20 children
Generated 5 immigrants

✓ Complete: 25 layouts in ga_output/generation_002/
  - 20 children (child_000.csv - child_019.csv)
  - 5 immigrants (immigrant_000.csv - immigrant_004.csv)
  - Lineage log: ga_output/generation_002/lineage.csv
```

### Step 7: Repeat

Continue the cycle:
1. Evaluate all layouts in generation_002
2. Select best performers
3. Create new parent manifest
4. Generate generation_003
5. ...

## 📋 Configuration Reference

### Run Configuration (YAML)

**Common Fields**:

```yaml
mode: variant  # or 'offspring'

output:
  root: path/to/output           # Where to save results
  overwrite: false               # Allow overwriting existing files

ga_config: ga_ext/ga_ext_config.yaml  # Path to GA parameters
placement_config: config.yaml         # Path to placement parameters (optional)
```

**Variant Mode**:

```yaml
mode: variant

input:
  parent: path/to/parent.csv  # Single parent layout

generation:
  variants: 10  # Number of variants to generate
```

**Offspring Mode**:

```yaml
mode: offspring

input:
  # Choose ONE:
  parents_manifest: parents.csv     # CSV with paths, scores, weights
  # OR
  parents_dir: path/to/parents/     # Directory of CSVs (equal weights)

generation:
  children: 20                  # Children via crossover + mutation
  immigrants: 5                 # Fresh random layouts (optional)
```

### GA Configuration (ga_ext_config.yaml)

Located at `ga_ext/ga_ext_config.yaml`, this file controls genetic operators:

```yaml
placement_config_path: config.yaml  # Main placement configuration

crossover:
  strategy: bandwise  # 'bandwise', 'block_2d', 'entity_wise', or 'region_aware'

  # For block_2d mode:
  block_2d_num_vertical_splits: 2    # Divide grid into 2x2 blocks
  block_2d_num_horizontal_splits: 2

  # For region_aware mode:
  region_aware:
    blocks_per_region_x: 2    # Divide each allowed region into 2x2 blocks
    blocks_per_region_y: 2

mutation:
  # Probability of applying each mutation type
  swap_prob: 0.3      # Within-band position swap (conservative)
  jitter_prob: 0.4    # Small position nudge (balanced)
  reseed_prob: 0.2    # Re-place entities randomly (aggressive)

  jitter_radius: 3    # Max distance for jitter moves (in grid cells)
  reseed_fraction: 0.1  # Fraction of entities to reseed (10%)

repair:
  max_separation_iterations: 20  # Iterations for separation refinement
  random_seed: 42                # For reproducibility (null = random)
```

**Crossover Strategies**:
- **bandwise**: Safest. Inherit each (entity, band) from one parent.
- **block_2d**: Exploratory. Divide grid into blocks, inherit independently.
- **entity_wise**: Aggressive. Inherit entire entity types from one parent.
- **region_aware**: Smart. Block crossover within each allowed region independently (guarantees zero region violations).

**Why Region-Aware Crossover?**

When entity types have disjoint allowed regions (e.g., supply inlets in y=3-6, exhaust outlets in y=1-2,7-8), standard block_2d crossover can violate region constraints by inheriting entities from the wrong region. Region-aware crossover solves this by:

1. **Grouping entities by allowed region**: Identifies which entity types share the same allowed region
2. **Independent block crossover per region**: Applies block-based inheritance within each region separately
3. **Guaranteed constraint satisfaction**: Entities can never leave their allowed region (zero violations by construction)
4. **Reduced repair overhead**: No region-based repairs needed, only separation refinement
5. **Preserves spatial patterns**: Maintains useful 2D patterns within each region

**When to use region_aware**:
- ✅ Entity types have disjoint or non-overlapping allowed regions
- ✅ Supply/exhaust separation is critical to preserve
- ✅ Want exploratory crossover without region violations
- ❌ Not needed if all entities share the same allowed region (use block_2d instead)

**Mutation Operators**:
- **swap**: Swap two entities in same band (safe, local optimization)
- **jitter**: Move entity to nearby free cell (balanced exploration)
- **reseed**: Re-place random fraction of entities (aggressive, escapes local optima)

## 📂 Output Structure

### Variant Mode

```
ga_output/variants/
├── variant_000.csv
├── variant_001.csv
├── ...
├── variant_009.csv
└── lineage.csv
```

### Offspring Mode

```
ga_output/generation_002/
├── child_000.csv
├── child_001.csv
├── ...
├── child_019.csv
├── immigrant_000.csv
├── ...
├── immigrant_004.csv
└── lineage.csv
```

### Lineage Log Format

`lineage.csv` tracks full provenance:

```csv
child_id,child_path,parent1_path,parent2_path,crossover_op,mutation_ops,repair_notes,generation
variant_000,ga_output/variants/variant_000.csv,output/placement_final.csv,,,swap|jitter,No repairs needed,0
child_000,ga_output/gen_002/child_000.csv,parent1.csv,parent2.csv,bandwise,jitter,Relocated 2 entities,1
```

**Fields**:
- **child_id**: Unique identifier
- **child_path**: Output file path
- **parent1_path, parent2_path**: Parent layouts (parent2 empty for variants)
- **crossover_op**: Strategy used (bandwise/block_2d/entity_wise)
- **mutation_ops**: Applied mutations (e.g., "swap|jitter")
- **repair_notes**: Summary of repairs performed
- **generation**: Generation number (0-indexed)

## 🔧 Advanced Usage

### Custom Grid Configuration

To use a different grid setup, modify `config.yaml` and reference it in `ga_ext_config.yaml`:

```yaml
# ga_ext_config.yaml
placement_config_path: custom_config.yaml
```

### Weighted Parent Selection

When using `parent_selection: weighted`, parents with higher weights are more likely to be selected:

```csv
csv_path,score,weight
parent1.csv,0.85,1.0
parent2.csv,0.92,3.0  # 3x more likely to be selected
parent3.csv,0.78,0.5
```

### Controlling Randomness

For reproducible results, set `random_seed` in `ga_ext_config.yaml`:

```yaml
repair:
  random_seed: 42  # Same results every run
```

For different results each time:

```yaml
repair:
  random_seed: null  # Random seed each run
```

### Multi-Generation Evolution Loop

Example script for automated evolution:

```python
import subprocess
import csv

def evaluate_layout(csv_path):
    """Your evaluation function here."""
    # Run CFD simulation, ML model, etc.
    return score

def create_parent_manifest(layouts_with_scores, output_path):
    """Select top performers and create manifest."""
    top_layouts = sorted(layouts_with_scores, key=lambda x: x[1], reverse=True)[:5]

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['csv_path', 'score', 'weight'])
        for path, score in top_layouts:
            writer.writerow([path, score, 1.0])

# Multi-generation loop
for gen in range(10):
    # Generate offspring
    subprocess.run(['python3', 'ga_cli.py', f'gen_{gen}_config.yaml'])

    # Evaluate all layouts
    layouts = glob.glob(f'ga_output/gen_{gen+1}/*.csv')
    scored = [(path, evaluate_layout(path)) for path in layouts]

    # Select best for next generation
    create_parent_manifest(scored, f'parents_gen_{gen+1}.csv')

    print(f"Generation {gen+1}: Best score = {max(s for _, s in scored):.3f}")
```

## 🐛 Troubleshooting

### "Output file already exists"

Set `overwrite: true` in your run configuration:

```yaml
output:
  overwrite: true
```

### "No free cells available for relocation"

Your grid is too dense. Either:
- Reduce entity counts in `config.yaml`
- Increase grid size
- Adjust allowed regions

### "Repair failed: quota violations persist"

The repair system tried but couldn't balance quotas. Check:
- Band configuration (too few bands?)
- Allowed regions (too restrictive?)
- Entity counts (too high for grid size?)

### "Invalid YAML configuration"

Ensure all required fields are present:

**Variant mode**: `mode`, `input.parent_csv`, `output.output_root`, `generation.num_variants`

**Offspring mode**: `mode`, `input.parents_manifest` OR `input.parents_dir`, `output.output_root`, `generation.num_children`

### Mutation has no effect

Increase mutation probabilities in `ga_ext_config.yaml`:

```yaml
mutation:
  swap_prob: 0.5
  jitter_prob: 0.6
  reseed_prob: 0.3
```

(Probabilities don't need to sum to 1.0; they're independent)

## 📊 Performance Tips

### Faster Generation

- Reduce `max_separation_iterations` (default: 20)
- Use `bandwise` crossover (fastest)
- Reduce number of immigrants

### Better Exploration

- Increase `reseed_prob` and `reseed_fraction`
- Use `block_2d` or `entity_wise` crossover
- Add more immigrants per generation

### Better Exploitation

- Increase `swap_prob` (local optimization)
- Use `bandwise` crossover (preserves structure)
- Reduce mutation probabilities

## 🧪 Testing

Run all unit tests:

```bash
PYTHONPATH=. python3 tests/test_ga_ext/test_io_utils.py
PYTHONPATH=. python3 tests/test_ga_ext/test_operations.py
PYTHONPATH=. python3 tests/test_ga_ext/test_repair.py
```

Expected: **57/57 tests passing** ✅

## 📚 Additional Resources

- **Methodology**: See `docs/methodology_*.md` for algorithm details
- **Implementation Roadmap**: `GA_IMPLEMENTATION_ROADMAP.md`
- **Session Notes**: `SESSION_CHECKPOINT.md`
- **Example Configs**: `examples/variant_run.yaml`, `examples/offspring_run.yaml`

## 🤝 Integration with External Evaluators

The GA extension is designed to work with **any** external evaluator:

1. **Generate layouts**: Use variant or offspring mode
2. **Export layouts**: Already in CSV format
3. **Run evaluator**: Your CFD solver, ML model, simulation, etc.
4. **Create manifest**: List best layouts with scores and weights
5. **Generate next generation**: Feed manifest back to GA

Example evaluator interface:

```python
def evaluate_all_layouts(layout_dir):
    """Evaluate all CSV layouts in directory."""
    results = []
    for csv_file in glob.glob(f"{layout_dir}/*.csv"):
        # Read layout
        layout = pd.read_csv(csv_file)

        # Run your evaluator (CFD, ML, etc.)
        score = run_cfd_simulation(layout)  # Your code here

        results.append((csv_file, score))

    return results
```

## 🎓 Example Workflow

**Goal**: Find optimal ventilation layout for a warehouse

```bash
# 1. Generate initial layout
python3 main.py
# Output: output/placement_final.csv

# 2. Generate 20 variants
cat > explore.yaml <<EOF
mode: variant
input:
  parent: output/placement_final.csv
output:
  root: warehouse/gen_000
  overwrite: true
generation:
  variants: 20
ga_config: ga_ext/ga_ext_config.yaml
EOF

python3 ga_cli.py explore.yaml

# 3. Evaluate all variants (your CFD solver)
python3 my_cfd_evaluator.py warehouse/gen_000/*.csv > scores.txt

# 4. Select top 5, create manifest
python3 create_manifest.py scores.txt > parents.csv

# 5. Generate next generation
cat > evolve.yaml <<EOF
mode: offspring
input:
  parents_manifest: parents.csv
output:
  root: warehouse/gen_001
  overwrite: true
generation:
  children: 30
  immigrants: 5
ga_config: ga_ext/ga_ext_config.yaml
EOF

python3 ga_cli.py evolve.yaml

# 6. Repeat steps 3-5 for generations 2, 3, 4...
```

## ⚙️ Design Philosophy

**External Fitness**: The GA extension does NOT compute fitness scores. You provide pre-selected parents (already scored by your evaluator), and the GA generates new layouts. This design:
- Supports any fitness function (CFD, ML, human judgment, etc.)
- Maintains clean separation of concerns
- Allows flexible evaluation pipelines

**Band-Aware Operations**: All genetic operations respect band boundaries, ensuring:
- Stratification constraints automatically preserved
- Less repair needed
- Higher quality offspring

**Non-Invasive**: Zero modifications to existing `src/` code:
- Existing `main.py` workflow unchanged
- GA is optional add-on
- Reduced risk of breaking validated code

---

## 📞 Support

- **Issues**: Check `SESSION_CHECKPOINT.md` for known issues
- **Algorithm Details**: Read `docs/methodology_*.md`
- **Implementation**: See `GA_IMPLEMENTATION_ROADMAP.md`

**Version**: Phase 4 Complete (67% of roadmap)
**Last Updated**: 2025-10-02
