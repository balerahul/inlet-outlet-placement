"""
Orchestration module for GA extension.

Implements variant and offspring mode generation workflows.
"""

from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np
import yaml

from .data_models import Individual, LineageRecord, create_immigrant_record
from .io_utils import (
    load_csv_to_individual,
    save_individual_to_csv,
    load_parent_manifest,
    load_parents_from_directory,
    save_lineage_log
)
from .engine_interface import EngineInterface
from .mutation import mutate
from .crossover import bandwise_crossover
from .repair import repair_and_refine


def run_variant_mode(run_config: Dict) -> None:
    """
    Generate mutated variants from single parent.

    This mode creates N variants of a single parent layout by applying
    mutation operators (no crossover). Each variant is repaired and refined
    before being saved.

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
    print("=" * 70)
    print("VARIANT MODE")
    print("=" * 70)

    # Load GA configuration
    ga_config_path = run_config.get('ga_config', 'ga_ext/ga_ext_config.yaml')
    print(f"Loading GA config from: {ga_config_path}")
    with open(ga_config_path, 'r') as f:
        ga_config = yaml.safe_load(f)

    # Load placement configuration path
    placement_config_path = run_config.get('placement_config', 'config.yaml')
    print(f"Loading placement config from: {placement_config_path}")

    # Create engine interface to get grid/band configs
    engine = EngineInterface(placement_config_path)
    grid_config = engine.get_grid_config()
    band_config = engine.get_band_config()

    # Setup RNG
    seed = run_config.get('random_seed', ga_config.get('random_seed'))
    if seed is None:
        seed = int(np.random.randint(0, 2**31))
    print(f"Random seed: {seed}")
    rng = np.random.default_rng(seed)

    # Load parent
    parent_path = run_config['input']['parent']
    print(f"Loading parent from: {parent_path}")
    parent = load_csv_to_individual(parent_path)
    print(f"Parent ID: {parent.id}")
    print(f"Parent entities: {sum(len(p) for p in parent.placements.values())}")

    # Create output directory
    output_root = Path(run_config['output']['root'])
    overwrite = run_config['output'].get('overwrite', False)

    if output_root.exists() and not overwrite:
        raise FileExistsError(
            f"Output directory already exists: {output_root}\n"
            f"Set 'output.overwrite: true' in config to overwrite"
        )

    output_root.mkdir(parents=True, exist_ok=overwrite)
    print(f"Output directory: {output_root}\n")

    # Generate variants
    num_variants = run_config['generation']['variants']
    print(f"Generating {num_variants} variants from parent {parent.id}...")
    print()

    children = []
    lineage_records = []

    for i in range(num_variants):
        # Copy parent
        child = parent.copy()
        child.id = f"variant_{i:03d}"

        # Apply mutation
        child, mutation_ops = mutate(child, ga_config, grid_config, band_config, rng)

        # Repair & refine
        child = repair_and_refine(child, placement_config_path, ga_config, rng)

        # Save
        child_path = output_root / f"variant_{i:03d}.csv"
        save_individual_to_csv(child, child_path, overwrite=overwrite)

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

        # Progress reporting
        if (i + 1) % 10 == 0 or i == num_variants - 1:
            print(f"  Progress: {i+1}/{num_variants} variants generated")

    # Save lineage
    lineage_log_path = output_root / 'lineage_log.csv'
    save_lineage_log(lineage_records, lineage_log_path)

    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Generated: {len(children)} variants")
    print(f"Output directory: {output_root}")
    print(f"Lineage log: {lineage_log_path}")
    print(f"Files created: {len(list(output_root.glob('*.csv')))}")


def run_offspring_mode(run_config: Dict) -> None:
    """
    Generate children from parent set via crossover + mutation.

    This mode creates children by selecting pairs of parents, applying
    crossover and mutation, then repairing and refining the results.
    Optionally generates fresh random immigrants for diversity.

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
    print("=" * 70)
    print("OFFSPRING MODE")
    print("=" * 70)

    # Load GA configuration
    ga_config_path = run_config.get('ga_config', 'ga_ext/ga_ext_config.yaml')
    print(f"Loading GA config from: {ga_config_path}")
    with open(ga_config_path, 'r') as f:
        ga_config = yaml.safe_load(f)

    # Load placement configuration path
    placement_config_path = run_config.get('placement_config', 'config.yaml')
    print(f"Loading placement config from: {placement_config_path}")

    # Create engine interface to get grid/band configs
    engine = EngineInterface(placement_config_path)
    grid_config = engine.get_grid_config()
    band_config = engine.get_band_config()

    # Setup RNG
    seed = run_config.get('random_seed', ga_config.get('random_seed'))
    if seed is None:
        seed = int(np.random.randint(0, 2**31))
    print(f"Random seed: {seed}")
    rng = np.random.default_rng(seed)

    # Load parents
    input_config = run_config['input']
    if 'parents_manifest' in input_config:
        manifest_path = input_config['parents_manifest']
        print(f"Loading parents from manifest: {manifest_path}")
        parent_manifest = load_parent_manifest(manifest_path)
        parents = parent_manifest.parents
        weights = parent_manifest.get_weights()
    elif 'parents_dir' in input_config:
        dir_path = input_config['parents_dir']
        print(f"Loading parents from directory: {dir_path}")
        parent_manifest = load_parents_from_directory(dir_path)
        parents = parent_manifest.parents
        weights = None
    else:
        # Should never reach here due to validation
        raise ValueError("Must specify either 'parents_manifest' or 'parents_dir'")

    print(f"Loaded {len(parents)} parents")
    if weights:
        print(f"Using weighted parent selection")
    else:
        print(f"Using uniform parent selection")

    # Create output directory
    output_root = Path(run_config['output']['root'])
    overwrite = run_config['output'].get('overwrite', False)

    if output_root.exists() and not overwrite:
        raise FileExistsError(
            f"Output directory already exists: {output_root}\n"
            f"Set 'output.overwrite: true' in config to overwrite"
        )

    output_root.mkdir(parents=True, exist_ok=overwrite)
    print(f"Output directory: {output_root}\n")

    # Generate children
    num_children = run_config['generation']['children']
    print(f"Generating {num_children} children via crossover + mutation...")
    print()

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
        save_individual_to_csv(child, child_path, overwrite=overwrite)

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

        # Progress reporting
        if (i + 1) % 10 == 0 or i == num_children - 1:
            print(f"  Progress: {i+1}/{num_children} children generated")

    # Generate immigrants (if requested)
    num_immigrants = run_config['generation'].get('immigrants', 0)
    if num_immigrants > 0:
        print()
        print(f"Generating {num_immigrants} fresh random immigrants...")
        immigrants = generate_immigrants(
            num_immigrants, placement_config_path, output_root, rng
        )

        # Add immigrant lineage records
        for j, imm in enumerate(immigrants):
            lineage_records.append(
                create_immigrant_record(imm.path, seed + num_children + j)
            )

        print(f"  Generated {len(immigrants)} immigrants")

    # Save lineage
    lineage_log_path = output_root / 'lineage_log.csv'
    save_lineage_log(lineage_records, lineage_log_path)

    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Generated: {num_children} children + {num_immigrants} immigrants")
    print(f"Total individuals: {num_children + num_immigrants}")
    print(f"Output directory: {output_root}")
    print(f"Lineage log: {lineage_log_path}")
    print(f"Files created: {len(list(output_root.glob('*.csv')))}")


