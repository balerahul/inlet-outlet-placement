"""
Tests for GA operations: band utilities, crossover, and mutation.
"""

import unittest
import numpy as np
from pathlib import Path

from ga_ext.data_models import Individual
from ga_ext.band_utils import (
    partition_by_band,
    get_band_for_position,
    count_entities_per_band,
    get_band_boundaries,
)
from ga_ext.crossover import (
    bandwise_crossover,
    block_2d_crossover,
    entity_wise_crossover,
    detect_conflicts,
)
from ga_ext.mutation import (
    within_band_swap,
    band_local_jitter,
    micro_reseed,
    mutate,
)


class TestBandUtils(unittest.TestCase):
    """Test band utility functions."""

    def setUp(self):
        """Set up test configuration."""
        self.grid_config = {'width': 20, 'height': 10}
        self.band_config = {'num_bands': 2}

    def test_partition_by_band(self):
        """Test partitioning placements by band."""
        placements = {
            'vinlet': [(5, 2), (10, 8)],  # Band 0 and Band 1
            'acinlet': [(3, 3), (7, 7)]   # Band 0 and Band 1
        }

        partition = partition_by_band(placements, self.grid_config, self.band_config)

        # Check that all positions are partitioned
        total_positions = sum(len(positions) for positions in partition.values())
        self.assertEqual(total_positions, 4)

        # Check that each position is in some band
        self.assertGreater(len(partition), 0)

    def test_get_band_for_position(self):
        """Test determining band for a position."""
        # With 2 bands and height=10, bands are roughly [1-5] and [6-10]
        band = get_band_for_position((5, 3), self.grid_config, self.band_config)
        self.assertIn(band, [0, 1])

        band = get_band_for_position((5, 8), self.grid_config, self.band_config)
        self.assertIn(band, [0, 1])

    def test_count_entities_per_band(self):
        """Test counting entities per band."""
        placements = {
            'vinlet': [(5, 2), (10, 8), (15, 9)],
            'acinlet': [(3, 3)]
        }

        counts = count_entities_per_band(placements, self.grid_config, self.band_config)

        # Should have counts for both bands
        total_count = sum(counts.values())
        self.assertEqual(total_count, 4)

    def test_get_band_boundaries(self):
        """Test getting band boundaries."""
        boundaries = get_band_boundaries(self.grid_config, self.band_config)

        self.assertEqual(len(boundaries), 2)
        for band_idx, y_min, y_max in boundaries:
            self.assertGreaterEqual(y_min, 1)
            self.assertLessEqual(y_max, 10)
            self.assertLessEqual(y_min, y_max)


class TestCrossover(unittest.TestCase):
    """Test crossover operators."""

    def setUp(self):
        """Set up test parents."""
        self.parent_a = Individual(
            id="parent_a",
            path=Path("parent_a.csv"),
            placements={
                'vinlet': [(1, 2), (3, 4), (5, 8)],
                'acinlet': [(2, 3), (4, 7)]
            }
        )

        self.parent_b = Individual(
            id="parent_b",
            path=Path("parent_b.csv"),
            placements={
                'vinlet': [(2, 2), (4, 4), (6, 9)],
                'acinlet': [(3, 3), (5, 7)]
            }
        )

        self.config = {
            'crossover_rate': 0.5,
            'crossover_strategy': 'bandwise'
        }
        self.grid_config = {'width': 20, 'height': 10}
        self.band_config = {'num_bands': 2}
        self.rng = np.random.default_rng(42)

    def test_bandwise_crossover(self):
        """Test band-wise crossover produces valid child."""
        child, mask = bandwise_crossover(
            self.parent_a,
            self.parent_b,
            self.config,
            self.grid_config,
            self.band_config,
            self.rng
        )

        # Child should have placements
        self.assertGreater(child.total_entity_count(), 0)

        # Child should have both entity types
        self.assertIn('vinlet', child.placements)
        self.assertIn('acinlet', child.placements)

        # Mask should have entries
        self.assertGreater(len(mask), 0)

        # All mask values should be from parents
        for value in mask.values():
            self.assertIn(value, ["A", "B", "A (fallback)", "B (fallback)", "none"])

    def test_block_2d_crossover(self):
        """Test 2D block crossover produces valid child."""
        child, mask = block_2d_crossover(
            self.parent_a,
            self.parent_b,
            self.config,
            self.grid_config,
            self.rng,
            blocks_x=2,
            blocks_y=2
        )

        # Child should have placements
        self.assertGreater(child.total_entity_count(), 0)

        # Mask should have 4 blocks (2x2)
        self.assertEqual(len(mask), 4)

    def test_entity_wise_crossover(self):
        """Test entity-wise crossover produces valid child."""
        child, mask = entity_wise_crossover(
            self.parent_a,
            self.parent_b,
            self.config,
            self.rng
        )

        # Child should have placements
        self.assertGreater(child.total_entity_count(), 0)

        # Mask should have one entry per entity type
        self.assertEqual(len(mask), 2)

    def test_detect_conflicts(self):
        """Test conflict detection."""
        # Create individual with conflict
        conflicted = Individual(
            id="conflicted",
            path=Path("conflicted.csv"),
            placements={
                'vinlet': [(5, 5), (10, 10)],
                'acinlet': [(5, 5)]  # Same position as vinlet!
            }
        )

        conflicts = detect_conflicts(conflicted)

        # Should detect one conflict at (5, 5)
        self.assertEqual(len(conflicts), 1)
        self.assertIn((5, 5), conflicts)

        # No conflicts in well-formed individual
        conflicts = detect_conflicts(self.parent_a)
        self.assertEqual(len(conflicts), 0)


