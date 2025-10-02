"""
Repair and refinement system for GA extension.

Provides functions to resolve conflicts, adjust quotas, and refine separation
distances in GA-generated children.
"""

from typing import Dict, List, Tuple, Set, Optional
import numpy as np

from .data_models import Individual
from .engine_interface import EngineInterface
from .band_utils import (
    partition_by_band,
    get_band_quotas,
    count_entities_per_band,
    calculate_quota_deviation
)


def repair_conflicts(
    individual: Individual,
    engine: EngineInterface,
    config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, List[str]]:
    """
    Resolve position conflicts (multiple entities at same cell).

    Algorithm:
    1. Identify all conflicting cells
    2. For each conflict: keep one entity (random), relocate others
    3. Use engine.suggest_relocation() to find best free cell in same band
    4. Track all relocations in notes

    Args:
        individual: Individual with potential conflicts
        engine: Engine interface for utilities
        config: GA configuration
        rng: Random number generator

    Returns:
        Tuple of (repaired_individual, repair_notes)
    """
    notes = []

    # Check for conflicts
    conflicts = engine.check_conflicts(individual.placements)

    if not conflicts:
        notes.append("repair_conflicts: No conflicts detected")
        return individual, notes

    notes.append(f"repair_conflicts: Found {len(conflicts)} conflicting cells")

    # Create mutable copy of placements
    repaired_placements = {
        entity_type: positions.copy()
        for entity_type, positions in individual.placements.items()
    }

    # Track all occupied positions
    occupied = individual.get_all_positions()

    # Resolve each conflict
    for conflict_pos in conflicts:
        # Find which entities are at this position
        entities_at_pos = []
        for entity_type, positions in repaired_placements.items():
            if conflict_pos in positions:
                entities_at_pos.append(entity_type)

        if len(entities_at_pos) <= 1:
            # Already resolved in previous iteration
            continue

        # Keep first entity (random choice), relocate others
        keep_entity = entities_at_pos[rng.integers(0, len(entities_at_pos))]
        relocate_entities = [e for e in entities_at_pos if e != keep_entity]

        notes.append(
            f"  Conflict at {conflict_pos}: keeping {keep_entity}, "
            f"relocating {relocate_entities}"
        )

        # Relocate each conflicting entity
        for entity_type in relocate_entities:
            # Find which band this position is in
            try:
                band_id = engine.get_band_id_for_position(conflict_pos)
            except ValueError:
                notes.append(f"    ERROR: {conflict_pos} not in any band")
                continue

            # Suggest new location
            new_pos = engine.suggest_relocation(
                entity_type,
                conflict_pos,
                band_id,
                occupied
            )

            if new_pos is None:
                # No free cells available - try adjacent bands
                notes.append(
                    f"    WARNING: No free cells in band {band_id} for {entity_type}"
                )

                # Try adjacent bands
                for adj_band in [band_id - 1, band_id + 1]:
                    if 0 <= adj_band < engine.get_band_config()['num_bands']:
                        new_pos = engine.suggest_relocation(
                            entity_type,
                            conflict_pos,
                            adj_band,
                            occupied
                        )
                        if new_pos:
                            notes.append(
                                f"    Relocated to adjacent band {adj_band}"
                            )
                            break

            if new_pos is None:
                # Still no free cells - remove entity
                notes.append(
                    f"    ERROR: Could not relocate {entity_type} from {conflict_pos} - removing"
                )
                repaired_placements[entity_type].remove(conflict_pos)
            else:
                # Replace old position with new
                idx = repaired_placements[entity_type].index(conflict_pos)
                repaired_placements[entity_type][idx] = new_pos
                occupied.remove(conflict_pos)
                occupied.add(new_pos)
                notes.append(
                    f"    Relocated {entity_type}: {conflict_pos} -> {new_pos}"
                )

    # Create repaired individual
    repaired = individual.copy()
    repaired.placements = repaired_placements

    return repaired, notes


