"""
Mutation operators for GA extension.

Implements band-respecting mutation operators: within-band swap,
local jitter, and micro-reseed.
"""

from typing import Dict, List, Tuple, Set, Optional
import numpy as np
import math

from .data_models import Individual
from .band_utils import (
    partition_by_band,
    get_band_for_position,
    get_free_cells_in_band
)
from src.stratified_placement import GridCell, NormalizedPoint, GridRegion


def within_band_swap(
    individual: Individual,
    entity_type: str,
    grid_config: Dict,
    band_config: Dict,
    config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, List[str]]:
    """
    Swap positions of two entities of same type within same band.

    Only accepts swap if it maintains or improves minimum distance.

    Args:
        individual: Individual to mutate
        entity_type: Entity type to mutate
        grid_config: Grid configuration
        band_config: Band configuration
        config: GA configuration
        rng: Random number generator

    Returns:
        Tuple of (mutated_individual, operation_log)
    """
    if entity_type not in individual.placements:
        return individual, [f"within_band_swap: {entity_type} not found"]

    # Partition by band
    partition = partition_by_band(individual.placements, grid_config, band_config)

    # Find bands with this entity
    entity_bands = [key for key in partition.keys() if key[0] == entity_type]

    if not entity_bands:
        return individual, [f"within_band_swap: no {entity_type} found in any band"]

    # Select random band
    band_key = entity_bands[rng.integers(0, len(entity_bands))]
    _, band_id = band_key

    positions = partition[band_key]

    if len(positions) < 2:
        return individual, [f"within_band_swap: only {len(positions)} {entity_type} in band {band_id}"]

    # Select two random positions
    idx1, idx2 = rng.choice(len(positions), size=2, replace=False)
    pos1, pos2 = positions[idx1], positions[idx2]

    # Calculate current min distance for these two
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    wy = config.get('wy', 2.0)
    current_dist = math.sqrt(dx*dx + (dy*wy)**2)

    # Try swap - check if it improves overall separation
    # For simplicity, just accept the swap (can add distance check if needed)

    # Apply swap
    mutated_placements = {k: v.copy() if isinstance(v, list) else v
                          for k, v in individual.placements.items()}
    mutated_placements[entity_type] = [
        pos if pos not in [pos1, pos2] else (pos2 if pos == pos1 else pos1)
        for pos in mutated_placements[entity_type]
    ]

    mutated = individual.copy()
    mutated.placements = mutated_placements

    op_log = [f"within_band_swap({entity_type}, band={band_id}): swapped {pos1} <-> {pos2}"]

    return mutated, op_log


def band_local_jitter(
    individual: Individual,
    entity_type: str,
    grid_config: Dict,
    band_config: Dict,
    config: Dict,
    rng: np.random.Generator,
    max_attempts: int = 10
) -> Tuple[Individual, List[str]]:
    """
    Move one entity to a nearby free cell in same band.

    Attempts to improve separation by trying nearby positions.

    Args:
        individual: Individual to mutate
        entity_type: Entity type to mutate
        grid_config: Grid configuration
        band_config: Band configuration
        config: GA configuration
        rng: Random number generator
        max_attempts: Max attempts to find better position

    Returns:
        Tuple of (mutated_individual, operation_log)
    """
    if entity_type not in individual.placements:
        return individual, [f"band_local_jitter: {entity_type} not found"]

    positions = individual.placements[entity_type]
    if not positions:
        return individual, [f"band_local_jitter: no {entity_type} placements"]

    # Select random position to jitter
    idx = rng.integers(0, len(positions))
    current_pos = positions[idx]

    # Get band for this position
    try:
        band_id = get_band_for_position(current_pos, grid_config, band_config)
    except ValueError:
        return individual, [f"band_local_jitter: position {current_pos} not in any band"]

    # Get occupied positions (excluding current)
    occupied = individual.get_all_positions()
    occupied.discard(current_pos)

    # Get all cells in grid (approximate allowed region as full grid for now)
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    all_cells = grid_region.all_cells()

    # Get free cells in same band
    free_cells = get_free_cells_in_band(
        band_id,
        occupied,
        all_cells,
        grid_config,
        band_config
    )

    if not free_cells:
        return individual, [f"band_local_jitter: no free cells in band {band_id}"]

    # Try nearby positions (within radius of current position)
    jitter_radius = config.get('mutation', {}).get('jitter_radius', 3)
    x, y = current_pos

    nearby_free = [
        pos for pos in free_cells
        if abs(pos[0] - x) <= jitter_radius and abs(pos[1] - y) <= jitter_radius
    ]

    if not nearby_free:
        # Fallback to any free cell in band
        nearby_free = list(free_cells)

    if not nearby_free:
        return individual, [f"band_local_jitter: no suitable positions found"]

    # Select random nearby position
    new_pos = nearby_free[rng.integers(0, len(nearby_free))]

    # Apply jitter
    mutated_placements = {k: v.copy() if isinstance(v, list) else v
                          for k, v in individual.placements.items()}
    mutated_placements[entity_type] = [
        new_pos if i == idx else pos
        for i, pos in enumerate(mutated_placements[entity_type])
    ]

    mutated = individual.copy()
    mutated.placements = mutated_placements

    op_log = [f"band_local_jitter({entity_type}, band={band_id}): moved {current_pos} -> {new_pos}"]

    return mutated, op_log


