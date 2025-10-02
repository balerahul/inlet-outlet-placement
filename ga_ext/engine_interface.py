"""
Engine interface for GA extension.

Non-invasive wrapper around existing PlacementEngine functionality.
Provides utility methods for repair and refinement without modifying existing code.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path
import math

# Non-invasive imports from existing system
from src.stratified_placement import (
    GridCell, GridRegion, Entity, EntityType, Stratification, PlacementEngine, NormalizedPoint
)
from src.config_loader import load_config, create_entities_from_config, parse_allowed_region


class EngineInterface:
    """
    Non-invasive interface to existing PlacementEngine capabilities.

    This class wraps existing functionality to support GA repair and refinement
    operations without modifying any existing source code.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize engine interface by loading configuration.

        Args:
            config_path: Path to main configuration file
        """
        # Load configuration
        self.config = load_config(config_path)

        # Create grid region
        grid_config = self.config.get('grid', {})
        self.grid_region = GridRegion(
            width=grid_config.get('width', 20),
            height=grid_config.get('height', 10)
        )

        # Create entities
        self.entities = create_entities_from_config(self.config, self.grid_region)
        self.entity_map = {e.entity_type.value: e for e in self.entities}

        # Create stratification
        stratification_config = self.config.get('stratification', {})
        num_bands = stratification_config.get('num_bands', 3)
        self.stratification = Stratification.create_horizontal_bands(
            self.grid_region, num_bands
        )

        # Get optimization parameters
        opt_config = self.config.get('optimization', {})
        self.random_seed = opt_config.get('random_seed', 0)

        # Get separation parameters
        sep_config = self.config.get('separation', {})
        self.cross_entity_radius = sep_config.get('cross_entity_radius', 1.0)

        # Get anisotropy parameter
        self.anisotropy_y = stratification_config.get('anisotropy_y', 1.0)

    def check_conflicts(self, placements: Dict[str, List[Tuple[int, int]]]) -> List[Tuple[int, int]]:
        """
        Detect position conflicts (multiple entities at same cell).

        Args:
            placements: Dictionary mapping entity_type to list of (x, y) positions

        Returns:
            List of (x, y) positions with conflicts (multiple entities)
        """
        position_count = {}

        for entity_type, positions in placements.items():
            for pos in positions:
                position_count[pos] = position_count.get(pos, 0) + 1

        # Return positions with count > 1
        conflicts = [pos for pos, count in position_count.items() if count > 1]
        return conflicts

    def validate_allowed_regions(self, placements: Dict[str, List[Tuple[int, int]]]) -> Dict[str, List[Tuple[int, int]]]:
        """
        Check if all placements are within their allowed regions.

        Args:
            placements: Dictionary mapping entity_type to list of (x, y) positions

        Returns:
            Dictionary mapping entity_type to list of out-of-region positions
        """
        violations = {}

        for entity_type, positions in placements.items():
            if entity_type not in self.entity_map:
                continue

            entity = self.entity_map[entity_type]
            allowed_cells = {(cell.x, cell.y) for cell in entity.allowed_region}

            out_of_region = [pos for pos in positions if pos not in allowed_cells]

            if out_of_region:
                violations[entity_type] = out_of_region

        return violations

    def calculate_min_distances(
        self,
        placements: Dict[str, List[Tuple[int, int]]],
        anisotropy_y: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate minimum separation distance for each entity type.

        Uses anisotropic distance metric (emphasizes Y-axis separation).

        Args:
            placements: Dictionary mapping entity_type to list of (x, y) positions
            anisotropy_y: Y-axis weighting factor (default: from config)

        Returns:
            Dictionary mapping entity_type to minimum distance
        """
        if anisotropy_y is None:
            anisotropy_y = self.anisotropy_y

        min_distances = {}

        for entity_type, positions in placements.items():
            if len(positions) < 2:
                min_distances[entity_type] = float('inf')
                continue

            min_dist = float('inf')

            # Check all pairs
            for i, pos1 in enumerate(positions):
                for pos2 in positions[i+1:]:
                    dist = self._anisotropic_distance(pos1, pos2, anisotropy_y)
                    min_dist = min(min_dist, dist)

            min_distances[entity_type] = min_dist

        return min_distances

    def calculate_cross_entity_min_distance(
        self,
        placements: Dict[str, List[Tuple[int, int]]],
        anisotropy_y: Optional[float] = None
    ) -> float:
        """
        Calculate minimum distance between different entity types.

        Args:
            placements: Dictionary mapping entity_type to list of (x, y) positions
            anisotropy_y: Y-axis weighting factor (default: from config)

        Returns:
            Minimum cross-entity distance
        """
        if anisotropy_y is None:
            anisotropy_y = self.anisotropy_y

        min_cross_dist = float('inf')
        entity_types = list(placements.keys())

        # Check all pairs of different entity types
        for i, type_a in enumerate(entity_types):
            for type_b in entity_types[i+1:]:
                for pos_a in placements[type_a]:
                    for pos_b in placements[type_b]:
                        dist = self._anisotropic_distance(pos_a, pos_b, anisotropy_y)
                        min_cross_dist = min(min_cross_dist, dist)

        return min_cross_dist

    def suggest_relocation(
        self,
        entity_type: str,
        current_pos: Tuple[int, int],
        band_id: int,
        occupied_positions: Set[Tuple[int, int]],
        avoid_positions: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Suggest best free cell in band for relocation.

        Uses farthest-point logic to maximize separation from occupied cells.

        Args:
            entity_type: Type of entity to relocate
            current_pos: Current position (to be replaced)
            band_id: Band index to search within
            occupied_positions: Set of all occupied positions
            avoid_positions: Additional positions to avoid (optional)

        Returns:
            Best free position (x, y) or None if no free cells available
        """
        if entity_type not in self.entity_map:
            return None

        entity = self.entity_map[entity_type]

        # Get band
        if band_id >= len(self.stratification.bands):
            return None

        band = self.stratification.bands[band_id]

        # Get cells in band within allowed region
        band_cells = band.get_cells_in_region(entity.allowed_region)

        # Filter out occupied cells
        all_occupied = occupied_positions.copy()
        if avoid_positions:
            all_occupied.update(avoid_positions)

        free_cells = [
            (cell.x, cell.y)
            for cell in band_cells
            if (cell.x, cell.y) not in all_occupied
        ]

        if not free_cells:
            return None

        # If only one free cell, return it
        if len(free_cells) == 1:
            return free_cells[0]

        # Find cell farthest from all occupied positions
        best_cell = None
        best_min_dist = -1

        for candidate in free_cells:
            # Calculate minimum distance to any occupied cell
            min_dist = float('inf')
            for occ_pos in occupied_positions:
                if occ_pos == current_pos:
                    # Don't consider the position we're replacing
                    continue
                dist = self._anisotropic_distance(candidate, occ_pos, self.anisotropy_y)
                min_dist = min(min_dist, dist)

            # Track best candidate (maximize minimum distance)
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_cell = candidate

        return best_cell

    def get_free_cells_in_band(
        self,
        band_id: int,
        entity_type: str,
        occupied_positions: Set[Tuple[int, int]]
    ) -> Set[Tuple[int, int]]:
        """
        Get all free cells in a band within allowed region for entity type.

        Args:
            band_id: Band index
            entity_type: Type of entity
            occupied_positions: Set of occupied positions

        Returns:
            Set of free (x, y) positions
        """
        if entity_type not in self.entity_map:
            return set()

        if band_id >= len(self.stratification.bands):
            return set()

        entity = self.entity_map[entity_type]
        band = self.stratification.bands[band_id]

        # Get cells in band within allowed region
        band_cells = band.get_cells_in_region(entity.allowed_region)

        # Filter out occupied
        free_cells = {
            (cell.x, cell.y)
            for cell in band_cells
            if (cell.x, cell.y) not in occupied_positions
        }

        return free_cells

    def _anisotropic_distance(
        self,
        pos1: Tuple[int, int],
        pos2: Tuple[int, int],
        anisotropy_y: float
    ) -> float:
        """
        Calculate anisotropic distance between two positions.

        Uses normalized coordinates and Y-axis weighting.

        Args:
            pos1: First position (x, y)
            pos2: Second position (x, y)
            anisotropy_y: Y-axis weighting factor

        Returns:
            Weighted distance
        """
        # Convert to grid cells
        cell1 = GridCell(pos1[0], pos1[1])
        cell2 = GridCell(pos2[0], pos2[1])

        # Normalize
        p1 = self.grid_region.normalize_cell(cell1)
        p2 = self.grid_region.normalize_cell(cell2)

        # Calculate anisotropic distance
        dx = p1.x - p2.x
        dy = (p1.y - p2.y) * anisotropy_y

        return math.sqrt(dx*dx + dy*dy)

    def get_band_id_for_position(self, pos: Tuple[int, int]) -> int:
        """
        Determine which band a position belongs to.

        Args:
            pos: Position (x, y)

        Returns:
            Band index
        """
        cell = GridCell(pos[0], pos[1])

        for band in self.stratification.bands:
            if band.contains_cell(cell):
                return band.index

        raise ValueError(f"Position {pos} not in any band")

    def get_grid_config(self) -> Dict[str, int]:
        """Get grid configuration."""
        return {
            'width': self.grid_region.width,
            'height': self.grid_region.height
        }

    def get_band_config(self) -> Dict[str, int]:
        """Get band configuration."""
        return {
            'num_bands': len(self.stratification.bands)
        }

    def get_entity_configs(self) -> List[Dict[str, Any]]:
        """
        Get entity configurations for quota calculation.

        Returns:
            List of entity config dictionaries
        """
        configs = []

        for entity in self.entities:
            configs.append({
                'type': entity.entity_type.value,
                'count': entity.count,
                'allowed_region': 'full',  # Simplified - actual regions are in entity.allowed_region
                'intra_radius': entity.intra_radius
            })

        return configs