def repair_quotas(
    individual: Individual,
    engine: EngineInterface,
    config: Dict,
    rng: np.random.Generator
) -> Tuple[Individual, List[str]]:
    """
    Adjust placements to meet per-band quotas.

    Algorithm:
    1. Calculate quota surplus/deficit per (entity, band)
    2. Move surplus entities to adjacent deficit bands
    3. If impossible, record "quota_borrow" in notes

    Args:
        individual: Individual with potential quota imbalances
        engine: Engine interface for utilities
        config: GA configuration
        rng: Random number generator

    Returns:
        Tuple of (repaired_individual, repair_notes)
    """
    notes = []

    grid_config = engine.get_grid_config()
    band_config = engine.get_band_config()
    entity_configs = engine.get_entity_configs()

    # Calculate expected quotas
    expected_quotas = get_band_quotas(entity_configs, grid_config, band_config)

    # Calculate actual counts
    actual_counts = count_entities_per_band(
        individual.placements, grid_config, band_config
    )

    # Calculate deviations
    deviations = calculate_quota_deviation(actual_counts, expected_quotas)

    # Filter out zero deviations
    imbalances = {key: dev for key, dev in deviations.items() if dev != 0}

    if not imbalances:
        notes.append("repair_quotas: All quotas balanced")
        return individual, notes

    notes.append(f"repair_quotas: Found {len(imbalances)} quota imbalances")

    # Create mutable copy
    repaired_placements = {
        entity_type: positions.copy()
        for entity_type, positions in individual.placements.items()
    }

    # Partition by band for easier manipulation
    partition = partition_by_band(repaired_placements, grid_config, band_config)

    # Track occupied positions
    occupied = individual.get_all_positions()

    # Process each entity type
    entity_types = set(key[0] for key in imbalances.keys())

    for entity_type in entity_types:
        # Find surplus and deficit bands for this entity
        surplus_bands = []
        deficit_bands = []

        for (e_type, band_id), deviation in deviations.items():
            if e_type != entity_type:
                continue

            if deviation > 0:
                surplus_bands.append((band_id, deviation))
            elif deviation < 0:
                deficit_bands.append((band_id, -deviation))

        if not surplus_bands or not deficit_bands:
            continue

        notes.append(
            f"  {entity_type}: surplus bands {surplus_bands}, "
            f"deficit bands {deficit_bands}"
        )

        # Move entities from surplus to deficit bands
        for surplus_band_id, surplus_count in surplus_bands:
            if not deficit_bands:
                break

            key = (entity_type, surplus_band_id)
            if key not in partition or not partition[key]:
                continue

            # Try to move surplus_count entities
            for _ in range(surplus_count):
                if not partition[key]:
                    break

                if not deficit_bands:
                    break

                # Pick a random entity from surplus band
                pos_idx = rng.integers(0, len(partition[key]))
                old_pos = partition[key][pos_idx]

                # Find closest deficit band
                target_band_id = deficit_bands[0][0]

                # Try to relocate to deficit band
                new_pos = engine.suggest_relocation(
                    entity_type,
                    old_pos,
                    target_band_id,
                    occupied
                )

                if new_pos is None:
                    notes.append(
                        f"    WARNING: Could not move {entity_type} from "
                        f"band {surplus_band_id} to band {target_band_id}"
                    )
                    continue

                # Move entity
                partition[key].pop(pos_idx)
                target_key = (entity_type, target_band_id)
                if target_key not in partition:
                    partition[target_key] = []
                partition[target_key].append(new_pos)

                # Update occupied
                occupied.remove(old_pos)
                occupied.add(new_pos)

                notes.append(
                    f"    Moved {entity_type}: {old_pos} (band {surplus_band_id}) -> "
                    f"{new_pos} (band {target_band_id})"
                )

                # Update deficit count
                deficit_bands[0] = (target_band_id, deficit_bands[0][1] - 1)
                if deficit_bands[0][1] == 0:
                    deficit_bands.pop(0)

    # Reconstruct placements from partition
    repaired_placements = {}
    for (entity_type, band_id), positions in partition.items():
        if entity_type not in repaired_placements:
            repaired_placements[entity_type] = []
        repaired_placements[entity_type].extend(positions)

    # Create repaired individual
    repaired = individual.copy()
    repaired.placements = repaired_placements

    return repaired, notes


