# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an advanced indoor optimization project implementing a comprehensive **stratified, non-overlapping multi-entity placement system** for rectangular grids. The system optimally places different types of HVAC components (vinlet, voutlet, acinlet, acoutlet) while ensuring proper distribution, spacing, and adherence to the methodology outlined in `placement_plan.md`.

## Core Architecture

The system implements a sophisticated **three-phase stratified placement algorithm**:

### Phase A: Normalize & Partition
- **GridRegion**: Handles coordinate normalization to [0,1]×[0,1] space
- **Stratification**: Creates horizontal bands for quota-based placement
- **Entity**: Defines placement constraints and allowed regions

### Phase B: Initial Per-Entity Placement
- **Band-aware quota system**: Distributes entities proportionally across bands based on available cells
- **Enhanced farthest point sampling**: Maintains separation while respecting band constraints
- **Conflict avoidance**: Tracks occupied cells across all entities

### Phase C: Joint Refinement (Blue-Noise Optimization)
- **BlueNoiseOptimizer**: Iteratively improves separation distances
- **Local optimization**: Performs swaps and nudges within bands
- **Separation enforcement**: Maintains both intra-entity and cross-entity minimum distances

## Key Components

### Core System Files (src/ directory)
- `src/stratified_placement.py`: Main placement engine with three-phase algorithm
- `src/placement_metrics.py`: Comprehensive quality analysis and reporting
- `src/visualization.py`: Advanced multi-panel visualization system
- `src/config_loader.py`: YAML configuration loading and validation
- `src/placement_exporter.py`: Export system for various output formats
- `src/validate_config.py`: Configuration validation utilities
- `config.yaml`: Configuration file for all system parameters

### Main Entry Point
- `main.py`: Primary user interface and command-line entry point

### Examples and Legacy (examples/ directory)
- `examples/generate_random_individual.py`: Original simple implementation
- `examples/example_advanced_placement.py`: Comprehensive demo of new system
- `placement_plan.md`: Detailed methodology documentation

### Testing
- `tests/`: Unit tests for all core components
- `run_tests.py`: Test runner with integration tests

## Development Commands

### **🎯 Primary Entry Points (Recommended)**

```bash
# Main runner script (RECOMMENDED) - Basic placement
python3 main.py

# With detailed quality analysis
python3 main.py --detailed

# With full visualization (may pause for plot display)
python3 main.py --visualize

# Run multiple random trials for comparison
python3 main.py --trials 5

# Use custom configuration file
python3 main.py --config custom.yaml
```

### **📋 Configuration Management**

```bash
# View current configuration
python3 -c "from src.config_loader import print_config_summary; print_config_summary()"

# Validate configuration
python3 -c "from src.validate_config import ConfigValidator; validator = ConfigValidator(); validator.validate_config_file('config.yaml')"
```

### **🔬 Alternative Entry Points**

```bash
# Full demo with comprehensive analysis (may pause for plots)
python3 examples/example_advanced_placement.py

# Quick programmatic usage
python3 -c "
from src.config_loader import create_placement_engine_from_config
engine = create_placement_engine_from_config()
result = engine.place_all_entities()
print('Placed:', sum(len(p) for p in result.placements.values()), 'entities')
"

# Original legacy implementation
python3 examples/generate_random_individual.py
```

### Running Tests
```bash
# Run all tests (unit + integration)
python3 run_tests.py

# Run individual test modules
python3 -m pytest tests/test_stratification.py
python3 -m pytest tests/test_placement_engine.py
```

### Running Original Implementation
```bash
python3 examples/generate_random_individual.py
```

## Dependencies

### Required
- Python 3.7+
- `matplotlib` for visualization
- `PyYAML` for configuration loading

### Installation
```bash
pip3 install matplotlib PyYAML
```

## Configuration System

The system uses YAML configuration for flexible parameter control:

- **Grid dimensions** and band configuration
- **Entity definitions** with counts, radii, and allowed regions  
- **Separation constraints** (intra-entity and cross-entity)
- **Optimization parameters** (iterations, random seed)
- **Visualization settings** and output options

Modify `config.yaml` to adjust placement parameters without code changes.

### **🎲 Randomization and Reproducibility Control**

The system supports flexible randomization control via the `random_seed` parameter:

```yaml
optimization:
  max_iterations: 100
  random_seed: 42        # Fixed seed for reproducible results
  # random_seed: null    # Random seed each run (different results)
  # random_seed: "random" # Same as null - generates random seed
```

**Usage Examples:**
```bash
# Reproducible results (same output every time)
# Set random_seed: 42 in config.yaml
python3 run_placement.py

# Different results each run
# Set random_seed: null in config.yaml  
python3 run_placement.py

# Compare multiple random configurations
python3 run_placement.py --trials 10
```