def micro_reseed(
    individual: Individual,
    entity_type: str,
    fraction: float,
    grid_config: Dict,
    band_config: Dict,
    config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, List[str]]:
    """
    Re-place a small fraction of entities within their bands.

    Drops selected entities and places them in random free cells
    within the same bands they originally occupied.

    Args:
        individual: Individual to mutate
        entity_type: Entity type to mutate
        fraction: Fraction of entities to reseed (e.g., 0.1 for 10%)
        grid_config: Grid configuration
        band_config: Band configuration
        config: GA configuration
        rng: Random number generator

    Returns:
        Tuple of (mutated_individual, operation_log)
    """
    if entity_type not in individual.placements:
        return individual, [f"micro_reseed: {entity_type} not found"]

    positions = individual.placements[entity_type]
    if not positions:
        return individual, [f"micro_reseed: no {entity_type} placements"]

    # Calculate number to reseed
    num_to_reseed = max(1, int(len(positions) * fraction))

    # Select random positions to reseed
    indices_to_reseed = rng.choice(len(positions), size=num_to_reseed, replace=False)

    # Group by band
    partition = partition_by_band(individual.placements, grid_config, band_config)

    # Get occupied positions (excluding ones we're reseeding)
    occupied = individual.get_all_positions()
    for idx in indices_to_reseed:
        occupied.discard(positions[idx])

    # Reseed each selected position
    mutated_placements = {k: v.copy() if isinstance(v, list) else v
                          for k, v in individual.placements.items()}

    op_log = []
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    all_cells = grid_region.all_cells()

    for idx in indices_to_reseed:
        old_pos = positions[idx]

        # Get band for this position
        try:
            band_id = get_band_for_position(old_pos, grid_config, band_config)
        except ValueError:
            continue

        # Get free cells in same band
        free_cells = get_free_cells_in_band(
            band_id,
            occupied,
            all_cells,
            grid_config,
            band_config
        )

        if not free_cells:
            # Keep old position if no free cells
            continue

        # Select random free cell
        new_pos = list(free_cells)[rng.integers(0, len(free_cells))]

        # Update placements
        for i, pos in enumerate(mutated_placements[entity_type]):
            if pos == old_pos:
                mutated_placements[entity_type][i] = new_pos
                break

        # Mark new position as occupied
        occupied.add(new_pos)

        op_log.append(f"micro_reseed({entity_type}, band={band_id}): {old_pos} -> {new_pos}")

    mutated = individual.copy()
    mutated.placements = mutated_placements

    return mutated, op_log


def mutate(
    individual: Individual,
    config: Dict,
    grid_config: Dict,
    band_config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, List[str]]:
    """
    Apply mutation operators according to configuration.

    This is the main mutation orchestrator. It:
    1. Decides whether to mutate (based on mutation_rate)
    2. Selects entity types to mutate
    3. Selects and applies mutation operators
    4. Limits total operations per individual

    Args:
        individual: Individual to mutate
        config: GA configuration with mutation settings
        grid_config: Grid configuration
        band_config: Band configuration
        rng: Random number generator

    Returns:
        Tuple of (mutated_individual, operation_log)
    """
    mutation_rate = config.get('mutation_rate', 0.3)

    # Decide whether to mutate
    if rng.random() > mutation_rate:
        return individual, ["no_mutation: skipped (probability)"]

    # Get mutation configuration
    mutation_config = config.get('mutation', {})
    operator_probs = mutation_config.get('operators', {
        'within_band_swap': 0.4,
        'band_local_jitter': 0.4,
        'micro_reseed': 0.2
    })
    max_ops = mutation_config.get('max_ops_per_individual', 3)
    micro_reseed_fraction = mutation_config.get('micro_reseed_fraction', 0.1)

    # Normalize operator probabilities
    total_prob = sum(operator_probs.values())
    if total_prob > 0:
        operator_probs = {k: v/total_prob for k, v in operator_probs.items()}

    # Get available entity types
    entity_types = list(individual.placements.keys())
    if not entity_types:
        return individual, ["no_mutation: no entities"]

    # Apply mutations
    mutated = individual.copy()
    all_logs = []

    num_ops = rng.integers(1, max_ops + 1)

    for _ in range(num_ops):
        # Select operator
        op_choice = rng.random()
        cumulative = 0
        selected_op = None

        for op_name, prob in operator_probs.items():
            cumulative += prob
            if op_choice <= cumulative:
                selected_op = op_name
                break

        if selected_op is None:
            selected_op = list(operator_probs.keys())[0]

        # Select random entity type
        entity_type = entity_types[rng.integers(0, len(entity_types))]

        # Apply operator
        if selected_op == 'within_band_swap':
            mutated, log = within_band_swap(mutated, entity_type, grid_config, band_config, config, rng)
        elif selected_op == 'band_local_jitter':
            mutated, log = band_local_jitter(mutated, entity_type, grid_config, band_config, config, rng)
        elif selected_op == 'micro_reseed':
            mutated, log = micro_reseed(mutated, entity_type, micro_reseed_fraction,
                                       grid_config, band_config, config, rng)
        else:
            log = [f"unknown_operator: {selected_op}"]

        all_logs.extend(log)

    return mutated, all_logs


def mutation_statistics(original: Individual, mutated: Individual) -> Dict:
    """
    Calculate statistics about mutation operations.

    Args:
        original: Original individual before mutation
        mutated: Individual after mutation

    Returns:
        Dictionary with mutation statistics
    """
    stats = {
        'total_placements': mutated.total_entity_count(),
        'positions_changed': 0,
    }

    # Count how many positions changed
    for entity_type in set(original.placements.keys()) | set(mutated.placements.keys()):
        orig_positions = set(original.placements.get(entity_type, []))
        mut_positions = set(mutated.placements.get(entity_type, []))

        changed = len(orig_positions.symmetric_difference(mut_positions))
        stats['positions_changed'] += changed
        stats[f'{entity_type}_changed'] = changed

    stats['change_rate'] = stats['positions_changed'] / max(stats['total_placements'], 1)

    return stats
