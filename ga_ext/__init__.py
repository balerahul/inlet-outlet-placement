"""
GA Extension for Stratified Placement System

This package provides genetic algorithm functionality for evolving
existing CSV placement layouts through band-aware crossover and mutation.

Key Features:
- External fitness evaluation (no internal scoring)
- Non-intrusive design (no modifications to existing code)
- Band-aware operations (respects stratified structure)
- Two modes: variant (single parent) and offspring (multi-parent)

Modules:
- data_models: Core data structures (Individual, ParentManifest, LineageRecord)
- io_utils: CSV I/O, manifest parsing, lineage logging
- band_utils: Band partitioning and quota calculation
- crossover: Band-wise and block-2D crossover operators
- mutation: Band-respecting mutation operators
- repair: Conflict resolution and separation refinement
- engine_interface: Non-invasive wrapper for existing placement engine
- cli: Command-line interface for variant and offspring modes
"""

__version__ = "0.1.0"
__author__ = "Indoor Optimization Team"

from .data_models import Individual, ParentManifest, LineageRecord

__all__ = [
    "Individual",
    "ParentManifest",
    "LineageRecord",
]