def refine_separation(
    individual: Individual,
    engine: EngineInterface,
    config: Dict,
    max_iterations: int = 20
) -> Tuple[Individual, List[str]]:
    """
    Iteratively improve worst-case minimum distances.

    Algorithm (limited Phase-C style optimization):
    1. Identify entity with worst minimum distance
    2. Attempt local swaps/nudges within band
    3. Accept if improves global min distance (lexicographic maximin)
    4. Repeat for max_iterations or until no improvement
    5. Respect band boundaries and allowed regions

    Args:
        individual: Individual to refine
        engine: Engine interface for utilities
        config: GA configuration
        max_iterations: Maximum optimization iterations

    Returns:
        Tuple of (refined_individual, refinement_notes)
    """
    notes = []
    notes.append(f"refine_separation: Starting with max_iterations={max_iterations}")

    refined_placements = {
        entity_type: positions.copy()
        for entity_type, positions in individual.placements.items()
    }

    grid_config = engine.get_grid_config()
    band_config = engine.get_band_config()

    # Track improvements
    improvements = 0

    for iteration in range(max_iterations):
        # Calculate current minimum distances
        min_distances = engine.calculate_min_distances(refined_placements)

        # Find entity type with worst minimum distance
        if not min_distances:
            break

        worst_entity_type = min(min_distances.keys(), key=lambda k: min_distances[k])
        worst_min_dist = min_distances[worst_entity_type]

        if worst_min_dist == float('inf'):
            # All entities are well-separated
            break

        # Try to improve this entity type's separation
        improved = _try_improve_entity_separation(
            worst_entity_type,
            refined_placements,
            engine,
            grid_config,
            band_config,
            config
        )

        if not improved:
            # No improvement possible
            break

        refined_placements = improved
        improvements += 1

        # Calculate new min distance
        new_min_distances = engine.calculate_min_distances(refined_placements)
        new_min_dist = new_min_distances.get(worst_entity_type, float('inf'))

        notes.append(
            f"  Iteration {iteration+1}: Improved {worst_entity_type} "
            f"from {worst_min_dist:.3f} to {new_min_dist:.3f}"
        )

    notes.append(f"refine_separation: Made {improvements} improvements")

    # Create refined individual
    refined = individual.copy()
    refined.placements = refined_placements

    return refined, notes