def select_two_parents(
    parents: List[Individual],
    weights: Optional[List[float]],
    rng: np.random.Generator
) -> Tuple[Individual, Individual]:
    """
    Select two distinct parents for crossover.

    Uses weighted sampling if weights are provided, otherwise uniform random.
    Ensures the two selected parents are different.

    Args:
        parents: List of parent Individual objects
        weights: Optional list of selection weights (same length as parents)
        rng: Random number generator

    Returns:
        Tuple of (parent_a, parent_b)

    Raises:
        ValueError: If fewer than 2 parents available
    """
    if len(parents) < 2:
        raise ValueError(f"Need at least 2 parents for crossover, got {len(parents)}")

    if weights is not None:
        # Weighted random selection
        weights_array = np.array(weights, dtype=float)
        weights_normalized = weights_array / np.sum(weights_array)

        # Select first parent
        idx_a = rng.choice(len(parents), p=weights_normalized)

        # Select second parent (exclude first)
        remaining_indices = [i for i in range(len(parents)) if i != idx_a]
        remaining_weights = [weights[i] for i in remaining_indices]
        remaining_weights_array = np.array(remaining_weights, dtype=float)
        remaining_weights_normalized = remaining_weights_array / np.sum(remaining_weights_array)

        idx_b = remaining_indices[
            rng.choice(len(remaining_indices), p=remaining_weights_normalized)
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
) -> List[Individual]:
    """
    Generate fresh random layouts using existing placement engine.

    Creates completely new layouts using the stratified placement engine
    to maintain genetic diversity in the population.

    Args:
        num_immigrants: Number of immigrants to generate
        config_path: Path to placement configuration file (config.yaml)
        output_root: Directory to save immigrant CSVs
        rng: Random number generator

    Returns:
        List of Individual objects representing immigrants

    Implementation:
        - Import from src modules
        - Create PlacementEngine instance for each immigrant (with different seeds)
        - Run placement
        - Save CSVs to output_root/immigrant_{j:03d}.csv
        - Return as Individual objects

    This maintains diversity without external input.
    """
    from src.config_loader import load_config, create_entities_from_config
    from src.stratified_placement import PlacementEngine, GridRegion

    # Load configuration once
    config = load_config(config_path)

    # Extract parameters
    grid_config = config.get("grid", {})
    width = grid_config.get("width", 10)
    height = grid_config.get("height", 8)
    grid_region = GridRegion(width, height)

    # Create entities
    entities = create_entities_from_config(config, grid_region)

    # Get placement parameters
    separation_config = config.get("separation", {})
    cross_entity_radius = separation_config.get("cross_entity_radius", 1.0)

    stratification_config = config.get("stratification", {})
    anisotropy_y = stratification_config.get("anisotropy_y", 1.0)
    num_bands = stratification_config.get("num_bands", None)

    immigrants = []

    for j in range(num_immigrants):
        # Create engine with unique seed
        seed = int(rng.integers(0, 2**31))

        engine = PlacementEngine(
            grid_region=grid_region,
            entities=entities,
            cross_entity_radius=cross_entity_radius,
            anisotropy_y=anisotropy_y,
            num_bands=num_bands,
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

        # Save to CSV (always allow overwrite for immigrants)
        save_individual_to_csv(immigrant, immigrant_path, overwrite=True)
        immigrants.append(immigrant)

    return immigrants