## Algorithm Features

### Advanced Capabilities
- **Proportional quota distribution**: Bands get quotas based on available cell density
- **Anisotropic distance metrics**: Emphasizes vertical (Y-axis) separation when needed  
- **Comprehensive metrics**: Quality scores, coverage analysis, separation violations
- **Blue-noise optimization**: Iterative improvement of minimum distances
- **Feasibility reporting**: Detailed constraint violation tracking

### Key Improvements Over Original
- Full stratified band-based placement with guaranteed coverage
- Proper separation radius enforcement with conflict resolution
- Configuration-driven approach for easy parameter adjustment
- Comprehensive quality metrics and reporting
- Advanced multi-panel visualization system
- Extensive test coverage with integration validation

## Genetic Algorithm Extension (ga_ext/)

### Overview
**NEW (2025-10-01)**: An optional genetic algorithm extension that evolves existing placement layouts through band-aware crossover and mutation with **external fitness evaluation**.

**Status**: Phases 1-3 complete (50% of roadmap) - Foundation, Operations, and Repair implemented.

### Key Features
- ✅ **Non-invasive**: Zero modifications to existing `src/` code
- ✅ **External fitness**: Accepts pre-selected parents, performs only generation operations
- ✅ **Band-aware**: All operations respect stratified structure and quotas
- ✅ **Opt-in**: Separate CLI tool, existing `main.py` behavior unchanged
- ✅ **Repair & Refinement**: Resolves conflicts, balances quotas, improves separation

### Directory Structure
```
ga_ext/
  __init__.py              # Package initialization
  ga_ext_config.yaml       # GA configuration
  data_models.py           # Individual, ParentManifest, LineageRecord
  io_utils.py              # CSV I/O, manifest parsing
  band_utils.py            # Band partitioning utilities
  crossover.py             # 3 crossover strategies
  mutation.py              # 3 mutation operators
  engine_interface.py      # ✅ Non-invasive wrapper for PlacementEngine
  repair.py                # ✅ Conflict resolution, quota adjustment, separation refinement
  [TODO] cli.py

tests/test_ga_ext/
  test_io_utils.py         # 18 tests (all passing)
  test_operations.py       # 14 tests (all passing)
  test_repair.py           # 25 tests (all passing) ✅ NEW

docs/
  methodology_band_aware_partitioning.md
  methodology_crossover_operators.md
  methodology_mutation_operators.md
```

### Running GA Extension Tests
```bash
# From project root
PYTHONPATH=. python3 tests/test_ga_ext/test_io_utils.py
PYTHONPATH=. python3 tests/test_ga_ext/test_operations.py
```

### Implemented Features (Phases 1-2)

**Crossover Strategies**:
- Bandwise: Inherit (entity, band) units from parents (safest)
- Block-2D: Inherit spatial blocks independently (exploratory)
- Entity-wise: Inherit entire entity types (most aggressive)

**Mutation Operators**:
- Within-band swap: Exchange positions in same band (conservative)
- Band-local jitter: Move to nearby free cell (balanced)
- Micro-reseed: Re-place fraction randomly (disruptive)

### Remaining Work (Phases 3-6)
See `SESSION_CHECKPOINT.md` and `GA_IMPLEMENTATION_ROADMAP.md` for:
- Phase 3: Repair & Refinement (conflict resolution, quota adjustment)
- Phase 4: CLI & Orchestration (variant/offspring modes)
- Phase 5: Validation & Testing (edge cases, integration)
- Phase 6: Documentation & Examples (user guide, workflows)

### Quick References
- **Implementation Plan**: `GA_IMPLEMENTATION_ROADMAP.md`
- **Current Status**: `SESSION_CHECKPOINT.md`
- **Original Design**: `ga_integration_plan_for_stratified_placement_system_implementation_guide.md`
- **Methodology Docs**: `docs/methodology_*.md`

---

## Quality Metrics

The system provides detailed analysis including:
- **Overall quality score** (0-1, higher is better)
- **Quota satisfaction rates** per entity and band
- **Coverage metrics** (band/row occupation rates)
- **Separation analysis** (violations, minimum distances)
- **Distribution uniformity** (histogram analysis)

## Usage Patterns

1. **Default usage**: Use `config.yaml` with `example_advanced_placement.py`
2. **Custom scenarios**: Modify configuration file parameters
3. **Programmatic**: Import modules and create custom `PlacementEngine`
4. **Analysis**: Use `PlacementMetrics` for detailed quality assessment
5. **Visualization**: Use `PlacementVisualizer` for comprehensive plots