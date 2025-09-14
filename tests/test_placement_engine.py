"""
Tests for the placement engine and optimization
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from stratified_placement import (
    GridCell, GridRegion, Entity, EntityType, PlacementEngine,
    PlacementResult, euclidean_distance
)


class TestPlacementEngine(unittest.TestCase):
    """Test PlacementEngine functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.grid_region = GridRegion(10, 8)
        
        # Create entities similar to the original example
        supply_cells = {GridCell(x, y) for x in range(1, 11) for y in range(3, 7)}
        exhaust_cells = self.grid_region.all_cells() - supply_cells
        
        self.entities = [
            Entity(EntityType.VINLET, 2, supply_cells, intra_radius=1.0),
            Entity(EntityType.VOUTLET, 3, exhaust_cells, intra_radius=1.0),
            Entity(EntityType.ACINLET, 4, supply_cells, intra_radius=1.0),
            Entity(EntityType.ACOUTLET, 5, exhaust_cells, intra_radius=1.0)
        ]
        
        self.engine = PlacementEngine(
            grid_region=self.grid_region,
            entities=self.entities,
            cross_entity_radius=1.0,
            random_seed=42
        )
    
    def test_engine_initialization(self):
        """Test that engine initializes correctly"""
        self.assertEqual(self.engine.grid_region, self.grid_region)
        self.assertEqual(len(self.engine.entities), 4)
        self.assertEqual(self.engine.cross_entity_radius, 1.0)
        self.assertEqual(self.engine.random_seed, 42)
    
    def test_place_all_entities(self):
        """Test complete placement process"""
        result = self.engine.place_all_entities()
        
        # Check that result is valid
        self.assertIsInstance(result, PlacementResult)
        
        # Check that all entities have placements
        expected_entity_types = {EntityType.VINLET, EntityType.VOUTLET, 
                               EntityType.ACINLET, EntityType.ACOUTLET}
        self.assertEqual(set(result.placements.keys()), expected_entity_types)
        
        # Check that placement counts match entity counts
        for entity in self.entities:
            placed_count = len(result.placements[entity.entity_type])
            self.assertEqual(placed_count, entity.count)
    
    def test_placement_respects_regions(self):
        """Test that placements respect allowed regions"""
        result = self.engine.place_all_entities()
        
        for entity in self.entities:
            placements = result.placements[entity.entity_type]
            
            for placement in placements:
                self.assertIn(placement, entity.allowed_region,
                            f"Placement {placement} not in allowed region for {entity.entity_type}")
    
    def test_no_overlapping_placements(self):
        """Test that no two entities occupy the same cell"""
        result = self.engine.place_all_entities()
        
        all_placements = []
        for placements in result.placements.values():
            all_placements.extend(placements)
        
        # Check for duplicates
        unique_placements = set(all_placements)
        self.assertEqual(len(all_placements), len(unique_placements),
                        "Found overlapping placements")
    
    def test_farthest_point_sampling(self):
        """Test farthest point sampling method"""
        available_cells = [GridCell(1, 1), GridCell(1, 2), GridCell(2, 1), 
                          GridCell(2, 2), GridCell(3, 1)]
        
        # Sample 3 points
        sampled = self.engine._farthest_point_sampling(available_cells, 3)
        
        self.assertEqual(len(sampled), 3)
        self.assertTrue(all(cell in available_cells for cell in sampled))
        
        # Check that they are reasonably spread out
        min_distance = float('inf')
        for i, p1 in enumerate(sampled):
            for p2 in sampled[i+1:]:
                dist = euclidean_distance(p1, p2)
                min_distance = min(min_distance, dist)
        
        # Should have some reasonable minimum separation
        self.assertGreater(min_distance, 0)
    
    def test_reproducible_results(self):
        """Test that same seed produces same results"""
        result1 = self.engine.place_all_entities()
        
        # Create new engine with same seed
        engine2 = PlacementEngine(
            grid_region=self.grid_region,
            entities=self.entities,
            cross_entity_radius=1.0,
            random_seed=42  # Same seed
        )
        result2 = engine2.place_all_entities()
        
        # Results should be identical
        for entity_type in result1.placements:
            placements1 = sorted(result1.placements[entity_type], key=lambda c: (c.x, c.y))
            placements2 = sorted(result2.placements[entity_type], key=lambda c: (c.x, c.y))
            self.assertEqual(placements1, placements2)


class TestPlacementResult(unittest.TestCase):
    """Test PlacementResult functionality"""
    
    def test_placement_result_creation(self):
        """Test creating a placement result"""
        result = PlacementResult()
        
        self.assertEqual(len(result.placements), 0)
        self.assertEqual(len(result.metrics), 0)
        self.assertEqual(len(result.feasibility_notes), 0)
        self.assertEqual(len(result.quota_deviations), 0)
    
    def test_add_feasibility_note(self):
        """Test adding feasibility notes"""
        result = PlacementResult()
        
        result.add_feasibility_note("Test note 1")
        result.add_feasibility_note("Test note 2")
        
        self.assertEqual(len(result.feasibility_notes), 2)
        self.assertIn("Test note 1", result.feasibility_notes)
        self.assertIn("Test note 2", result.feasibility_notes)


class TestDistanceFunctions(unittest.TestCase):
    """Test distance calculation functions"""
    
    def test_euclidean_distance(self):
        """Test euclidean distance calculation"""
        cell1 = GridCell(0, 0)
        cell2 = GridCell(3, 4)
        
        distance = euclidean_distance(cell1, cell2)
        expected = 5.0  # 3-4-5 triangle
        
        self.assertAlmostEqual(distance, expected)
    
    def test_euclidean_distance_same_cell(self):
        """Test distance between same cell"""
        cell = GridCell(5, 3)
        distance = euclidean_distance(cell, cell)
        self.assertEqual(distance, 0.0)


if __name__ == '__main__':
    unittest.main()