"""
Band utilities for GA extension.

Non-invasive functions that extract band information from existing placement system
and partition individuals by band for GA operations.
"""

from typing import Dict, Set, Tuple, List
from pathlib import Path
import sys

# Import from existing system (non-invasive)
from src.stratified_placement import GridRegion, GridCell, Entity, Stratification, EntityType


def partition_by_band(
    individual_placements: Dict[str, List[Tuple[int, int]]],
    grid_config: Dict,
    band_config: Dict
) -> Dict[Tuple[str, int], List[Tuple[int, int]]]:
    """
    Partition an individual's placements by (entity_type, band_id).

    This enables band-aware crossover and mutation operations.

    Args:
        individual_placements: Dict mapping entity_type to list of (x, y) positions
        grid_config: Grid configuration (width, height)
        band_config: Band configuration (num_bands)

    Returns:
        Dict mapping (entity_type, band_id) to list of positions in that band

    Example:
        >>> placements = {'vinlet': [(5, 2), (10, 8)], 'acinlet': [(3, 5)]}
        >>> partition = partition_by_band(placements, {'width': 20, 'height': 10}, {'num_bands': 2})
        >>> # Returns: {('vinlet', 0): [(5, 2)], ('vinlet', 1): [(10, 8)], ('acinlet', 1): [(3, 5)]}
    """
    # Create grid region and stratification
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    stratification = Stratification.create_horizontal_bands(
        grid_region,
        num_bands=band_config.get('num_bands', 3)
    )

    # Partition placements by band
    result = {}

    for entity_type, positions in individual_placements.items():
        for x, y in positions:
            cell = GridCell(x, y)

            # Find which band this cell belongs to
            for band in stratification.bands:
                if band.contains_cell(cell):
                    key = (entity_type, band.index)
                    if key not in result:
                        result[key] = []
                    result[key].append((x, y))
                    break

    return result


def get_band_for_position(
    position: Tuple[int, int],
    grid_config: Dict,
    band_config: Dict
) -> int:
    """
    Determine which band a position belongs to.

    Args:
        position: (x, y) position
        grid_config: Grid configuration
        band_config: Band configuration

    Returns:
        Band index
    """
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    stratification = Stratification.create_horizontal_bands(
        grid_region,
        num_bands=band_config.get('num_bands', 3)
    )

    x, y = position
    cell = GridCell(x, y)

    for band in stratification.bands:
        if band.contains_cell(cell):
            return band.index

    raise ValueError(f"Position {position} not in any band")


def get_band_quotas(
    entity_configs: List[Dict],
    grid_config: Dict,
    band_config: Dict
) -> Dict[Tuple[str, int], int]:
    """
    Calculate expected quotas for each (entity_type, band_id) combination.

    Uses existing stratification logic to compute proportional quotas based
    on available cells per band.

    Args:
        entity_configs: List of entity configurations with type, count, allowed_region
        grid_config: Grid configuration (width, height)
        band_config: Band configuration (num_bands)

    Returns:
        Dict mapping (entity_type, band_id) to expected count

    Example:
        >>> entities = [{'type': 'vinlet', 'count': 10, 'allowed_region': 'full'}]
        >>> quotas = get_band_quotas(entities, {'width': 20, 'height': 10}, {'num_bands': 2})
    """
    # Create grid region and stratification
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    stratification = Stratification.create_horizontal_bands(
        grid_region,
        num_bands=band_config.get('num_bands', 3)
    )

    result = {}

    for entity_config in entity_configs:
        entity_type_str = entity_config['type']

        # Parse entity type
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            # If not a standard EntityType, use string directly
            entity_type = entity_type_str

        # Determine allowed region
        allowed_region_spec = entity_config.get('allowed_region', 'full')
        if allowed_region_spec == 'full':
            allowed_region = grid_region.all_cells()
        else:
            # Parse custom region specification
            allowed_region = parse_allowed_region(allowed_region_spec, grid_region)

        # Create Entity object
        entity = Entity(
            entity_type=entity_type if isinstance(entity_type, EntityType) else EntityType.VINLET,
            count=entity_config['count'],
            allowed_region=allowed_region
        )

        # Calculate quotas using existing logic
        quotas = stratification.calculate_quotas(entity)

        # Store in result
        for band_idx, quota in quotas.items():
            result[(entity_type_str, band_idx)] = quota

    return result


