"""
Visualization utilities for GA extension.

Provides functions to convert GA Individuals to visualization format
and generate comprehensive multi-panel plots.
"""

from pathlib import Path
from typing import Dict, Any, Tuple

from src.stratified_placement import (
    PlacementResult, EntityType, GridCell
)
from src.placement_metrics import PlacementMetrics
from src.visualization import PlacementVisualizer

from .data_models import Individual
from .engine_interface import EngineInterface


def individual_to_placement_result(
    individual: Individual,
    engine_interface: EngineInterface
) -> PlacementResult:
    """
    Convert Individual (GA format) to PlacementResult (visualization format).

    Args:
        individual: GA Individual with placements dict[str, list[tuple[int, int]]]
        engine_interface: Engine interface providing entity map and configuration

    Returns:
        PlacementResult compatible with PlacementVisualizer

    Example:
        individual.placements = {
            'vinlet': [(3, 3), (5, 4)],
            'voutlet': [(3, 1), (5, 2)]
        }
        →
        result.placements = {
            EntityType.VINLET: [GridCell(3, 3), GridCell(5, 4)],
            EntityType.VOUTLET: [GridCell(3, 1), GridCell(5, 2)]
        }
    """
    placements_converted = {}

    for entity_type_str, positions in individual.placements.items():
        # Convert string to EntityType enum
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            # Unknown entity type, skip
            continue

        # Convert (x, y) tuples to GridCell objects
        grid_cells = [GridCell(x, y) for x, y in positions]
        placements_converted[entity_type] = grid_cells

    # Create PlacementResult
    result = PlacementResult(
        placements=placements_converted,
        metrics={
            'individual_id': individual.id,
            'external_score': individual.external_score
        },
        feasibility_notes=individual.metadata.get('repair_notes', '').split('; ')
            if individual.metadata.get('repair_notes') else []
    )

    return result


def visualize_individual(
    individual: Individual,
    engine_interface: EngineInterface,
    output_path: Path,
    figsize: Tuple[int, int] = (16, 12)
) -> None:
    """
    Generate comprehensive visualization plot for an individual.

    Creates a multi-panel plot showing:
    - Main placement with band boundaries
    - Coverage metrics by entity
    - Placement density heatmap
    - Separation violations
    - Y-coordinate distribution

    Args:
        individual: Individual to visualize
        engine_interface: Engine interface providing grid, entities, stratification
        output_path: Path to save PNG file
        figsize: Figure size (width, height) in inches

    Example:
        visualize_individual(
            individual=child,
            engine_interface=engine,
            output_path=Path("ga_output/variants/variant_000.png"),
            figsize=(16, 12)
        )
    """
    # Convert Individual to PlacementResult
    result = individual_to_placement_result(individual, engine_interface)

    # Create metrics analyzer
    metrics_analyzer = PlacementMetrics(
        grid_region=engine_interface.grid_region,
        stratification=engine_interface.stratification,
        entities=engine_interface.entities,
        cross_entity_radius=engine_interface.cross_entity_radius
    )

    # Compute metrics
    metrics = metrics_analyzer.analyze_placement(result)

    # Create visualizer
    visualizer = PlacementVisualizer(
        grid_region=engine_interface.grid_region,
        stratification=engine_interface.stratification,
        entities=engine_interface.entities
    )

    # Generate and save plot
    visualizer.plot_comprehensive_analysis(
        result=result,
        metrics=metrics,
        figsize=figsize,
        save_path=str(output_path)
    )

    print(f"  Saved visualization: {output_path}")
