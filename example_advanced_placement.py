#!/usr/bin/env python3
"""
Advanced Stratified Placement Example

Demonstrates the full stratified placement system with configuration loading,
comprehensive metrics analysis, and enhanced visualization.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from stratified_placement import (
    GridRegion, Entity, EntityType, PlacementEngine, GridCell
)
from placement_metrics import PlacementMetrics, print_placement_report
from visualization import PlacementVisualizer
from config_loader import (
    create_placement_engine_from_config, 
    get_visualization_config,
    print_config_summary
)


def main():
    """Main example execution"""
    print("Advanced Stratified Placement System Demo")
    print("=" * 50)
    
    # Load configuration and print summary
    try:
        print_config_summary()
        print()
        
        # Create placement engine from configuration
        engine = create_placement_engine_from_config()
        
        print("Running stratified placement algorithm...")
        print("- Phase A: Normalize & Partition")
        print("- Phase B: Initial Per-Entity Placement (Meet Quotas)")
        print("- Phase C: Joint Refinement (Blue-Noise Optimization)")
        print()
        
        # Execute placement
        result = engine.place_all_entities()
        
        print("Placement completed!")
        print(f"Total entities placed: {sum(len(p) for p in result.placements.values())}")
        print(f"Feasibility notes: {len(result.feasibility_notes)}")
        print()
        
        # Analyze placement quality
        print("Analyzing placement quality...")
        metrics_analyzer = PlacementMetrics(
            engine.grid_region,
            engine.stratification,
            engine.entities,
            engine.cross_entity_radius
        )
        
        metrics = metrics_analyzer.analyze_placement(result)
        
        # Print comprehensive report
        report = print_placement_report(metrics)
        print(report)
        
        # Visualize results
        print("Generating visualizations...")
        vis_config = get_visualization_config()
        
        visualizer = PlacementVisualizer(
            engine.grid_region,
            engine.stratification,
            engine.entities
        )
        
        # Show comprehensive analysis
        visualizer.plot_comprehensive_analysis(
            result, 
            metrics,
            figsize=vis_config.get('figure_size', [16, 12])
        )
        
        # Print individual entity results
        print("\nDetailed Placement Results:")
        print("-" * 30)
        for entity_type, placements in result.placements.items():
            print(f"{entity_type.value}: {len(placements)} entities")
            for i, cell in enumerate(placements):
                print(f"  {i+1}: ({cell.x}, {cell.y})")
        
        if result.feasibility_notes:
            print("\nFeasibility Notes:")
            for note in result.feasibility_notes:
                print(f"  - {note}")
        
        return result, metrics
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def compare_with_original():
    """Compare new stratified system with original implementation"""
    print("\n" + "=" * 50)
    print("COMPARISON WITH ORIGINAL IMPLEMENTATION")
    print("=" * 50)
    
    # Import original functions
    try:
        from generate_random_individual import (
            sample_with_color_constraint, plot_grid
        )
        
        # Original implementation
        n, m = 12, 8
        num_vinlet, num_voutlet, num_acinlet, num_acoutlet = 2, 3, 7, 11
        supply_cells = [(x, y) for x in range(1, n+1) for y in range(3, 7)]
        exhaust_cells = [(x, y) for x in range(1, n+1) for y in range(1, m+1) 
                        if (x, y) not in supply_cells]
        
        print("Running original implementation...")
        original_result = sample_with_color_constraint(
            n, m, num_vinlet, num_voutlet, num_acinlet, num_acoutlet,
            supply_cells, exhaust_cells
        )
        
        # Convert to new format for comparison
        from stratified_placement import PlacementResult
        original_placement_result = PlacementResult()
        original_placement_result.placements = {
            EntityType.VINLET: [GridCell(x, y) for x, y in original_result[0]],
            EntityType.VOUTLET: [GridCell(x, y) for x, y in original_result[1]],
            EntityType.ACINLET: [GridCell(x, y) for x, y in original_result[2]],
            EntityType.ACOUTLET: [GridCell(x, y) for x, y in original_result[3]]
        }
        
        print("Original placement completed!")
        
        # Compare visualizations
        from visualization import compare_placements
        
        # Load new system result
        new_engine = create_placement_engine_from_config()
        new_result = new_engine.place_all_entities()
        
        print("Comparing visualizations...")
        compare_placements(
            [original_placement_result, new_result],
            ["Original FPS", "Stratified System"],
            new_engine.grid_region,
            new_engine.entities
        )
        
    except ImportError:
        print("Could not import original implementation for comparison")


if __name__ == "__main__":
    # Run main example
    result, metrics = main()
    
    # Optional comparison with original
    if result is not None:
        try:
            compare_with_original()
        except Exception as e:
            print(f"Comparison failed: {e}")
    
    print("\nDemo completed!")