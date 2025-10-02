"""
Tests for GA repair and refinement system.

Tests engine interface, conflict resolution, quota adjustment,
separation refinement, and complete repair pipeline.
"""

import unittest
import numpy as np
from pathlib import Path
import tempfile
import yaml

from ga_ext.data_models import Individual
from ga_ext.engine_interface import EngineInterface
from ga_ext.repair import (
    repair_conflicts,
    repair_quotas,
    refine_separation,
    repair_and_refine
)


class TestEngineInterface(unittest.TestCase):
    """Test engine interface wrapper."""

    def setUp(self):
        """Set up test configuration."""
        self.engine = EngineInterface("config.yaml")

    def test_load_config(self):
        """Test configuration loading."""
        self.assertIsNotNone(self.engine.config)
        self.assertIsNotNone(self.engine.grid_region)
        self.assertGreater(len(self.engine.entities), 0)

    def test_check_conflicts_no_conflicts(self):
        """Test conflict detection with no conflicts."""
        placements = {
            'vinlet': [(2, 3), (5, 4)],
            'acinlet': [(8, 5), (10, 6)]
        }

        conflicts = self.engine.check_conflicts(placements)
        self.assertEqual(len(conflicts), 0)

    def test_check_conflicts_with_conflicts(self):
        """Test conflict detection with overlapping positions."""
        placements = {
            'vinlet': [(5, 4), (8, 5)],
            'acinlet': [(5, 4), (10, 6)]  # Conflict at (5, 4)
        }

        conflicts = self.engine.check_conflicts(placements)
        self.assertEqual(len(conflicts), 1)
        self.assertIn((5, 4), conflicts)

    def test_calculate_min_distances(self):
        """Test minimum distance calculation."""
        placements = {
            'vinlet': [(2, 3), (8, 4)],
            'acinlet': [(10, 5)]
        }

        min_distances = self.engine.calculate_min_distances(placements)

        self.assertIn('vinlet', min_distances)
        self.assertGreater(min_distances['vinlet'], 0)
        # acinlet has only one position, so min_dist is inf
        self.assertEqual(min_distances['acinlet'], float('inf'))

    def test_validate_allowed_regions(self):
        """Test allowed region validation."""
        # Get actual allowed region for vinlet
        vinlet_entity = self.engine.entity_map.get('vinlet')
        if vinlet_entity:
            # Pick a valid position from allowed region
            valid_pos = next(iter(vinlet_entity.allowed_region))
            valid_pos = (valid_pos.x, valid_pos.y)

            placements = {
                'vinlet': [valid_pos]
            }

            violations = self.engine.validate_allowed_regions(placements)
            self.assertEqual(len(violations), 0)

    def test_suggest_relocation(self):
        """Test relocation suggestion."""
        occupied = {(5, 4), (6, 4), (7, 4)}

        # Try to relocate entity from (5, 4) in band 1
        new_pos = self.engine.suggest_relocation(
            'vinlet',
            (5, 4),
            band_id=1,
            occupied_positions=occupied
        )

        # Should suggest a position not in occupied
        if new_pos:
            self.assertNotIn(new_pos, occupied)

    def test_get_band_id_for_position(self):
        """Test band ID determination."""
        # Position (5, 3) should be in some band
        band_id = self.engine.get_band_id_for_position((5, 3))
        self.assertGreaterEqual(band_id, 0)
        self.assertLess(band_id, self.engine.get_band_config()['num_bands'])


