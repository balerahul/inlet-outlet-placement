"""
Stratified Multi-Entity Placement System

Implements the full methodology from placement_plan.md for optimal placement
of multiple entity types on rectangular grids with stratification guarantees.
"""

import math
import random
from typing import List, Tuple, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class EntityType(Enum):
    """Entity types for HVAC components"""
    VINLET = "vinlet"
    VOUTLET = "voutlet" 
    ACINLET = "acinlet"
    ACOUTLET = "acoutlet"


@dataclass
class GridCell:
    """Represents a discrete grid cell with integer coordinates"""
    x: int
    y: int
    
    def __hash__(self) -> int:
        return hash((self.x, self.y))
    
    def __iter__(self):
        """Allow unpacking as tuple"""
        yield self.x
        yield self.y


@dataclass
class NormalizedPoint:
    """Normalized coordinates in [0,1] x [0,1] space"""
    x: float
    y: float
    
    def distance_to(self, other: 'NormalizedPoint', anisotropy_y: float = 1.0) -> float:
        """Calculate anisotropic distance with y-axis weighting"""
        dx = self.x - other.x
        dy = (self.y - other.y) * anisotropy_y
        return math.sqrt(dx*dx + dy*dy)


@dataclass
class Entity:
    """Entity definition with placement constraints"""
    entity_type: EntityType
    count: int
    allowed_region: Set[GridCell]
    intra_radius: float = 1.0  # Minimum distance between same entities
    color: str = "blue"  # For visualization
    
    def __post_init__(self):
        if self.count > len(self.allowed_region):
            raise ValueError(f"{self.entity_type.value} count ({self.count}) exceeds allowed region size ({len(self.allowed_region)})")


@dataclass
class GridRegion:
    """Rectangular grid with coordinate normalization capabilities"""
    width: int  # n in placement_plan.md
    height: int  # m in placement_plan.md
    
    def normalize_cell(self, cell: GridCell) -> NormalizedPoint:
        """Convert grid cell to normalized [0,1] coordinates"""
        return NormalizedPoint(
            x=(cell.x - 0.5) / self.width,
            y=(cell.y - 0.5) / self.height
        )
    
    def denormalize_point(self, point: NormalizedPoint) -> GridCell:
        """Convert normalized point back to grid cell"""
        return GridCell(
            x=round(point.x * self.width + 0.5),
            y=round(point.y * self.height + 0.5)
        )
    
    def all_cells(self) -> Set[GridCell]:
        """Generate all valid grid cells"""
        return {GridCell(x, y) for x in range(1, self.width + 1) 
                for y in range(1, self.height + 1)}


@dataclass
class Band:
    """Horizontal band for stratification"""
    y_min: int
    y_max: int
    index: int
    
    def contains_cell(self, cell: GridCell) -> bool:
        """Check if cell falls within this band"""
        return self.y_min <= cell.y <= self.y_max
    
    def get_cells_in_region(self, region: Set[GridCell]) -> Set[GridCell]:
        """Get all cells from region that fall within this band"""
        return {cell for cell in region if self.contains_cell(cell)}


@dataclass
class Stratification:
    """Manages band-based stratification of the grid"""
    bands: List[Band]
    grid_region: GridRegion
    
    @classmethod
    def create_horizontal_bands(cls, grid_region: GridRegion, num_bands: int) -> 'Stratification':
        """Create horizontal stratification bands"""
        if num_bands <= 0:
            raise ValueError("Number of bands must be positive")
        
        band_height = grid_region.height / num_bands
        bands = []
        
        for i in range(num_bands):
            y_min = max(1, round(i * band_height + 1))
            y_max = min(grid_region.height, round((i + 1) * band_height))
            bands.append(Band(y_min, y_max, i))
        
        return cls(bands, grid_region)
    
    def calculate_quotas(self, entity: Entity) -> Dict[int, int]:
        """Calculate per-band quotas for an entity based on available cells per band"""
        # Find which bands have cells in the entity's allowed region
        band_cell_counts = {}
        total_available = 0
        
        for band in self.bands:
            band_cells = band.get_cells_in_region(entity.allowed_region)
            count = len(band_cells)
            band_cell_counts[band.index] = count
            total_available += count
        
        if total_available == 0:
            return {band.index: 0 for band in self.bands}
        
        # Calculate quotas proportional to available cells in each band
        quotas = {}
        allocated_total = 0
        
        for band in self.bands:
            available_in_band = band_cell_counts[band.index]
            if available_in_band == 0:
                quotas[band.index] = 0
            else:
                # Proportional allocation
                quota = round(entity.count * available_in_band / total_available)
                quotas[band.index] = quota
                allocated_total += quota
        
        # Adjust for rounding errors
        quota_difference = entity.count - allocated_total
        if quota_difference != 0:
            # Find bands with available cells and adjust
            adjustable_bands = [band.index for band in self.bands 
                              if band_cell_counts[band.index] > 0]
            
            if adjustable_bands:
                for i in range(abs(quota_difference)):
                    band_idx = adjustable_bands[i % len(adjustable_bands)]
                    if quota_difference > 0:
                        quotas[band_idx] += 1
                    else:
                        quotas[band_idx] = max(0, quotas[band_idx] - 1)
        
        return quotas