class TestMutation(unittest.TestCase):
    """Test mutation operators."""

    def setUp(self):
        """Set up test individual."""
        self.individual = Individual(
            id="test_ind",
            path=Path("test_ind.csv"),
            placements={
                'vinlet': [(5, 2), (10, 3), (15, 8), (18, 9)],
                'acinlet': [(3, 3), (7, 4), (12, 7), (17, 8)]
            }
        )

        self.config = {
            'wy': 2.0,
            'mutation_rate': 1.0,  # Always mutate for testing
            'mutation': {
                'operators': {
                    'within_band_swap': 0.4,
                    'band_local_jitter': 0.4,
                    'micro_reseed': 0.2
                },
                'max_ops_per_individual': 2,
                'micro_reseed_fraction': 0.25,
                'jitter_radius': 3
            }
        }
        self.grid_config = {'width': 20, 'height': 10}
        self.band_config = {'num_bands': 2}
        self.rng = np.random.default_rng(42)

    def test_within_band_swap(self):
        """Test within-band swap operator."""
        mutated, log = within_band_swap(
            self.individual,
            'vinlet',
            self.grid_config,
            self.band_config,
            self.config,
            self.rng
        )

        # Should have same number of entities
        self.assertEqual(
            mutated.get_entity_count('vinlet'),
            self.individual.get_entity_count('vinlet')
        )

        # Log should mention the operation
        self.assertGreater(len(log), 0)
        self.assertTrue(any('within_band_swap' in entry for entry in log))

    def test_band_local_jitter(self):
        """Test local jitter operator."""
        mutated, log = band_local_jitter(
            self.individual,
            'vinlet',
            self.grid_config,
            self.band_config,
            self.config,
            self.rng
        )

        # Should have same number of entities
        self.assertEqual(
            mutated.get_entity_count('vinlet'),
            self.individual.get_entity_count('vinlet')
        )

        # Log should mention the operation
        self.assertGreater(len(log), 0)
        self.assertTrue(any('band_local_jitter' in entry for entry in log))

    def test_micro_reseed(self):
        """Test micro-reseed operator."""
        fraction = 0.25  # Reseed 25% (1 out of 4 vinlets)

        mutated, log = micro_reseed(
            self.individual,
            'vinlet',
            fraction,
            self.grid_config,
            self.band_config,
            self.config,
            self.rng
        )

        # Should have same number of entities
        self.assertEqual(
            mutated.get_entity_count('vinlet'),
            self.individual.get_entity_count('vinlet')
        )

        # At least one position should have changed
        orig_positions = set(self.individual.placements['vinlet'])
        mut_positions = set(mutated.placements['vinlet'])
        self.assertNotEqual(orig_positions, mut_positions)

    def test_mutate_orchestrator(self):
        """Test mutation orchestrator."""
        mutated, log = mutate(
            self.individual,
            self.config,
            self.grid_config,
            self.band_config,
            self.rng
        )

        # Should have log entries
        self.assertGreater(len(log), 0)

        # Should have same total entities (no additions/deletions)
        self.assertEqual(
            mutated.total_entity_count(),
            self.individual.total_entity_count()
        )

    def test_mutation_preserves_entity_counts(self):
        """Test that mutation doesn't change entity counts."""
        for _ in range(5):  # Run multiple times
            mutated, _ = mutate(
                self.individual,
                self.config,
                self.grid_config,
                self.band_config,
                self.rng
            )

            for entity_type in self.individual.placements.keys():
                self.assertEqual(
                    mutated.get_entity_count(entity_type),
                    self.individual.get_entity_count(entity_type),
                    f"Entity count mismatch for {entity_type}"
                )

    def test_mutation_with_zero_rate(self):
        """Test that mutation_rate=0 skips mutation."""
        config = self.config.copy()
        config['mutation_rate'] = 0.0

        mutated, log = mutate(
            self.individual,
            config,
            self.grid_config,
            self.band_config,
            self.rng
        )

        # Should skip mutation
        self.assertTrue(any('no_mutation' in entry or 'skipped' in entry for entry in log))


def run_tests():
    """Run all tests in this module."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestBandUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestCrossover))
    suite.addTests(loader.loadTestsFromTestCase(TestMutation))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