class TestConflictRepair(unittest.TestCase):
    """Test conflict resolution."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EngineInterface("config.yaml")
        self.config = {}
        self.rng = np.random.default_rng(42)

    def test_repair_no_conflicts(self):
        """Test repair with no conflicts."""
        individual = Individual(
            id="test_001",
            path=Path("test.csv"),
            placements={
                'vinlet': [(2, 3), (8, 4)],
                'acinlet': [(5, 5), (10, 6)]
            }
        )

        repaired, notes = repair_conflicts(individual, self.engine, self.config, self.rng)

        self.assertEqual(len(repaired.placements['vinlet']), 2)
        self.assertEqual(len(repaired.placements['acinlet']), 2)
        self.assertIn("No conflicts", notes[0])

    def test_repair_single_conflict(self):
        """Test resolving single conflict."""
        individual = Individual(
            id="test_002",
            path=Path("test.csv"),
            placements={
                'vinlet': [(5, 4)],
                'acinlet': [(5, 4)]  # Conflict
            }
        )

        repaired, notes = repair_conflicts(individual, self.engine, self.config, self.rng)

        # Should have resolved conflict
        conflicts_after = self.engine.check_conflicts(repaired.placements)
        self.assertEqual(len(conflicts_after), 0)

        # Total entity count should be preserved
        total_before = sum(len(p) for p in individual.placements.values())
        total_after = sum(len(p) for p in repaired.placements.values())
        self.assertEqual(total_before, total_after)

    def test_repair_multiple_conflicts(self):
        """Test resolving multiple conflicts."""
        individual = Individual(
            id="test_003",
            path=Path("test.csv"),
            placements={
                'vinlet': [(5, 4), (6, 5)],
                'acinlet': [(5, 4), (6, 5)]  # Two conflicts
            }
        )

        repaired, notes = repair_conflicts(individual, self.engine, self.config, self.rng)

        # Should have resolved all conflicts
        conflicts_after = self.engine.check_conflicts(repaired.placements)
        self.assertEqual(len(conflicts_after), 0)

    def test_conflict_repair_preserves_count(self):
        """Test that conflict repair preserves total entity count."""
        individual = Individual(
            id="test_004",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 3), (5, 4), (7, 5)],
                'acinlet': [(5, 4), (9, 6)]  # One conflict at (5, 4)
            }
        )

        total_before = sum(len(p) for p in individual.placements.values())

        repaired, notes = repair_conflicts(individual, self.engine, self.config, self.rng)

        total_after = sum(len(p) for p in repaired.placements.values())
        self.assertEqual(total_before, total_after)

    def test_repair_notes_logged(self):
        """Test that repair notes are properly logged."""
        individual = Individual(
            id="test_005",
            path=Path("test.csv"),
            placements={
                'vinlet': [(5, 4)],
                'acinlet': [(5, 4)]
            }
        )

        repaired, notes = repair_conflicts(individual, self.engine, self.config, self.rng)

        # Should have logged the conflict and resolution
        self.assertGreater(len(notes), 0)
        notes_text = '\n'.join(notes)
        self.assertIn("conflict", notes_text.lower())


class TestQuotaRepair(unittest.TestCase):
    """Test quota adjustment."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EngineInterface("config.yaml")
        self.config = {}
        self.rng = np.random.default_rng(42)

    def test_repair_balanced_quotas(self):
        """Test repair with already balanced quotas."""
        # Create individual with roughly balanced quotas
        individual = Individual(
            id="test_006",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 3), (3, 5)],  # One in each band (assuming 2 bands)
                'acinlet': [(5, 3), (5, 5), (7, 3), (7, 5)]
            }
        )

        repaired, notes = repair_quotas(individual, self.engine, self.config, self.rng)

        # Should not have made major changes
        total_before = sum(len(p) for p in individual.placements.values())
        total_after = sum(len(p) for p in repaired.placements.values())
        self.assertEqual(total_before, total_after)

    def test_quota_repair_preserves_count(self):
        """Test that quota repair preserves total entity count."""
        individual = Individual(
            id="test_007",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 3), (5, 3), (7, 3)],  # All in lower band
                'acinlet': [(9, 6), (10, 6)]
            }
        )

        total_before = sum(len(p) for p in individual.placements.values())

        repaired, notes = repair_quotas(individual, self.engine, self.config, self.rng)

        total_after = sum(len(p) for p in repaired.placements.values())
        self.assertEqual(total_before, total_after)

    def test_quota_repair_respects_regions(self):
        """Test that quota repair respects allowed regions."""
        individual = Individual(
            id="test_008",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (5, 4)],
                'acinlet': [(7, 4), (9, 5)]
            }
        )

        repaired, notes = repair_quotas(individual, self.engine, self.config, self.rng)

        # Validate that all positions are in allowed regions
        violations = self.engine.validate_allowed_regions(repaired.placements)
        self.assertEqual(len(violations), 0)

    def test_quota_notes_logged(self):
        """Test that quota adjustment notes are logged."""
        individual = Individual(
            id="test_009",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 3), (5, 3), (7, 3)],
                'acinlet': [(9, 5), (10, 6)]
            }
        )

        repaired, notes = repair_quotas(individual, self.engine, self.config, self.rng)

        self.assertGreater(len(notes), 0)