@dataclass
class PlacementResult:
    """Result of placement operation"""
    placements: Dict[EntityType, List[GridCell]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    feasibility_notes: List[str] = field(default_factory=list)
    quota_deviations: Dict[EntityType, Dict[int, int]] = field(default_factory=dict)
    
    def add_feasibility_note(self, note: str):
        """Add a feasibility constraint note"""
        self.feasibility_notes.append(note)


class PlacementEngine:
    """Main engine implementing the three-phase stratified placement"""
    
    def __init__(self, 
                 grid_region: GridRegion,
                 entities: List[Entity],
                 cross_entity_radius: float = 1.0,
                 anisotropy_y: float = 1.0,
                 num_bands: Optional[int] = None,
                 random_seed: int = 0):
        """
        Initialize placement engine
        
        Args:
            grid_region: The grid to place entities on
            entities: List of entity definitions
            cross_entity_radius: Minimum distance between different entities
            anisotropy_y: Y-axis weighting for distance calculations (>1 emphasizes vertical separation)
            num_bands: Number of horizontal bands (defaults to max usable rows)
            random_seed: Random seed for reproducibility
        """
        self.grid_region = grid_region
        self.entities = entities
        self.cross_entity_radius = cross_entity_radius
        self.anisotropy_y = anisotropy_y
        self.random_seed = random_seed
        
        # Set default number of bands
        if num_bands is None:
            # Use the maximum number of distinct usable rows across all entities
            all_y_coords = set()
            for entity in entities:
                for cell in entity.allowed_region:
                    all_y_coords.add(cell.y)
            num_bands = len(all_y_coords)
        
        self.stratification = Stratification.create_horizontal_bands(grid_region, num_bands)
        
        # Initialize random seed
        random.seed(self.random_seed)
    
    def place_all_entities(self) -> PlacementResult:
        """
        Execute the full three-phase placement algorithm
        
        Returns:
            PlacementResult with all placements and metrics
        """
        result = PlacementResult()
        
        # Phase A: Normalize & Partition (already done in __init__)
        
        # Phase B: Initial Per-Entity Placement (Meet Quotas)
        self._phase_b_initial_placement(result)
        
        # Phase C: Joint Refinement (Blue-Noise Optimization)
        self._phase_c_joint_refinement(result)
        
        return result
    
    def _phase_b_initial_placement(self, result: PlacementResult):
        """Phase B: Band-aware initial placement to meet quotas"""
        # Track all occupied cells across entities
        all_occupied_cells = set()
        
        for entity in self.entities:
            quotas = self.stratification.calculate_quotas(entity)
            entity_placements = []
            
            for band in self.stratification.bands:
                band_cells = band.get_cells_in_region(entity.allowed_region)
                quota = quotas[band.index]
                
                if quota == 0:
                    continue
                
                # Filter out already occupied cells
                available_band_cells = [cell for cell in band_cells if cell not in all_occupied_cells]
                
                if len(available_band_cells) < quota:
                    # Need to borrow from adjacent bands or reduce quota
                    deficit = quota - len(available_band_cells)
                    result.add_feasibility_note(
                        f"{entity.entity_type.value} band {band.index} has deficit of {deficit}"
                    )
                    # Place all available cells in this band
                    band_placements = available_band_cells[:]
                else:
                    # Use farthest point sampling within the band
                    band_placements = self._farthest_point_sampling(
                        available_band_cells, quota, entity_placements
                    )
                
                entity_placements.extend(band_placements)
                # Mark these cells as occupied
                all_occupied_cells.update(band_placements)
            
            result.placements[entity.entity_type] = entity_placements
    
    def _phase_c_joint_refinement(self, result: PlacementResult):
        """Phase C: Blue-noise optimization with separation constraints"""
        optimizer = BlueNoiseOptimizer(
            self.grid_region,
            self.stratification,
            self.entities,
            self.cross_entity_radius,
            self.anisotropy_y
        )
        
        # Run optimization iterations
        optimizer.optimize_placements(result, max_iterations=100)
    
    def _farthest_point_sampling(self, 
                                available_cells: List[GridCell], 
                                count: int,
                                existing_placements: List[GridCell] = None) -> List[GridCell]:
        """
        Farthest point sampling within a subset, considering existing placements
        
        Args:
            available_cells: Cells to sample from
            count: Number of points to sample
            existing_placements: Already placed cells to maintain distance from
        """
        if count <= 0:
            return []
        
        if count >= len(available_cells):
            return available_cells[:]
        
        if not available_cells:
            return []
        
        # Remove any cells that are already occupied by other entities
        all_occupied = set()
        if existing_placements:
            all_occupied.update(existing_placements)
        
        # Filter available cells to exclude occupied ones
        free_cells = [cell for cell in available_cells if cell not in all_occupied]
        
        if not free_cells:
            return []
        
        if count >= len(free_cells):
            return free_cells[:]
        
        # Start with a random cell if no existing placements, otherwise start far from existing
        if not existing_placements:
            start_cell = random.choice(free_cells)
        else:
            # Find cell farthest from all existing placements
            def min_distance_to_existing(cell):
                return min(self._cell_distance(cell, existing) for existing in existing_placements)
            start_cell = max(free_cells, key=min_distance_to_existing)
        
        chosen = [start_cell]
        remaining = [cell for cell in free_cells if cell != start_cell]
        
        if not remaining:
            return chosen
        
        # Build distance map
        nearest_dist = {}
        for cell in remaining:
            nearest_dist[cell] = self._cell_distance(cell, start_cell)
        
        # Iteratively add farthest points
        while len(chosen) < count and remaining:
            # Find cell with maximum distance to nearest chosen point
            next_cell = max(remaining, key=lambda cell: nearest_dist[cell])
            chosen.append(next_cell)
            remaining.remove(next_cell)
            
            # Update distances for remaining cells
            for cell in remaining:
                dist_to_new = self._cell_distance(cell, next_cell)
                if dist_to_new < nearest_dist[cell]:
                    nearest_dist[cell] = dist_to_new
        
        return chosen
    
    def _cell_distance(self, cell1: GridCell, cell2: GridCell) -> float:
        """Calculate anisotropic distance between two cells"""
        p1 = self.grid_region.normalize_cell(cell1)
        p2 = self.grid_region.normalize_cell(cell2)
        return p1.distance_to(p2, self.anisotropy_y)


def euclidean_distance(cell1: GridCell, cell2: GridCell) -> float:
    """Simple euclidean distance between grid cells"""
    return math.sqrt((cell1.x - cell2.x)**2 + (cell1.y - cell2.y)**2)


class BlueNoiseOptimizer:
    """Phase C optimizer implementing blue-noise refinement with separation constraints"""
    
    def __init__(self,
                 grid_region: GridRegion,
                 stratification: Stratification,
                 entities: List[Entity],
                 cross_entity_radius: float,
                 anisotropy_y: float):
        self.grid_region = grid_region
        self.stratification = stratification
        self.entities = entities
        self.cross_entity_radius = cross_entity_radius
        self.anisotropy_y = anisotropy_y
        self.entity_map = {e.entity_type: e for e in entities}
    
    def optimize_placements(self, result: PlacementResult, max_iterations: int = 100):
        """
        Perform iterative blue-noise optimization
        
        Uses local swaps and nudges within bands to improve separation distances
        while maintaining quota satisfaction and regional constraints.
        """
        for iteration in range(max_iterations):
            improvement_made = False
            
            # Try to improve intra-entity separations
            for entity in self.entities:
                if self._improve_intra_entity_separation(result, entity.entity_type):
                    improvement_made = True
            
            # Try to improve cross-entity separations
            if self._improve_cross_entity_separation(result):
                improvement_made = True
            
            # If no improvement was made, we've reached a local optimum
            if not improvement_made:
                break
        
        result.metrics['optimization_iterations'] = iteration + 1
    
    def _improve_intra_entity_separation(self, result: PlacementResult, entity_type: EntityType) -> bool:
        """Attempt to improve minimum intra-entity separation distance"""
        if entity_type not in result.placements:
            return False
        
        placements = result.placements[entity_type]
        if len(placements) < 2:
            return False
        
        entity = self.entity_map[entity_type]
        
        # Find the pair with minimum separation
        min_distance = float('inf')
        min_pair = None
        
        for i, p1 in enumerate(placements):
            for j, p2 in enumerate(placements[i+1:], i+1):
                dist = self._cell_distance(p1, p2)
                if dist < min_distance:
                    min_distance = dist
                    min_pair = (i, j)
        
        if min_pair is None or min_distance >= entity.intra_radius:
            return False
        
        # Try to move one of the points in the minimum pair
        i, j = min_pair
        improved = False
        
        # Try moving the first point
        if self._try_move_point_for_better_separation(result, entity_type, i):
            improved = True
        # Try moving the second point if first didn't work
        elif self._try_move_point_for_better_separation(result, entity_type, j):
            improved = True
        
        return improved
    
    def _improve_cross_entity_separation(self, result: PlacementResult) -> bool:
        """Attempt to improve minimum cross-entity separation distance"""
        entity_types = list(result.placements.keys())
        if len(entity_types) < 2:
            return False
        
        # Find the minimum cross-entity distance
        min_distance = float('inf')
        min_info = None
        
        for i, type1 in enumerate(entity_types):
            for type2 in entity_types[i+1:]:
                placements1 = result.placements[type1]
                placements2 = result.placements[type2]
                
                for idx1, p1 in enumerate(placements1):
                    for idx2, p2 in enumerate(placements2):
                        dist = self._cell_distance(p1, p2)
                        if dist < min_distance:
                            min_distance = dist
                            min_info = (type1, idx1, type2, idx2)
        
        if min_info is None or min_distance >= self.cross_entity_radius:
            return False
        
        type1, idx1, type2, idx2 = min_info
        
        # Try moving one of the conflicting points
        if self._try_move_point_for_better_separation(result, type1, idx1):
            return True
        elif self._try_move_point_for_better_separation(result, type2, idx2):
            return True
        
        return False
    
    def _try_move_point_for_better_separation(self, result: PlacementResult, 
                                            entity_type: EntityType, point_index: int) -> bool:
        """
        Try to move a specific point to improve separation while maintaining constraints
        
        Returns True if an improvement was made
        """
        placements = result.placements[entity_type]
        if point_index >= len(placements):
            return False
        
        current_cell = placements[point_index]
        entity = self.entity_map[entity_type]
        
        # Find which band this point is in
        current_band = None
        for band in self.stratification.bands:
            if band.contains_cell(current_cell):
                current_band = band
                break
        
        if current_band is None:
            return False
        
        # Get available cells in the same band within the allowed region
        band_cells = current_band.get_cells_in_region(entity.allowed_region)
        available_cells = [cell for cell in band_cells 
                          if cell != current_cell and cell not in placements]
        
        if not available_cells:
            return False
        
        best_cell = None
        best_improvement = 0
        
        for candidate_cell in available_cells:
            improvement = self._calculate_separation_improvement(
                result, entity_type, point_index, current_cell, candidate_cell
            )
            
            if improvement > best_improvement:
                best_improvement = improvement
                best_cell = candidate_cell
        
        if best_cell is not None:
            # Make the move
            placements[point_index] = best_cell
            return True
        
        return False
    
    def _calculate_separation_improvement(self, result: PlacementResult,
                                        entity_type: EntityType, point_index: int,
                                        old_cell: GridCell, new_cell: GridCell) -> float:
        """
        Calculate the improvement in separation distances from moving a point
        
        Returns positive value if the move improves separations
        """
        placements = result.placements[entity_type]
        entity = self.entity_map[entity_type]
        
        old_min_distances = []
        new_min_distances = []
        
        # Calculate distances to other points of the same entity
        for i, other_cell in enumerate(placements):
            if i == point_index:
                continue
            
            old_dist = self._cell_distance(old_cell, other_cell)
            new_dist = self._cell_distance(new_cell, other_cell)
            
            old_min_distances.append(old_dist)
            new_min_distances.append(new_dist)
        
        # Calculate distances to points of other entities
        for other_type, other_placements in result.placements.items():
            if other_type == entity_type:
                continue
            
            for other_cell in other_placements:
                old_dist = self._cell_distance(old_cell, other_cell)
                new_dist = self._cell_distance(new_cell, other_cell)
                
                old_min_distances.append(old_dist)
                new_min_distances.append(new_dist)
        
        # Calculate improvement based on minimum distances
        if old_min_distances and new_min_distances:
            old_min = min(old_min_distances)
            new_min = min(new_min_distances)
            return new_min - old_min
        
        return 0
    
    def _cell_distance(self, cell1: GridCell, cell2: GridCell) -> float:
        """Calculate anisotropic distance between cells"""
        p1 = self.grid_region.normalize_cell(cell1)
        p2 = self.grid_region.normalize_cell(cell2)
        return p1.distance_to(p2, self.anisotropy_y)