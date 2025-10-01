"""
Tests for I/O utilities and data models.

Tests CSV parsing, serialization, manifest loading, and lineage logging.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from ga_ext.data_models import Individual, ParentManifest, LineageRecord, create_immigrant_record
from ga_ext.io_utils import (
    load_csv_to_individual,
    save_individual_to_csv,
    load_parent_manifest,
    load_parents_from_directory,
    save_lineage_log,
    create_generation_folder,
    generate_child_path,
    validate_csv_format,
)


class TestDataModels(unittest.TestCase):
    """Test core data model classes."""

    def test_individual_creation(self):
        """Test Individual creation and basic operations."""
        placements = {
            'vinlet': [(5, 4), (10, 8)],
            'acinlet': [(3, 2), (7, 6)]
        }

        ind = Individual(
            id="test_001",
            path=Path("test.csv"),
            placements=placements
        )

        self.assertEqual(ind.id, "test_001")
        self.assertEqual(ind.total_entity_count(), 4)
        self.assertEqual(ind.get_entity_count('vinlet'), 2)
        self.assertEqual(ind.get_entity_count('acinlet'), 2)
        self.assertEqual(len(ind.get_all_positions()), 4)

    def test_individual_copy(self):
        """Test Individual deep copy."""
        placements = {'vinlet': [(5, 4), (10, 8)]}
        ind1 = Individual(id="test_001", path=Path("test.csv"), placements=placements)
        ind2 = ind1.copy()

        # Modify copy
        ind2.placements['vinlet'].append((15, 12))

        # Original should be unchanged
        self.assertEqual(len(ind1.placements['vinlet']), 2)
        self.assertEqual(len(ind2.placements['vinlet']), 3)

    def test_parent_manifest_creation(self):
        """Test ParentManifest creation and validation."""
        ind1 = Individual(id="p1", path=Path("p1.csv"), placements={'vinlet': [(1, 1)]})
        ind2 = Individual(id="p2", path=Path("p2.csv"), placements={'vinlet': [(2, 2)]})

        manifest = ParentManifest(
            parents=[ind1, ind2],
            metadata={'weights': [1.0, 0.5]}
        )

        self.assertEqual(len(manifest), 2)
        self.assertEqual(manifest.get_weights(), [1.0, 0.5])
        self.assertEqual(manifest.get_parent_by_id("p1").id, "p1")

    def test_parent_manifest_empty_validation(self):
        """Test ParentManifest rejects empty parent list."""
        with self.assertRaises(ValueError):
            ParentManifest(parents=[])

    def test_lineage_record_creation(self):
        """Test LineageRecord creation and validation."""
        record = LineageRecord(
            child_path=Path("child_001.csv"),
            parent_ids=["p1", "p2"],
            mode="offspring",
            crossover_mask={('vinlet', 0): 'A', ('vinlet', 1): 'B'},
            mutation_ops=["within_band_swap(vinlet)", "band_local_jitter(acinlet)"],
            repair_notes="conflict_resolved: 2",
            seed=42
        )

        self.assertEqual(record.mode, "offspring")
        self.assertEqual(len(record.parent_ids), 2)
        self.assertEqual(len(record.mutation_ops), 2)

    def test_lineage_record_variant_validation(self):
        """Test LineageRecord validates variant mode has one parent."""
        with self.assertRaises(ValueError):
            LineageRecord(
                child_path=Path("child.csv"),
                parent_ids=["p1", "p2"],  # Too many for variant mode
                mode="variant",
                crossover_mask=None,
                mutation_ops=["within_band_swap(vinlet)"],
                repair_notes="",
                seed=42
            )

    def test_lineage_record_to_dict(self):
        """Test LineageRecord serialization to dict."""
        record = LineageRecord(
            child_path=Path("child_001.csv"),
            parent_ids=["p1", "p2"],
            mode="offspring",
            crossover_mask=None,
            mutation_ops=["swap", "jitter"],
            repair_notes="all good",
            seed=42,
            timestamp="2025-10-01T12:00:00"
        )

        data = record.to_dict()

        self.assertEqual(data['mode'], 'offspring')
        self.assertEqual(data['parent_ids'], 'p1,p2')
        self.assertEqual(data['mutation_ops'], 'swap; jitter')
        self.assertEqual(data['seed'], 42)

    def test_create_immigrant_record(self):
        """Test immigrant record creation helper."""
        record = create_immigrant_record(
            child_path=Path("immigrant_000.csv"),
            seed=123
        )

        self.assertEqual(record.mode, "immigrant")
        self.assertEqual(len(record.parent_ids), 0)
        self.assertEqual(len(record.mutation_ops), 0)


class TestIOUtils(unittest.TestCase):
    """Test I/O utility functions."""

    def setUp(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_csv_round_trip(self):
        """Test loading and saving CSV preserves data."""
        # Create test CSV
        csv_path = self.temp_path / "test_layout.csv"
        with open(csv_path, 'w') as f:
            f.write("name,type,x,y\n")
            f.write("vinlet_x5_y4,vinlet,5,4\n")
            f.write("vinlet_x10_y8,vinlet,10,8\n")
            f.write("acinlet_x3_y2,acinlet,3,2\n")

        # Load
        ind = load_csv_to_individual(csv_path, "test_001")

        self.assertEqual(ind.id, "test_001")
        self.assertEqual(len(ind.placements['vinlet']), 2)
        self.assertEqual(len(ind.placements['acinlet']), 1)
        self.assertIn((5, 4), ind.placements['vinlet'])
        self.assertIn((3, 2), ind.placements['acinlet'])

        # Save to new path
        output_path = self.temp_path / "output_layout.csv"
        save_individual_to_csv(ind, output_path)

        # Load again
        ind2 = load_csv_to_individual(output_path)

        # Should be identical
        self.assertEqual(ind.placements, ind2.placements)

    def test_save_csv_overwrite_protection(self):
        """Test CSV save prevents overwriting without flag."""
        csv_path = self.temp_path / "existing.csv"
        csv_path.touch()

        ind = Individual(
            id="test",
            path=csv_path,
            placements={'vinlet': [(1, 1)]}
        )

        # Should fail without overwrite=True
        with self.assertRaises(FileExistsError):
            save_individual_to_csv(ind, csv_path, overwrite=False)

        # Should succeed with overwrite=True
        save_individual_to_csv(ind, csv_path, overwrite=True)

    def test_load_csv_invalid_file(self):
        """Test loading non-existent CSV raises error."""
        with self.assertRaises(FileNotFoundError):
            load_csv_to_individual(self.temp_path / "nonexistent.csv")

    def test_load_csv_invalid_format(self):
        """Test loading invalid CSV format raises error."""
        csv_path = self.temp_path / "invalid.csv"
        with open(csv_path, 'w') as f:
            f.write("wrong,columns,here\n")
            f.write("1,2,3\n")

        with self.assertRaises(ValueError):
            load_csv_to_individual(csv_path)

    def test_load_parent_manifest(self):
        """Test loading parent manifest CSV."""
        # Create parent CSVs
        parent1_csv = self.temp_path / "parent_001.csv"
        parent2_csv = self.temp_path / "parent_002.csv"

        for csv_path in [parent1_csv, parent2_csv]:
            with open(csv_path, 'w') as f:
                f.write("name,type,x,y\n")
                f.write("vinlet_x1_y1,vinlet,1,1\n")

        # Create manifest
        manifest_path = self.temp_path / "manifest.csv"
        with open(manifest_path, 'w') as f:
            f.write("id,path,score,weight,tags\n")
            f.write(f"p1,parent_001.csv,0.9,1.0,elite\n")
            f.write(f"p2,parent_002.csv,0.8,0.5,diverse\n")

        # Load manifest
        manifest = load_parent_manifest(manifest_path)

        self.assertEqual(len(manifest), 2)
        self.assertEqual(manifest.parents[0].external_score, 0.9)
        self.assertEqual(manifest.parents[1].external_score, 0.8)
        self.assertEqual(manifest.get_weights(), [1.0, 0.5])
        self.assertEqual(manifest.parents[0].metadata.get('tags'), 'elite')

    def test_load_parents_from_directory(self):
        """Test loading all CSVs from directory."""
        # Create multiple CSV files
        for i in range(3):
            csv_path = self.temp_path / f"parent_{i:03d}.csv"
            with open(csv_path, 'w') as f:
                f.write("name,type,x,y\n")
                f.write(f"vinlet_x{i}_y{i},vinlet,{i},{i}\n")

        # Load directory
        manifest = load_parents_from_directory(self.temp_path)

        self.assertEqual(len(manifest), 3)
        self.assertEqual(manifest.parents[0].id, "parent_000")

    def test_save_lineage_log(self):
        """Test saving lineage records to CSV."""
        records = [
            LineageRecord(
                child_path=Path("child_000.csv"),
                parent_ids=["p1", "p2"],
                mode="offspring",
                crossover_mask=None,
                mutation_ops=["swap"],
                repair_notes="good",
                seed=42
            ),
            LineageRecord(
                child_path=Path("child_001.csv"),
                parent_ids=["p3"],
                mode="variant",
                crossover_mask=None,
                mutation_ops=["jitter"],
                repair_notes="fixed 1 conflict",
                seed=43
            )
        ]

        log_path = self.temp_path / "lineage_log.csv"
        save_lineage_log(records, log_path)

        # Verify file exists and has content
        self.assertTrue(log_path.exists())

        # Read back and verify
        with open(log_path, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)  # Header + 2 records
            self.assertIn('child_path', lines[0])
            self.assertIn('child_000.csv', lines[1])

    def test_create_generation_folder(self):
        """Test generation folder creation."""
        gen_folder = create_generation_folder(self.temp_path, 5)

        self.assertTrue(gen_folder.exists())
        self.assertEqual(gen_folder.name, "gen_005")

        # Should fail if already exists
        with self.assertRaises(FileExistsError):
            create_generation_folder(self.temp_path, 5)

    def test_generate_child_path(self):
        """Test child path generation."""
        gen_folder = self.temp_path / "gen_001"
        gen_folder.mkdir()

        path = generate_child_path(gen_folder, 7, prefix="child")
        self.assertEqual(path.name, "child_007.csv")

        path = generate_child_path(gen_folder, 3, prefix="immigrant")
        self.assertEqual(path.name, "immigrant_003.csv")

    def test_validate_csv_format(self):
        """Test CSV format validation."""
        # Valid CSV
        valid_csv = self.temp_path / "valid.csv"
        with open(valid_csv, 'w') as f:
            f.write("name,type,x,y\n")
            f.write("vinlet_x1_y1,vinlet,1,1\n")

        is_valid, error = validate_csv_format(valid_csv)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

        # Invalid: missing columns
        invalid_csv = self.temp_path / "invalid.csv"
        with open(invalid_csv, 'w') as f:
            f.write("wrong,columns\n")
            f.write("1,2\n")

        is_valid, error = validate_csv_format(invalid_csv)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)

        # Invalid: non-existent file
        is_valid, error = validate_csv_format(self.temp_path / "nonexistent.csv")
        self.assertFalse(is_valid)
        self.assertIn("not found", error)


def run_tests():
    """Run all tests in this module."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDataModels))
    suite.addTests(loader.loadTestsFromTestCase(TestIOUtils))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