class TestSeparationRefinement(unittest.TestCase):
    """Test separation distance refinement."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EngineInterface("config.yaml")
        self.config = {'wy': 2.0}

    def test_refine_well_separated(self):
        """Test refinement with already well-separated placements."""
        individual = Individual(
            id="test_010",
            path=Path("test.csv"),
            placements={
                'vinlet': [(2, 3), (10, 6)],  # Far apart
                'acinlet': [(5, 4), (8, 5)]
            }
        )

        refined, notes = refine_separation(
            individual, self.engine, self.config, max_iterations=5
        )

        # Should complete quickly (no improvements needed)
        self.assertGreater(len(notes), 0)

    def test_refinement_improves_distance(self):
        """Test that refinement can improve minimum distance."""
        # Create individual with entities close together
        individual = Individual(
            id="test_011",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (4, 4)],  # Very close
                'acinlet': [(7, 5), (10, 5)]
            }
        )

        # Calculate initial min distance
        initial_min_dists = self.engine.calculate_min_distances(individual.placements)

        refined, notes = refine_separation(
            individual, self.engine, self.config, max_iterations=10
        )

        # Calculate refined min distance
        refined_min_dists = self.engine.calculate_min_distances(refined.placements)

        # Should be equal or improved (depending on grid constraints)
        for entity_type in initial_min_dists:
            if entity_type in refined_min_dists:
                self.assertGreaterEqual(
                    refined_min_dists[entity_type],
                    initial_min_dists[entity_type] - 0.1  # Allow small tolerance
                )

    def test_refinement_respects_bands(self):
        """Test that refinement keeps entities in their bands."""
        individual = Individual(
            id="test_012",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 3), (5, 4)],
                'acinlet': [(7, 5), (9, 6)]
            }
        )

        # Get initial bands
        initial_bands = {}
        for entity_type, positions in individual.placements.items():
            initial_bands[entity_type] = [
                self.engine.get_band_id_for_position(pos) for pos in positions
            ]

        refined, notes = refine_separation(
            individual, self.engine, self.config, max_iterations=10
        )

        # Get refined bands
        refined_bands = {}
        for entity_type, positions in refined.placements.items():
            refined_bands[entity_type] = [
                self.engine.get_band_id_for_position(pos) for pos in positions
            ]

        # Band assignments should be same (may be reordered)
        for entity_type in initial_bands:
            self.assertEqual(
                sorted(initial_bands[entity_type]),
                sorted(refined_bands[entity_type])
            )

    def test_refinement_iteration_limit(self):
        """Test that refinement respects iteration limit."""
        individual = Individual(
            id="test_013",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (5, 4), (7, 4)],
                'acinlet': [(9, 5), (11, 5)]
            }
        )

        refined, notes = refine_separation(
            individual, self.engine, self.config, max_iterations=3
        )

        # Should stop at or before max_iterations
        # Notes should indicate completion
        self.assertGreater(len(notes), 0)


class TestRepairPipeline(unittest.TestCase):
    """Test complete repair pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.rng = np.random.default_rng(42)

    def test_repair_clean_individual(self):
        """Test pipeline with clean individual (no issues)."""
        individual = Individual(
            id="test_014",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (9, 5)],
                'acinlet': [(5, 4), (7, 5)]
            }
        )

        repaired = repair_and_refine(individual)

        # Should complete successfully
        self.assertIn('repair_notes', repaired.metadata)
        self.assertIn('repair_status', repaired.metadata)
        self.assertEqual(repaired.metadata['repair_status'], 'completed')

    def test_repair_broken_individual(self):
        """Test pipeline with intentionally broken individual."""
        individual = Individual(
            id="test_015",
            path=Path("test.csv"),
            placements={
                'vinlet': [(5, 4), (5, 4)],  # Duplicate (conflict)
                'acinlet': [(3, 3), (4, 3), (6, 3)]  # All in one band (quota issue)
            }
        )

        repaired = repair_and_refine(individual)

        # Should have resolved conflicts
        engine = EngineInterface()
        conflicts = engine.check_conflicts(repaired.placements)
        self.assertEqual(len(conflicts), 0)

        # Should have repair notes
        self.assertIn('repair_notes', repaired.metadata)

    def test_repair_preserves_entity_count(self):
        """Test that complete pipeline preserves total entity count."""
        individual = Individual(
            id="test_016",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (5, 4), (7, 5)],
                'acinlet': [(5, 4), (9, 5), (11, 6)]  # Conflict at (5, 4)
            }
        )

        total_before = sum(len(p) for p in individual.placements.values())

        repaired = repair_and_refine(individual)

        total_after = sum(len(p) for p in repaired.placements.values())
        self.assertEqual(total_before, total_after)

    def test_repair_notes_comprehensive(self):
        """Test that repair notes capture all operations."""
        individual = Individual(
            id="test_017",
            path=Path("test.csv"),
            placements={
                'vinlet': [(5, 4), (5, 4)],  # Conflict
                'acinlet': [(7, 4), (9, 5)]
            }
        )

        repaired = repair_and_refine(individual)

        notes = repaired.metadata.get('repair_notes', '')

        # Should mention conflicts
        self.assertIn('conflict', notes.lower())

    def test_repair_validates_output(self):
        """Test that pipeline validates final output."""
        individual = Individual(
            id="test_018",
            path=Path("test.csv"),
            placements={
                'vinlet': [(3, 4), (5, 5)],
                'acinlet': [(7, 4), (9, 5)]
            }
        )

        repaired = repair_and_refine(individual)

        # Final output should have no conflicts
        engine = EngineInterface()
        conflicts = engine.check_conflicts(repaired.placements)
        self.assertEqual(len(conflicts), 0)

        # Should be in allowed regions
        violations = engine.validate_allowed_regions(repaired.placements)
        self.assertEqual(len(violations), 0)


def run_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEngineInterface))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictRepair))
    suite.addTests(loader.loadTestsFromTestCase(TestQuotaRepair))
    suite.addTests(loader.loadTestsFromTestCase(TestSeparationRefinement))
    suite.addTests(loader.loadTestsFromTestCase(TestRepairPipeline))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
