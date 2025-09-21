"""
Placement Export System

Exports placement results to various formats suitable for simulation pipelines
and automated processing. Supports JSON, CSV, XML, and custom formats.
"""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import time
from datetime import datetime

from .stratified_placement import PlacementResult, EntityType, GridCell, GridRegion
from .placement_metrics import PlacementMetrics


@dataclass 
class SimulationEntity:
    """Entity definition for simulation pipeline"""
    name: str  # e.g., acinlet_x5_y3
    type: str  # vinlet, voutlet, acinlet, acoutlet
    x: int
    y: int


@dataclass
class PlacementConfiguration:
    """Complete placement configuration for simulation"""
    entities: List[SimulationEntity]
    metadata: Dict[str, Any]


class PlacementExporter:
    """Exports placement results to CSV format for simulation"""
    
    def __init__(self):
        """Initialize exporter"""
        pass
    
    def create_simulation_config(self, 
                                result: PlacementResult,
                                grid_region: GridRegion) -> PlacementConfiguration:
        """
        Convert placement result to simulation configuration
        
        Args:
            result: Placement result from engine
            grid_region: Grid region definition
            
        Returns:
            Simple simulation configuration
        """
        # Generate metadata
        sim_metadata = {
            'timestamp': datetime.now().isoformat(),
            'generator': 'stratified_placement_system',
            'grid_size': f'{grid_region.width}x{grid_region.height}',
            'total_entities': sum(len(p) for p in result.placements.values())
        }
        
        # Convert placements to simulation entities with name convention
        sim_entities = []
        
        for entity_type, placements in result.placements.items():
            type_name = entity_type.value
            
            for placement in placements:
                # Create name with format: type_xN_yN
                entity_name = f'{type_name}_x{placement.x}_y{placement.y}'
                
                entity = SimulationEntity(
                    name=entity_name,
                    type=type_name,
                    x=placement.x,
                    y=placement.y
                )
                sim_entities.append(entity)
        
        return PlacementConfiguration(
            entities=sim_entities,
            metadata=sim_metadata
        )
    
    def export_csv(self, 
                  config: PlacementConfiguration,
                  output_path: str) -> str:
        """Export entity list to CSV format"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['name', 'type', 'x', 'y'])
            
            # Entity data
            for entity in config.entities:
                writer.writerow([
                    entity.name,
                    entity.type, 
                    entity.x,
                    entity.y
                ])
        
        return str(output_file)


def create_placement_file(result: PlacementResult,
                         grid_region: GridRegion,
                         output_name: Optional[str] = None) -> str:
    """
    Convenience function to create placement CSV file
    
    Args:
        result: Placement result
        grid_region: Grid region
        output_name: Base name for output file
        
    Returns:
        Path to generated CSV file
    """
    if output_name is None:
        timestamp = int(time.time())
        output_name = f"placement_{timestamp}"
    
    exporter = PlacementExporter()
    config = exporter.create_simulation_config(result, grid_region)
    
    return exporter.export_csv(config, f"output/{output_name}.csv")


if __name__ == "__main__":
    # Example usage
    from config_loader import create_placement_engine_from_config
    
    # Generate placement
    engine = create_placement_engine_from_config()
    result = engine.place_all_entities()
    
    # Export to CSV
    output_file = create_placement_file(
        result, engine.grid_region,
        output_name="example_placement"
    )
    
    print(f"Generated placement file: {output_file}")