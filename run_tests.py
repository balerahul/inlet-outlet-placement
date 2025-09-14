#!/usr/bin/env python3
"""
Test runner for the stratified placement system
"""

import unittest
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def run_all_tests():
    """Run all test modules"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import test modules
    try:
        from tests import test_stratification, test_placement_engine
        
        # Add test modules to suite
        suite.addTests(loader.loadTestsFromModule(test_stratification))
        suite.addTests(loader.loadTestsFromModule(test_placement_engine))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except ImportError as e:
        print(f"Failed to import test modules: {e}")
        return False


def run_integration_test():
    """Run a basic integration test"""
    print("\n" + "=" * 50)
    print("INTEGRATION TEST")
    print("=" * 50)
    
    try:
        from config_loader import create_placement_engine_from_config
        from placement_metrics import PlacementMetrics, print_placement_report
        
        # Create and run placement engine
        print("Creating placement engine from config...")
        engine = create_placement_engine_from_config()
        
        print("Running placement algorithm...")
        result = engine.place_all_entities()
        
        print("Analyzing placement quality...")
        metrics_analyzer = PlacementMetrics(
            engine.grid_region,
            engine.stratification,
            engine.entities,
            engine.cross_entity_radius
        )
        
        metrics = metrics_analyzer.analyze_placement(result)
        
        # Basic validation
        total_placed = sum(len(p) for p in result.placements.values())
        total_expected = sum(e.count for e in engine.entities)
        
        print(f"Entities placed: {total_placed}/{total_expected}")
        print(f"Quality score: {metrics['overall_quality_score']:.3f}")
        print(f"Feasibility notes: {len(result.feasibility_notes)}")
        
        # Check basic success criteria
        success = (
            total_placed == total_expected and
            metrics['overall_quality_score'] > 0.5 and
            len(result.feasibility_notes) == 0
        )
        
        if success:
            print("✓ Integration test PASSED")
        else:
            print("✗ Integration test FAILED")
            
        return success
        
    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Running Stratified Placement System Tests")
    print("=" * 60)
    
    # Run unit tests
    print("Running unit tests...")
    unit_success = run_all_tests()
    
    # Run integration test
    integration_success = run_integration_test()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Unit tests: {'PASSED' if unit_success else 'FAILED'}")
    print(f"Integration test: {'PASSED' if integration_success else 'FAILED'}")
    
    overall_success = unit_success and integration_success
    print(f"Overall: {'PASSED' if overall_success else 'FAILED'}")
    
    sys.exit(0 if overall_success else 1)