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


def region_aware_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    grid_config: Dict,
    engine_interface: 'EngineInterface',  # Type hint as string to avoid circular import
    rng: np.random.Generator,
    blocks_per_region_x: int = 2,
    blocks_per_region_y: int = 2
) -> Tuple[Individual, Dict]:
    """
    Combine parents using region-aware crossover.

    Groups entities by their allowed regions, then applies block-based crossover
    WITHIN each region independently. This guarantees that entities never
    violate their allowed region constraints during crossover.

    This is ideal for systems where entities have disjoint allowed regions
    (e.g., supply entities in middle rows, exhaust entities in top/bottom rows).

    Algorithm:
        1. Group entity types by their allowed regions (entities with same
           allowed region are grouped together)
        2. For each region group:
           a. Get bounding box of the allowed region
           b. Divide region into blocks_per_region_x × blocks_per_region_y blocks
           c. For each block, randomly inherit from Parent A or Parent B
           d. Collect entities from both parents based on block mask
        3. Combine all regions → child

    Args:
        parent_a: First parent
        parent_b: Second parent
        config: GA configuration
        grid_config: Grid configuration (width, height)
        engine_interface: Interface to access entity allowed regions
        rng: Random number generator
        blocks_per_region_x: Number of blocks to divide each region horizontally
        blocks_per_region_y: Number of blocks to divide each region vertically

    Returns:
        Tuple of (child_individual, region_mask)
        where region_mask maps (region_id, block_x, block_y) -> "A"|"B"

    Example:
        Supply region (y=3-6): vinlet, acinlet
        Exhaust region (y=1-2, 7-8): voutlet, acoutlet

        With blocks_per_region: 2×2:
        - Supply region divided into 4 blocks
        - Exhaust region divided into 4 blocks
        - Total 8 independent inheritance decisions
        - Guarantees: All vinlet/acinlet stay in supply region
                     All voutlet/acoutlet stay in exhaust region
    """
    from .engine_interface import EngineInterface  # Import here to avoid circular dependency

    # Step 1: Group entity types by their allowed regions
    # Two entities belong to the same region group if they have identical allowed_region sets
    region_groups = {}  # Maps frozenset(allowed_region) -> [entity_types]

    all_entity_types = set(parent_a.placements.keys()) | set(parent_b.placements.keys())

    for entity_type in all_entity_types:
        if entity_type not in engine_interface.entity_map:
            # Unknown entity type, skip
            continue

        entity = engine_interface.entity_map[entity_type]
        # Convert allowed_region Set[GridCell] to frozenset for hashability
        region_key = frozenset((cell.x, cell.y) for cell in entity.allowed_region)

        if region_key not in region_groups:
            region_groups[region_key] = {
                'entity_types': [],
                'cells': entity.allowed_region  # Keep original Set[GridCell]
            }
        region_groups[region_key]['entity_types'].append(entity_type)

    # Step 2: For each region group, apply block crossover
    child_placements = {}
    crossover_mask = {}

    for region_id, (region_key, region_data) in enumerate(region_groups.items()):
        entity_types_in_region = region_data['entity_types']
        allowed_cells = region_data['cells']

        # Get bounding box of this region
        x_coords = [cell.x for cell in allowed_cells]
        y_coords = [cell.y for cell in allowed_cells]

        if not x_coords or not y_coords:
            # Empty region, skip
            continue

        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        region_width = x_max - x_min + 1
        region_height = y_max - y_min + 1

        # Calculate block dimensions within this region
        block_width = region_width / blocks_per_region_x
        block_height = region_height / blocks_per_region_y

        # Create block mask for this region
        block_mask = {}
        for bx in range(blocks_per_region_x):
            for by in range(blocks_per_region_y):
                use_parent_a = rng.random() < 0.5
                block_mask[(bx, by)] = "A" if use_parent_a else "B"
                crossover_mask[(region_id, bx, by)] = "A" if use_parent_a else "B"

        # Function to determine which block a position belongs to within this region
        def get_block_in_region(x: int, y: int) -> Optional[Tuple[int, int]]:
            # Check if position is within this region's bounding box
            if not (x_min <= x <= x_max and y_min <= y <= y_max):
                return None

            # Calculate block coordinates relative to region
            bx = min(int((x - x_min) / block_width), blocks_per_region_x - 1)
            by = min(int((y - y_min) / block_height), blocks_per_region_y - 1)
            return (bx, by)

        # Inherit entities for this region based on block mask
        for entity_type in entity_types_in_region:
            if entity_type not in child_placements:
                child_placements[entity_type] = []

            # Get positions from both parents for this entity type
            positions_a = parent_a.placements.get(entity_type, [])
            positions_b = parent_b.placements.get(entity_type, [])

            # Add positions from A based on block mask
            for x, y in positions_a:
                block = get_block_in_region(x, y)
                if block is not None and block_mask.get(block) == "A":
                    child_placements[entity_type].append((x, y))

            # Add positions from B based on block mask
            for x, y in positions_b:
                block = get_block_in_region(x, y)
                if block is not None and block_mask.get(block) == "B":
                    child_placements[entity_type].append((x, y))

    # Create child individual
    child_id = f"{parent_a.id}_x_{parent_b.id}_region"
    child = Individual(
        id=child_id,
        path=parent_a.path.parent / f"{child_id}.csv",
        placements=child_placements,
        metadata={
            'parent_a_id': parent_a.id,
            'parent_b_id': parent_b.id,
            'crossover_strategy': 'region_aware',
            'num_regions': len(region_groups),
            'blocks_per_region_x': blocks_per_region_x,
            'blocks_per_region_y': blocks_per_region_y,
            'provisional': True  # Needs repair
        }
    )

    return child, crossover_mask


def apply_crossover(
    parent_a: Individual,
    parent_b: Individual,
    config: Dict,
    grid_config: Dict,
    band_config: Dict,
    rng: np.random.Generator,
    engine_interface: Optional['EngineInterface'] = None
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
        engine_interface: Optional engine interface (required for region_aware strategy)

    Returns:
        Tuple of (child_individual, crossover_mask)

    Raises:
        ValueError: If strategy is unknown or if region_aware is selected but
                   engine_interface is not provided
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

    elif strategy == 'region_aware':
        if engine_interface is None:
            raise ValueError(
                "region_aware crossover requires engine_interface parameter. "
                "Please pass engine_interface to apply_crossover()."
            )
        blocks_per_region_x = config.get('region_aware', {}).get('blocks_per_region_x', 2)
        blocks_per_region_y = config.get('region_aware', {}).get('blocks_per_region_y', 2)
        return region_aware_crossover(
            parent_a, parent_b, config, grid_config, engine_interface, rng,
            blocks_per_region_x, blocks_per_region_y
        )

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
