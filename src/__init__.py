"""
Indoor Optimization - Inlet/Outlet Placement System

A comprehensive stratified placement system for rectangular grids.
"""

__version__ = "1.0.0"
__author__ = "Indoor Optimization Team"

# Export main classes for easy importing
from .stratified_placement import (
    PlacementEngine,
    PlacementResult,
    EntityType,
    GridCell,
    GridRegion,
    Entity,
    Stratification
)

from .placement_metrics import PlacementMetrics
from .visualization import PlacementVisualizer
from .placement_exporter import PlacementExporter, create_placement_file
from .config_loader import create_placement_engine_from_config, load_config

__all__ = [
    'PlacementEngine',
    'PlacementResult',
    'EntityType',
    'GridCell',
    'GridRegion',
    'Entity',
    'Stratification',
    'PlacementMetrics',
    'PlacementVisualizer',
    'PlacementExporter',
    'create_placement_file',
    'create_placement_engine_from_config',
    'load_config'
]