#!/usr/bin/env python3
"""
Indoor Optimization - Inlet/Outlet Placement System

Main entry point for the stratified placement system.
This is the primary interface users should use to run placements.
Supports various modes for different use cases.
"""

import sys
import argparse
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from src.config_loader import (
    create_placement_engine_from_config,
    print_config_summary,
    get_visualization_config
)
from src.placement_metrics import PlacementMetrics, print_placement_report
from src.visualization import PlacementVisualizer
from src.placement_exporter import PlacementExporter, create_placement_file


def run_basic_placement(config_path="config.yaml", show_summary=True, output_name=None, save_plots=True):
    """Run basic placement and show results"""
    if show_summary:
        print("=" * 60)
        print("STRATIFIED PLACEMENT SYSTEM")
        print("=" * 60)
        print_config_summary(config_path)

    print("\nRunning placement algorithm...")
    start_time = time.time()

    # Create and run placement engine
    engine = create_placement_engine_from_config(config_path)
    result = engine.place_all_entities()

    elapsed_time = time.time() - start_time
    print(f"Placement completed in {elapsed_time:.3f} seconds")

    # Basic results
    total_placed = sum(len(p) for p in result.placements.values())
    total_expected = sum(e.count for e in engine.entities)

    print(f"\nResults Summary:")
    print(f"  Total entities placed: {total_placed}/{total_expected}")
    print(f"  Feasibility notes: {len(result.feasibility_notes)}")

    for entity_type, placements in result.placements.items():
        print(f"  {entity_type.value}: {len(placements)} entities")

    # Always generate CSV output
    if output_name is None:
        timestamp = int(time.time())
        output_name = f"placement_{timestamp}"

    print(f"\nExporting placement file as '{output_name}.csv'...")
    try:
        file_path = create_placement_file(result, engine.grid_region, output_name)
        print(f"  ✓ CSV: {file_path}")
    except Exception as e:
        print(f"  ✗ CSV: Failed - {e}")

    # Always generate visualization plot
    if save_plots:
        print(f"\nGenerating visualization plot...")
        try:
            # Set matplotlib to non-interactive backend to avoid display issues
            import matplotlib
            matplotlib.use('Agg')

            # Calculate metrics for visualization
            metrics_analyzer = PlacementMetrics(
                engine.grid_region,
                engine.stratification,
                engine.entities,
                engine.cross_entity_radius
            )
            metrics = metrics_analyzer.analyze_placement(result)

            # Create visualization
            vis_config = get_visualization_config(config_path)
            visualizer = PlacementVisualizer(
                engine.grid_region,
                engine.stratification,
                engine.entities
            )

            plot_path = f"output/{output_name}_plot.png"
            visualizer.plot_comprehensive_analysis(
                result,
                metrics,
                figsize=vis_config.get('figure_size', [16, 12]),
                save_path=plot_path
            )
            print(f"  ✓ Plot: {plot_path}")

        except Exception as e:
            print(f"  ✗ Plot: Failed - {e}")
            import traceback
            traceback.print_exc()

    return engine, result



def run_detailed_analysis(config_path="config.yaml", output_name=None, save_plots=True):
    """Run placement with detailed quality analysis"""
    engine, result = run_basic_placement(config_path, output_name=output_name, save_plots=save_plots)

    print("\nAnalyzing placement quality...")
    metrics_analyzer = PlacementMetrics(
        engine.grid_region,
        engine.stratification,
        engine.entities,
        engine.cross_entity_radius
    )

    metrics = metrics_analyzer.analyze_placement(result)

    # Print comprehensive report
    report = print_placement_report(metrics)
    print("\n" + report)

    return engine, result, metrics


def run_with_visualization(config_path="config.yaml", save_plots=False, output_name=None):
    """Run placement with full visualization"""
    engine, result, metrics = run_detailed_analysis(config_path, output_name=output_name)

    print("\nGenerating visualizations...")
    vis_config = get_visualization_config(config_path)

    visualizer = PlacementVisualizer(
        engine.grid_region,
        engine.stratification,
        engine.entities
    )

    # Create comprehensive visualization
    save_path = None
    if save_plots:
        timestamp = int(time.time())
        save_path = f"placement_analysis_{timestamp}.png"
        print(f"Saving plot to: {save_path}")

    try:
        visualizer.plot_comprehensive_analysis(
            result,
            metrics,
            figsize=vis_config.get('figure_size', [16, 12]),
            save_path=save_path
        )
    except Exception as e:
        print(f"Visualization failed (likely due to display issues): {e}")
        print("Continuing without visualization...")

    return engine, result, metrics