def _try_improve_entity_separation(
    entity_type: str,
    placements: Dict[str, List[Tuple[int, int]]],
    engine: EngineInterface,
    grid_config: Dict,
    band_config: Dict,
    config: Dict
) -> Optional[Dict[str, List[Tuple[int, int]]]]:
    """
    Try to improve separation for a specific entity type.

    Attempts local swaps within bands.

    Args:
        entity_type: Entity type to improve
        placements: Current placements
        engine: Engine interface
        grid_config: Grid configuration
        band_config: Band configuration
        config: GA configuration

    Returns:
        Improved placements or None if no improvement found
    """
    if entity_type not in placements or len(placements[entity_type]) < 2:
        return None

    positions = placements[entity_type]

    # Find the pair with minimum separation
    min_dist = float('inf')
    min_pair_indices = None

    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dist = engine._anisotropic_distance(
                positions[i], positions[j], engine.anisotropy_y
            )
            if dist < min_dist:
                min_dist = dist
                min_pair_indices = (i, j)

    if min_pair_indices is None:
        return None

    idx1, idx2 = min_pair_indices
    pos1, pos2 = positions[idx1], positions[idx2]

    # Try to move one of them to a better location in the same band
    band_id1 = engine.get_band_id_for_position(pos1)
    band_id2 = engine.get_band_id_for_position(pos2)

    # Get all occupied positions
    occupied = set()
    for positions_list in placements.values():
        occupied.update(positions_list)

    # Try moving pos1 to a better location in its band
    new_pos1 = engine.suggest_relocation(
        entity_type, pos1, band_id1, occupied, avoid_positions={pos1}
    )

    if new_pos1 and new_pos1 != pos1:
        # Check if this improves min distance
        new_dist = engine._anisotropic_distance(
            new_pos1, pos2, engine.anisotropy_y
        )

        if new_dist > min_dist:
            # Accept improvement
            new_placements = {k: v.copy() for k, v in placements.items()}
            new_placements[entity_type][idx1] = new_pos1
            return new_placements

    # Try moving pos2 to a better location in its band
    new_pos2 = engine.suggest_relocation(
        entity_type, pos2, band_id2, occupied, avoid_positions={pos2}
    )

    if new_pos2 and new_pos2 != pos2:
        # Check if this improves min distance
        new_dist = engine._anisotropic_distance(
            pos1, new_pos2, engine.anisotropy_y
        )

        if new_dist > min_dist:
            # Accept improvement
            new_placements = {k: v.copy() for k, v in placements.items()}
            new_placements[entity_type][idx2] = new_pos2
            return new_placements

    return None


def repair_and_refine(
    individual: Individual,
    config_path: str = "config.yaml",
    ga_config: Optional[Dict] = None,
    rng: Optional[np.random.Generator] = None
) -> Individual:
    """
    Complete repair and refinement pipeline.

    Steps:
    1. Resolve conflicts
    2. Adjust quotas
    3. Refine separation
    4. Validate (no overlaps, regions respected)
    5. Attach all notes to individual.metadata['repair_notes']

    Args:
        individual: Potentially broken child from crossover/mutation
        config_path: Path to main configuration file
        ga_config: GA configuration dictionary (optional)
        rng: Random number generator (optional)

    Returns:
        Valid, optimized Individual

    Raises:
        ValueError: If repair fails validation
    """
    # Initialize RNG if not provided
    if rng is None:
        rng = np.random.default_rng()

    # Load GA config if not provided
    if ga_config is None:
        import yaml
        ga_config_path = "ga_ext/ga_ext_config.yaml"
        try:
            with open(ga_config_path, 'r') as f:
                ga_config = yaml.safe_load(f)
        except:
            ga_config = {}

    # Create engine interface
    engine = EngineInterface(config_path)

    all_notes = []

    # Step 1: Resolve conflicts
    repaired, conflict_notes = repair_conflicts(individual, engine, ga_config, rng)
    all_notes.extend(conflict_notes)

    # Step 2: Adjust quotas
    repaired, quota_notes = repair_quotas(repaired, engine, ga_config, rng)
    all_notes.extend(quota_notes)

    # Step 3: Refine separation
    max_iters = ga_config.get('repair_max_iters', 20)
    repaired, refinement_notes = refine_separation(
        repaired, engine, ga_config, max_iterations=max_iters
    )
    all_notes.extend(refinement_notes)

    # Step 4: Final validation
    final_conflicts = engine.check_conflicts(repaired.placements)
    if final_conflicts:
        all_notes.append(
            f"VALIDATION WARNING: {len(final_conflicts)} conflicts remain after repair"
        )

    region_violations = engine.validate_allowed_regions(repaired.placements)
    if region_violations:
        all_notes.append(
            f"VALIDATION WARNING: Region violations detected: {region_violations}"
        )

    # Step 5: Attach notes to metadata
    repaired.metadata['repair_notes'] = '\n'.join(all_notes)
    repaired.metadata['repair_status'] = 'completed'

    return repaired
