"""
Crossover operators for GA extension.

Implements band-wise and block-2D crossover strategies that respect
stratified placement structure.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np

from .data_models import Individual
from .band_utils import partition_by_band


def bandwise_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    grid_config: Dict,
    band_config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, Dict]:
    """
    Combine two parents using band-wise crossover.

    For each (entity_type, band_id) combination, randomly select which parent
    to inherit from. This preserves band structure while enabling recombination.

    Args:
        parent_a: First parent
        parent_b: Second parent
        config: GA configuration
        grid_config: Grid configuration (width, height)
        band_config: Band configuration (num_bands)
        rng: Random number generator

    Returns:
        Tuple of (child_individual, crossover_mask)
        where crossover_mask maps (entity_type, band_id) -> "A"|"B"

    Note:
        Child may have conflicts (overlapping positions) which will be
        resolved by the repair process.
    """
    # Partition both parents by band
    partition_a = partition_by_band(parent_a.placements, grid_config, band_config)
    partition_b = partition_by_band(parent_b.placements, grid_config, band_config)

    # Get all band-entity combinations
    all_keys = set(partition_a.keys()) | set(partition_b.keys())

    # Create crossover mask and child placements
    crossover_mask = {}
    child_placements = {}

    for key in all_keys:
        entity_type, band_id = key

        # Randomly choose parent (50/50 by default, configurable)
        crossover_prob = config.get('crossover_rate', 0.5)
        use_parent_a = rng.random() < crossover_prob

        if use_parent_a and key in partition_a:
            selected_positions = partition_a[key].copy()
            crossover_mask[key] = "A"
        elif not use_parent_a and key in partition_b:
            selected_positions = partition_b[key].copy()
            crossover_mask[key] = "B"
        elif key in partition_a:
            # Fallback to A if B doesn't have this band-entity
            selected_positions = partition_a[key].copy()
            crossover_mask[key] = "A (fallback)"
        elif key in partition_b:
            # Fallback to B if A doesn't have this band-entity
            selected_positions = partition_b[key].copy()
            crossover_mask[key] = "B (fallback)"
        else:
            # Neither parent has this combination (shouldn't happen)
            selected_positions = []
            crossover_mask[key] = "none"

        # Add to child placements
        if entity_type not in child_placements:
            child_placements[entity_type] = []
        child_placements[entity_type].extend(selected_positions)

    # Create child individual
    child_id = f"{parent_a.id}_x_{parent_b.id}"
    child = Individual(
        id=child_id,
        path=parent_a.path.parent / f"{child_id}.csv",
        placements=child_placements,
        metadata={
            'parent_a_id': parent_a.id,
            'parent_b_id': parent_b.id,
            'crossover_strategy': 'bandwise',
            'provisional': True  # Needs repair
        }
    )

    return child, crossover_mask


def block_2d_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    grid_config: Dict,
    rng: np.random.Generator,
    blocks_x: int = 4,
    blocks_y: int = 4
) -> Tuple[Individual, Dict]:
    """
    Combine two parents using 2D block crossover.

    Divides grid into rectangular blocks and inherits each block from
    one parent or the other. Less band-aware than bandwise crossover,
    but provides more spatial diversity.

    Args:
        parent_a: First parent
        parent_b: Second parent
        config: GA configuration
        grid_config: Grid configuration
        rng: Random number generator
        blocks_x: Number of horizontal blocks
        blocks_y: Number of vertical blocks

    Returns:
        Tuple of (child_individual, block_mask)
        where block_mask maps (block_x, block_y) -> "A"|"B"
    """
    width = grid_config['width']
    height = grid_config['height']

    # Calculate block dimensions
    block_width = width / blocks_x
    block_height = height / blocks_y

    # Create block mask
    block_mask = {}
    for bx in range(blocks_x):
        for by in range(blocks_y):
            use_parent_a = rng.random() < 0.5
            block_mask[(bx, by)] = "A" if use_parent_a else "B"

    # Function to determine which block a position belongs to
    def get_block(x: int, y: int) -> Tuple[int, int]:
        bx = min(int((x - 1) / block_width), blocks_x - 1)
        by = min(int((y - 1) / block_height), blocks_y - 1)
        return (bx, by)

    # Combine placements based on block mask
    child_placements = {}

    for entity_type in set(parent_a.placements.keys()) | set(parent_b.placements.keys()):
        child_placements[entity_type] = []

        # Get positions from both parents
        positions_a = parent_a.placements.get(entity_type, [])
        positions_b = parent_b.placements.get(entity_type, [])

        # Add positions from A based on block mask
        for x, y in positions_a:
            block = get_block(x, y)
            if block_mask.get(block) == "A":
                child_placements[entity_type].append((x, y))

        # Add positions from B based on block mask
        for x, y in positions_b:
            block = get_block(x, y)
            if block_mask.get(block) == "B":
                child_placements[entity_type].append((x, y))

    # Create child individual
    child_id = f"{parent_a.id}_x_{parent_b.id}_block2d"
    child = Individual(
        id=child_id,
        path=parent_a.path.parent / f"{child_id}.csv",
        placements=child_placements,
        metadata={
            'parent_a_id': parent_a.id,
            'parent_b_id': parent_b.id,
            'crossover_strategy': 'block_2d',
            'blocks_x': blocks_x,
            'blocks_y': blocks_y,
            'provisional': True  # Needs repair
        }
    )

    return child, block_mask


def entity_wise_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, Dict]:
    """
    Combine parents using entity-wise crossover.

    For each entity type, inherit all placements from one parent or the other.
    This is the coarsest granularity and may require more repair.

    Args:
        parent_a: First parent
        parent_b: Second parent
        config: GA configuration
        rng: Random number generator

    Returns:
        Tuple of (child_individual, entity_mask)
        where entity_mask maps entity_type -> "A"|"B"
    """
    all_entity_types = set(parent_a.placements.keys()) | set(parent_b.placements.keys())

    entity_mask = {}
    child_placements = {}

    for entity_type in all_entity_types:
        # Randomly choose parent
        use_parent_a = rng.random() < 0.5

        if use_parent_a and entity_type in parent_a.placements:
            child_placements[entity_type] = parent_a.placements[entity_type].copy()
            entity_mask[entity_type] = "A"
        elif not use_parent_a and entity_type in parent_b.placements:
            child_placements[entity_type] = parent_b.placements[entity_type].copy()
            entity_mask[entity_type] = "B"
        elif entity_type in parent_a.placements:
            child_placements[entity_type] = parent_a.placements[entity_type].copy()
            entity_mask[entity_type] = "A (fallback)"
        elif entity_type in parent_b.placements:
            child_placements[entity_type] = parent_b.placements[entity_type].copy()
            entity_mask[entity_type] = "B (fallback)"

    # Create child individual
    child_id = f"{parent_a.id}_x_{parent_b.id}_entity"
    child = Individual(
        id=child_id,
        path=parent_a.path.parent / f"{child_id}.csv",
        placements=child_placements,
        metadata={
            'parent_a_id': parent_a.id,
            'parent_b_id': parent_b.id,
            'crossover_strategy': 'entity_wise',
            'provisional': True  # Needs repair
        }
    )

    return child, entity_mask


def apply_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    grid_config: Dict,
    band_config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, Dict]:
    """
    Apply crossover using configured strategy.

    This is the main entry point for crossover operations. It dispatches
    to the appropriate crossover strategy based on configuration.

    Args:
        parent_a: First parent
        parent_b: Second parent
        config: GA configuration
        grid_config: Grid configuration
        band_config: Band configuration
        rng: Random number generator

    Returns:
        Tuple of (child_individual, crossover_mask)
    """
    strategy = config.get('crossover_strategy', 'bandwise')

    if strategy == 'bandwise':
        return bandwise_crossover(parent_a, parent_b, config, grid_config, band_config, rng)
    elif strategy == 'block_2d':
        blocks_x = config.get('block_2d', {}).get('blocks_x', 4)
        blocks_y = config.get('block_2d', {}).get('blocks_y', 4)
        return block_2d_crossover(parent_a, parent_b, config, grid_config, rng, blocks_x, blocks_y)
    elif strategy == 'entity_wise':
        return entity_wise_crossover(parent_a, parent_b, config, rng)
    else:
        raise ValueError(f"Unknown crossover strategy: {strategy}")


def detect_conflicts(individual: Individual) -> List[Tuple[int, int]]:
    """
    Detect cell conflicts (overlapping positions) in an individual.

    Args:
        individual: Individual to check

    Returns:
        List of (x, y) positions that have conflicts
    """
    position_count = {}

    for entity_type, positions in individual.placements.items():
        for pos in positions:
            position_count[pos] = position_count.get(pos, 0) + 1

    # Return positions with more than one entity
    conflicts = [pos for pos, count in position_count.items() if count > 1]

    return conflicts


def crossover_statistics(child: Individual, parent_a: Individual, parent_b: Individual) -> Dict:
    """
    Calculate statistics about the crossover operation.

    Args:
        child: Child individual
        parent_a: First parent
        parent_b: Second parent

    Returns:
        Dictionary with crossover statistics
    """
    conflicts = detect_conflicts(child)

    stats = {
        'total_placements': child.total_entity_count(),
        'conflicts': len(conflicts),
        'conflict_rate': len(conflicts) / max(child.total_entity_count(), 1),
        'parent_a_placements': parent_a.total_entity_count(),
        'parent_b_placements': parent_b.total_entity_count(),
    }

    # Count how many placements per entity type
    for entity_type in set(child.placements.keys()):
        stats[f'{entity_type}_count'] = child.get_entity_count(entity_type)

    return stats