def run_multiple_random_trials(num_trials=5, config_path="config.yaml"):
    """Run multiple trials with different random seeds for comparison"""
    print("=" * 60)
    print(f"RUNNING {num_trials} RANDOM TRIALS")
    print("=" * 60)

    results = []

    for trial in range(num_trials):
        print(f"\n--- Trial {trial + 1}/{num_trials} ---")

        # Generate random seed for this trial
        import random
        random_seed = random.randint(1, 1000000)
        print(f"Using random seed: {random_seed}")

        # Temporarily override config for this trial
        from src.config_loader import load_config
        config = load_config(config_path)
        config['optimization']['random_seed'] = random_seed

        # Save temporary config
        import yaml
        temp_config_path = f"temp_config_trial_{trial}.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        try:
            # Generate CSV and plot for each trial
            trial_output_name = f"placement_trial_{trial + 1}_seed_{random_seed}"
            engine, result = run_basic_placement(temp_config_path, show_summary=False, output_name=trial_output_name, save_plots=True)

            # Calculate basic quality score
            metrics_analyzer = PlacementMetrics(
                engine.grid_region, engine.stratification, engine.entities, engine.cross_entity_radius
            )
            metrics = metrics_analyzer.analyze_placement(result)

            trial_result = {
                'trial': trial + 1,
                'seed': random_seed,
                'total_placed': sum(len(p) for p in result.placements.values()),
                'quality_score': metrics['overall_quality_score'],
                'feasibility_notes': len(result.feasibility_notes)
            }
            results.append(trial_result)

        finally:
            # Clean up temporary config
            Path(temp_config_path).unlink(missing_ok=True)

    # Summary of trials
    print("\n" + "=" * 60)
    print("TRIAL SUMMARY")
    print("=" * 60)
    print("Trial | Seed      | Placed | Quality | Issues")
    print("------|-----------|--------|---------|-------")

    for r in results:
        print(f"{r['trial']:5} | {r['seed']:9} | {r['total_placed']:6} | {r['quality_score']:7.3f} | {r['feasibility_notes']:6}")

    # Statistics
    if results:
        quality_scores = [r['quality_score'] for r in results]
        avg_quality = sum(quality_scores) / len(quality_scores)
        min_quality = min(quality_scores)
        max_quality = max(quality_scores)

        print(f"\nQuality Score Statistics:")
        print(f"  Average: {avg_quality:.3f}")
        print(f"  Range: {min_quality:.3f} - {max_quality:.3f}")
        print(f"  Std Dev: {(sum((q - avg_quality)**2 for q in quality_scores) / len(quality_scores))**0.5:.3f}")


def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Indoor Optimization - Stratified Placement System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                               # Basic placement (auto-generates CSV + plot)
  python3 main.py --detailed                    # With quality analysis + CSV + plot
  python3 main.py --visualize                   # Full interactive analysis + CSV + plot
  python3 main.py --output-name "room_v1"       # Custom filenames (room_v1.csv + room_v1_plot.png)
  python3 main.py --trials 10                   # Multiple random trials (each with CSV + plot)
  python3 main.py --config custom.yaml          # Custom config file
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )

    parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help='Run detailed quality analysis'
    )

    parser.add_argument(
        '--visualize', '-v',
        action='store_true',
        help='Generate comprehensive visualizations'
    )

    parser.add_argument(
        '--trials', '-t',
        type=int,
        metavar='N',
        help='Run N random trials for comparison'
    )

    parser.add_argument(
        '--output-name', '-n',
        type=str,
        metavar='NAME',
        help='Base name for CSV file (default: placement_TIMESTAMP)'
    )

    args = parser.parse_args()

    try:
        if args.trials:
            run_multiple_random_trials(args.trials, args.config)
        elif args.visualize:
            run_with_visualization(args.config, True, args.output_name)
        elif args.detailed:
            run_detailed_analysis(args.config, args.output_name, save_plots=True)
        else:
            run_basic_placement(args.config, output_name=args.output_name, save_plots=True)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()