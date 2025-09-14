"""
Tests for stratification and quota system
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from stratified_placement import (
    GridCell, GridRegion, Entity, EntityType, Stratification,
    NormalizedPoint, Band
)


class TestGridCell(unittest.TestCase):
    """Test GridCell functionality"""
    
    def test_grid_cell_creation(self):
        cell = GridCell(5, 3)
        self.assertEqual(cell.x, 5)
        self.assertEqual(cell.y, 3)
    
    def test_grid_cell_hash(self):
        cell1 = GridCell(5, 3)
        cell2 = GridCell(5, 3)
        cell3 = GridCell(3, 5)
        
        self.assertEqual(hash(cell1), hash(cell2))
        self.assertNotEqual(hash(cell1), hash(cell3))
    
    def test_grid_cell_unpacking(self):
        cell = GridCell(5, 3)
        x, y = cell
        self.assertEqual(x, 5)
        self.assertEqual(y, 3)


class TestGridRegion(unittest.TestCase):
    """Test GridRegion functionality"""
    
    def setUp(self):
        self.region = GridRegion(10, 8)
    
    def test_grid_region_creation(self):
        self.assertEqual(self.region.width, 10)
        self.assertEqual(self.region.height, 8)
    
    def test_normalize_cell(self):
        cell = GridCell(5, 4)
        normalized = self.region.normalize_cell(cell)
        
        self.assertAlmostEqual(normalized.x, (5 - 0.5) / 10)
        self.assertAlmostEqual(normalized.y, (4 - 0.5) / 8)
    
    def test_denormalize_point(self):
        point = NormalizedPoint(0.45, 0.4375)
        cell = self.region.denormalize_point(point)
        
        self.assertEqual(cell.x, 5)
        self.assertEqual(cell.y, 4)
    
    def test_all_cells(self):
        cells = self.region.all_cells()
        self.assertEqual(len(cells), 10 * 8)
        
        # Check that all coordinates are within bounds
        for cell in cells:
            self.assertTrue(1 <= cell.x <= 10)
            self.assertTrue(1 <= cell.y <= 8)


class TestNormalizedPoint(unittest.TestCase):
    """Test NormalizedPoint functionality"""
    
    def test_distance_isotropic(self):
        p1 = NormalizedPoint(0.0, 0.0)
        p2 = NormalizedPoint(0.3, 0.4)
        
        distance = p1.distance_to(p2, anisotropy_y=1.0)
        expected = (0.3**2 + 0.4**2)**0.5
        
        self.assertAlmostEqual(distance, expected)
    
    def test_distance_anisotropic(self):
        p1 = NormalizedPoint(0.0, 0.0)
        p2 = NormalizedPoint(0.3, 0.4)
        
        distance = p1.distance_to(p2, anisotropy_y=2.0)
        expected = (0.3**2 + (0.4 * 2.0)**2)**0.5
        
        self.assertAlmostEqual(distance, expected)


class TestBand(unittest.TestCase):
    """Test Band functionality"""
    
    def setUp(self):
        self.band = Band(y_min=3, y_max=5, index=1)
    
    def test_contains_cell(self):
        self.assertTrue(self.band.contains_cell(GridCell(1, 3)))
        self.assertTrue(self.band.contains_cell(GridCell(1, 4)))
        self.assertTrue(self.band.contains_cell(GridCell(1, 5)))
        self.assertFalse(self.band.contains_cell(GridCell(1, 2)))
        self.assertFalse(self.band.contains_cell(GridCell(1, 6)))
    
    def test_get_cells_in_region(self):
        region = {GridCell(1, 2), GridCell(1, 3), GridCell(1, 4), 
                 GridCell(1, 5), GridCell(1, 6)}
        
        band_cells = self.band.get_cells_in_region(region)
        expected = {GridCell(1, 3), GridCell(1, 4), GridCell(1, 5)}
        
        self.assertEqual(band_cells, expected)


class TestStratification(unittest.TestCase):
    """Test Stratification functionality"""
    
    def setUp(self):
        self.grid_region = GridRegion(10, 8)
        self.stratification = Stratification.create_horizontal_bands(
            self.grid_region, 4
        )
    
    def test_create_horizontal_bands(self):
        self.assertEqual(len(self.stratification.bands), 4)
        
        # Check that bands cover the entire height
        all_y_coords = set()
        for band in self.stratification.bands:
            for y in range(band.y_min, band.y_max + 1):
                all_y_coords.add(y)
        
        expected_y_coords = set(range(1, 9))  # 1 to 8 inclusive
        self.assertEqual(all_y_coords, expected_y_coords)
    
    def test_calculate_quotas_even_distribution(self):
        # Create entity with count divisible by number of bands
        allowed_region = self.grid_region.all_cells()
        entity = Entity(EntityType.VINLET, 8, allowed_region)
        
        quotas = self.stratification.calculate_quotas(entity)
        
        # Should have 2 entities per band (8 / 4 = 2)
        for band_idx, quota in quotas.items():
            self.assertEqual(quota, 2)
    
    def test_calculate_quotas_uneven_distribution(self):
        # Create entity with count not divisible by number of bands
        allowed_region = self.grid_region.all_cells()
        entity = Entity(EntityType.VINLET, 7, allowed_region)
        
        quotas = self.stratification.calculate_quotas(entity)
        
        # Should distribute 7 entities across 4 bands
        total_quota = sum(quotas.values())
        self.assertEqual(total_quota, 7)
        
        # First 3 bands should get 2, last band should get 1 (or similar distribution)
        quota_values = list(quotas.values())
        self.assertTrue(all(1 <= q <= 2 for q in quota_values))


class TestEntity(unittest.TestCase):
    """Test Entity functionality"""
    
    def setUp(self):
        self.allowed_region = {GridCell(1, 1), GridCell(1, 2), GridCell(2, 1)}
    
    def test_entity_creation_valid(self):
        entity = Entity(EntityType.VINLET, 2, self.allowed_region)
        
        self.assertEqual(entity.entity_type, EntityType.VINLET)
        self.assertEqual(entity.count, 2)
        self.assertEqual(entity.allowed_region, self.allowed_region)
        self.assertEqual(entity.intra_radius, 1.0)  # default
    
    def test_entity_creation_invalid_count(self):
        # Try to create entity with count exceeding region size
        with self.assertRaises(ValueError):
            Entity(EntityType.VINLET, 5, self.allowed_region)
    
    def test_entity_creation_with_custom_radius(self):
        entity = Entity(EntityType.VINLET, 2, self.allowed_region, intra_radius=2.5)
        self.assertEqual(entity.intra_radius, 2.5)


if __name__ == '__main__':
    unittest.main()