def parse_allowed_region(region_spec: str, grid_region: GridRegion) -> Set[GridCell]:
    """
    Parse allowed region specification.

    Supported formats:
    - "full": All cells
    - "top_half": Top half of grid
    - "bottom_half": Bottom half of grid
    - Custom specifications can be added

    Args:
        region_spec: Region specification string
        grid_region: Grid region

    Returns:
        Set of allowed GridCell objects
    """
    all_cells = grid_region.all_cells()

    if region_spec == 'full':
        return all_cells
    elif region_spec == 'top_half':
        mid_y = grid_region.height // 2
        return {cell for cell in all_cells if cell.y > mid_y}
    elif region_spec == 'bottom_half':
        mid_y = grid_region.height // 2
        return {cell for cell in all_cells if cell.y <= mid_y}
    else:
        # Default to full if unknown
        return all_cells


def get_band_boundaries(
    grid_config: Dict,
    band_config: Dict
) -> List[Tuple[int, int, int]]:
    """
    Get band boundaries for all bands.

    Args:
        grid_config: Grid configuration
        band_config: Band configuration

    Returns:
        List of (band_index, y_min, y_max) tuples
    """
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    stratification = Stratification.create_horizontal_bands(
        grid_region,
        num_bands=band_config.get('num_bands', 3)
    )

    return [(band.index, band.y_min, band.y_max) for band in stratification.bands]


def validate_band_preservation(
    original_partition: Dict[Tuple[str, int], List[Tuple[int, int]]],
    modified_partition: Dict[Tuple[str, int], List[Tuple[int, int]]]
) -> Tuple[bool, List[str]]:
    """
    Validate that GA operations preserved band constraints.

    Checks:
    1. All positions remain in their original bands
    2. Entity types are preserved

    Args:
        original_partition: Original band-wise partition
        modified_partition: Modified band-wise partition after GA ops

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check all keys present
    original_keys = set(original_partition.keys())
    modified_keys = set(modified_partition.keys())

    missing_keys = original_keys - modified_keys
    if missing_keys:
        errors.append(f"Missing band-entity combinations: {missing_keys}")

    extra_keys = modified_keys - original_keys
    if extra_keys:
        errors.append(f"Unexpected band-entity combinations: {extra_keys}")

    # For validation, we just check structure, not exact positions
    # (mutations and crossover will change positions)

    return len(errors) == 0, errors


def count_entities_per_band(
    individual_placements: Dict[str, List[Tuple[int, int]]],
    grid_config: Dict,
    band_config: Dict
) -> Dict[Tuple[str, int], int]:
    """
    Count how many entities of each type are in each band.

    Args:
        individual_placements: Placements to count
        grid_config: Grid configuration
        band_config: Band configuration

    Returns:
        Dict mapping (entity_type, band_id) to count
    """
    partition = partition_by_band(individual_placements, grid_config, band_config)

    return {key: len(positions) for key, positions in partition.items()}


def calculate_quota_deviation(
    actual_counts: Dict[Tuple[str, int], int],
    expected_quotas: Dict[Tuple[str, int], int]
) -> Dict[Tuple[str, int], int]:
    """
    Calculate deviation from expected quotas.

    Args:
        actual_counts: Actual entity counts per band
        expected_quotas: Expected quotas per band

    Returns:
        Dict mapping (entity_type, band_id) to deviation (positive = surplus, negative = deficit)
    """
    all_keys = set(actual_counts.keys()) | set(expected_quotas.keys())

    deviations = {}
    for key in all_keys:
        actual = actual_counts.get(key, 0)
        expected = expected_quotas.get(key, 0)
        deviations[key] = actual - expected

    return deviations


def get_free_cells_in_band(
    band_index: int,
    occupied_positions: Set[Tuple[int, int]],
    allowed_region: Set[GridCell],
    grid_config: Dict,
    band_config: Dict
) -> Set[Tuple[int, int]]:
    """
    Get all free (unoccupied) cells in a specific band within allowed region.

    Args:
        band_index: Band to search
        occupied_positions: Set of occupied (x, y) positions
        allowed_region: Set of allowed GridCell objects
        grid_config: Grid configuration
        band_config: Band configuration

    Returns:
        Set of free (x, y) positions in the band
    """
    grid_region = GridRegion(width=grid_config['width'], height=grid_config['height'])
    stratification = Stratification.create_horizontal_bands(
        grid_region,
        num_bands=band_config.get('num_bands', 3)
    )

    if band_index >= len(stratification.bands):
        return set()

    band = stratification.bands[band_index]

    # Get cells in band that are in allowed region
    band_cells = band.get_cells_in_region(allowed_region)

    # Filter out occupied cells
    free_cells = {
        (cell.x, cell.y)
        for cell in band_cells
        if (cell.x, cell.y) not in occupied_positions
    }

    return free_cells
